"""기존 관리도구에 로컬 문서 작업 API와 지속 작업함을 연결한다."""
from datetime import datetime
import json
import fcntl
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import threading
import uuid
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator
from .documents import REQUEST_INPUT_SCHEMA, load_workspace_config,load_yaml_document,save_yaml_document,parse_unique_json

BOOK_REQUEST_LIMIT = 2_000_000
MANAGEMENT_REQUEST_LIMIT = 32768
WORKFLOW_MODULE_ROOT = Path(__file__).resolve().parent
WORKFLOW_REPOSITORY_ROOT = WORKFLOW_MODULE_ROOT.parents[1]
DEFAULT_CONFIG_PATH = WORKFLOW_REPOSITORY_ROOT/'.local/worldbuilding/workspace.yaml'


class WorldbuildingManagement:
    """요청은 한 작업씩 실행하며 큐와 결과를 비공개 경로에 보존한다."""
    def __init__(self,workspace_config_path):
        self.workspace_config_path=workspace_config_path
        self.workspace_config_values=load_workspace_config(workspace_config_path)
        self.private_state_root=Path(self.workspace_config_values['private_state_root'])
        self.management_lock_stream=(self.private_state_root/'manager.lock').open('a')
        try:
            fcntl.flock(self.management_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:
            self.management_lock_stream.close()
            raise RuntimeError('같은 문서 작업 공간의 관리도구가 이미 실행 중입니다.') from current_lock_error
        self.management_csrf_token=secrets.token_urlsafe(32)
        self.worker_stop_event=threading.Event()
        self.current_process_handle=None
        self.current_task_identifier=None
        self.current_prepare_status='idle'
        self.worker_failure_text=''
        self.queue_operation_lock=threading.Lock()
        self.management_log_path=self.private_state_root/'management.log'
        (self.private_state_root/'jobs').mkdir(exist_ok=True)
        for current_status_path in (self.private_state_root/'jobs').glob('*/status.yaml'):
            current_status_values=load_yaml_document(current_status_path)
            if current_status_values['current_stage_name'] not in {'queued','completed','failed','rolled_back'}:
                current_status_values.update(current_stage_name='failed',failure_reason_text='관리도구 재시작으로 중단된 작업입니다. 변경 저널을 확인하세요.')
                save_yaml_document(current_status_path,current_status_values)
        self.worker_thread_handle=threading.Thread(target=self.process_pending_jobs,daemon=True)
        self.worker_thread_handle.start()

    def read_management_state(self):
        current_job_entries=[]
        for current_status_path in sorted((self.private_state_root/'jobs').glob('*/status.yaml'),reverse=True)[:50]:
            current_status_values=load_yaml_document(current_status_path)
            current_request_values=load_yaml_document(current_status_path.parent/'request.yaml')
            current_status_values['requested_instruction_text']=current_request_values['requested_instruction_text']
            current_status_values['discovery_steps']=[load_yaml_document(current_discovery_path)['discovery_decision_values'] for current_discovery_path in sorted(current_status_path.parent.glob('discovery-*.yaml'))]
            current_changes_path=current_status_path.parent/'changes.yaml'
            if current_changes_path.exists():
                current_status_values['document_change_entries']=load_yaml_document(current_changes_path)['document_change_entries']
            current_transaction_path=current_status_path.parent/'transaction.yaml'
            current_status_values['can_rollback_flag']=current_transaction_path.exists() and load_yaml_document(current_transaction_path)['transaction_apply_state'] in {'applying','applied'}
            current_job_entries.append(current_status_values)
        prepared_manifest_path=WORKFLOW_REPOSITORY_ROOT/'.local/worldbuilding/prepared.json'
        prepare_log_text=''
        if (self.private_state_root/'prepare.log').exists():
            prepare_log_text='\n'.join((self.private_state_root/'prepare.log').read_text(errors='replace').splitlines()[-15:])
        return {'management_csrf_token':self.management_csrf_token,'runtime_prepared_flag':prepared_manifest_path.exists() and (WORKFLOW_REPOSITORY_ROOT/'.model/worldbuilding/Qwen3-Embedding-0.6B-Q8_0.gguf').exists(),'runtime_prepare_status':self.current_prepare_status,'worker_failure_text':self.worker_failure_text,'runtime_prepare_log':prepare_log_text,'source_document_root':self.workspace_config_values['source_document_root'],'allowed_write_roots':self.workspace_config_values['allowed_write_roots'],'primary_document_roots':[str(Path(self.workspace_config_values['source_document_root'])/current_write_root) for current_write_root in self.workspace_config_values['allowed_write_roots']],'workflow_job_entries':current_job_entries}

    def submit_document_request(self,current_request_values):
        Draft202012Validator(REQUEST_INPUT_SCHEMA).validate(current_request_values)
        current_task_identifier=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
        current_run_root=self.private_state_root/'jobs'/current_task_identifier
        current_run_root.mkdir(mode=0o700)
        save_yaml_document(current_run_root/'request.yaml',current_request_values)
        save_yaml_document(current_run_root/'status.yaml',{'workflow_task_id':current_task_identifier,'current_stage_name':'queued','updated_timestamp_text':datetime.now(ZoneInfo('Asia/Seoul')).isoformat()})
        return {'workflow_task_id':current_task_identifier}

    def process_pending_jobs(self):
        try:
            self.process_pending_queue()
        except Exception as current_worker_error:
            self.worker_failure_text=str(current_worker_error)
            self.worker_stop_event.set()
            import traceback
            with self.management_log_path.open('a') as current_error_stream:
                current_error_stream.write(traceback.format_exc())

    def process_pending_queue(self):
        while not self.worker_stop_event.wait(1):
            with self.queue_operation_lock:
                if self.current_process_handle is not None:
                    continue
                queued_status_paths=[current_status_path for current_status_path in sorted((self.private_state_root/'jobs').glob('*/status.yaml')) if load_yaml_document(current_status_path)['current_stage_name']=='queued']
                if not queued_status_paths:
                    continue
                if not (WORKFLOW_REPOSITORY_ROOT/'.local/worldbuilding/prepared.json').exists():
                    continue
                current_run_root=queued_status_paths[0].parent
                self.current_task_identifier=current_run_root.name
                current_process_log=(current_run_root/'process.log').open('a')
                self.current_process_handle=subprocess.Popen([sys.executable,str(WORKFLOW_MODULE_ROOT/'worldbuilding.py'),'run','--config',str(self.workspace_config_path),'--task',current_run_root.name],stdout=current_process_log,stderr=subprocess.STDOUT,start_new_session=True)
            current_result_code=self.current_process_handle.wait()
            current_process_log.close()
            if current_result_code:
                current_status_values=load_yaml_document(current_run_root/'status.yaml')
                if current_status_values['current_stage_name']!='failed':
                    current_status_values.update(current_stage_name='failed',failure_reason_text='실행 프로세스 실패: '+ '\n'.join((current_run_root/'process.log').read_text(errors='replace').splitlines()[-12:]))
                    save_yaml_document(current_run_root/'status.yaml',current_status_values)
            with self.queue_operation_lock:
                self.current_process_handle=None
                self.current_task_identifier=None

    def start_environment_prepare(self):
        with self.queue_operation_lock:
            if self.current_process_handle is not None:
                raise ValueError('다른 작업이 실행 중입니다.')
            current_prepare_stream=(self.private_state_root/'prepare.log').open('w')
            self.current_prepare_status='running'
            self.current_process_handle=subprocess.Popen([sys.executable,str(WORKFLOW_MODULE_ROOT/'worldbuilding.py'),'prepare'],stdout=current_prepare_stream,stderr=subprocess.STDOUT,start_new_session=True)
        def finish_environment_prepare():
            current_exit_code=self.current_process_handle.wait()
            current_prepare_stream.close()
            with self.queue_operation_lock:
                self.current_prepare_status='completed' if current_exit_code==0 else 'failed'
                self.current_process_handle=None
        threading.Thread(target=finish_environment_prepare,daemon=True).start()

    def rollback_completed_task(self,current_task_identifier):
        if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{8}',current_task_identifier):
            raise ValueError('올바르지 않은 작업 ID')
        with self.queue_operation_lock:
            if self.current_process_handle is not None:
                raise ValueError('실행 중인 작업이 있습니다.')
            current_rollback_result=subprocess.run([sys.executable,str(WORKFLOW_MODULE_ROOT/'worldbuilding.py'),'rollback','--config',str(self.workspace_config_path),'--task',current_task_identifier],capture_output=True,text=True)
            if current_rollback_result.returncode:
                raise ValueError(current_rollback_result.stderr[-2000:])

    def close_management_worker(self):
        self.worker_stop_event.set()
        with self.queue_operation_lock:
            if self.current_process_handle is not None:
                try:
                    os.killpg(self.current_process_handle.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        self.worker_thread_handle.join(timeout=20)
        self.management_lock_stream.close()

    def handle_management_request(self,current_http_handler):
        requested_url_path=urlsplit(current_http_handler.path).path
        if not requested_url_path.startswith('/worldbuilding'):
            return False
        expected_host_text=f'127.0.0.1:{current_http_handler.server.server_port}'
        requested_host_text=current_http_handler.headers.get('Host','')
        if requested_host_text not in {expected_host_text,f'localhost:{current_http_handler.server.server_port}'}:
            current_http_handler.send_error(403)
            return True
        try:
            if current_http_handler.command=='GET' and requested_url_path in {'/worldbuilding','/worldbuilding/'}:
                response_body_bytes=(WORKFLOW_MODULE_ROOT/'management.html').read_bytes()
                response_type_value='text/html; charset=utf-8'
            elif current_http_handler.command=='GET' and requested_url_path=='/worldbuilding/library':
                response_body_bytes=(WORKFLOW_MODULE_ROOT/'book-library.html').read_bytes()
                response_type_value='text/html; charset=utf-8'
            elif current_http_handler.command=='GET' and requested_url_path=='/worldbuilding/api/books':
                from .bookbinding import list_document_books
                from .reorganization import list_document_reorganizations
                current_library_values=list_document_books(self.workspace_config_values)
                current_library_values['reorganization_entries']=list_document_reorganizations(self.workspace_config_values)
                response_body_bytes=json.dumps(current_library_values,ensure_ascii=False).encode()
                response_type_value='application/json; charset=utf-8'
            elif current_http_handler.command=='GET' and requested_url_path.startswith('/worldbuilding/books/'):
                from .bookbinding import read_book_artifact
                current_url_parts=requested_url_path.split('/')
                if len(current_url_parts)!=5:
                    raise ValueError('올바르지 않은 도서 경로입니다.')
                response_body_bytes=read_book_artifact(self.workspace_config_values,current_url_parts[3],current_url_parts[4])
                response_type_value='text/html; charset=utf-8' if current_url_parts[4]=='book.html' else 'text/plain; charset=utf-8'
            elif current_http_handler.command=='GET' and requested_url_path=='/worldbuilding/api/state':
                response_body_bytes=json.dumps(self.read_management_state(),ensure_ascii=False).encode()
                response_type_value='application/json; charset=utf-8'
            elif current_http_handler.command=='POST':
                if current_http_handler.headers.get('Origin')!=f'http://{requested_host_text}' or current_http_handler.headers.get('X-Worldbuilding-Token')!=self.management_csrf_token:
                    raise ValueError('같은 관리도구 화면에서 보낸 요청만 허용합니다.')
                request_content_length=int(current_http_handler.headers.get('Content-Length','0'))
                current_request_limit=BOOK_REQUEST_LIMIT if requested_url_path in {'/worldbuilding/api/books','/worldbuilding/api/book-plan','/worldbuilding/api/reorganize-preview'} else MANAGEMENT_REQUEST_LIMIT
                if not 0<request_content_length<=current_request_limit:
                    raise ValueError('요청 크기가 올바르지 않습니다.')
                request_body_values=parse_unique_json(current_http_handler.rfile.read(request_content_length).decode())
                if requested_url_path=='/worldbuilding/api/reorganize-preview':
                    from .reorganization import preview_document_reorganization
                    current_response_values=preview_document_reorganization(self.workspace_config_values,request_body_values)
                elif requested_url_path in {'/worldbuilding/api/reorganize-apply','/worldbuilding/api/reorganize-rollback'}:
                    from .reorganization import execute_document_reorganization
                    if not isinstance(request_body_values,dict) or set(request_body_values)!={'reorganization_id'} or not isinstance(request_body_values['reorganization_id'],str):
                        raise ValueError('올바르지 않은 파일 구조 작업 요청입니다.')
                    current_response_values=execute_document_reorganization(self.workspace_config_values,request_body_values['reorganization_id'],requested_url_path.rsplit('-',1)[1])
                elif requested_url_path in {'/worldbuilding/api/books','/worldbuilding/api/book-plan'}:
                    from .bookbinding import build_document_book, plan_document_book
                    current_response_values=(build_document_book if requested_url_path.endswith('/books') else plan_document_book)(self.workspace_config_values,request_body_values)
                elif requested_url_path=='/worldbuilding/api/tasks':
                    current_response_values=self.submit_document_request(request_body_values)
                elif requested_url_path=='/worldbuilding/api/learn' and request_body_values=={}:
                    current_response_values=self.submit_document_request({'requested_instruction_text':'세계관 문서 RAG 색인을 최신 원문으로 학습·갱신합니다.','requested_operation_mode':'index','requested_target_path':''})
                elif requested_url_path=='/worldbuilding/api/prepare' and request_body_values=={}:
                    self.start_environment_prepare()
                    current_response_values={'runtime_prepare_status':'running'}
                elif requested_url_path=='/worldbuilding/api/rollback' and set(request_body_values)=={'workflow_task_id'}:
                    self.rollback_completed_task(request_body_values['workflow_task_id'])
                    current_response_values={'current_stage_name':'rolled_back'}
                else:
                    raise ValueError('지원하지 않는 요청입니다.')
                response_body_bytes=json.dumps(current_response_values,ensure_ascii=False).encode()
                response_type_value='application/json; charset=utf-8'
            else:
                current_http_handler.send_error(404)
                return True
            current_http_handler.send_response(200)
        except Exception as current_request_error:
            current_http_handler.send_response(400)
            response_body_bytes=json.dumps({'failure_reason_text':str(current_request_error)},ensure_ascii=False).encode()
            response_type_value='application/json; charset=utf-8'
        current_http_handler.send_header('Content-Type',response_type_value)
        current_http_handler.send_header('Content-Length',str(len(response_body_bytes)))
        current_http_handler.end_headers()
        current_http_handler.wfile.write(response_body_bytes)
        return True
