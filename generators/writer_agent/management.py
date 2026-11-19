"""로컬 관리도구의 작가 에이전트 요청·작업·변경 미리보기 API."""
from pathlib import Path
from contextlib import closing
from urllib.parse import urlsplit,parse_qs
import json
import fcntl
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import uuid
from .documents import (DEFAULT_WORKSPACE_CONFIG,WORKFLOW_REPOSITORY_ROOT,load_workspace_config,read_yaml_document,save_yaml_document,parse_unique_json,calculate_content_hash,lock_workspace_state)
from .jobs import JOB_IDENTIFIER_PATTERN,create_writer_job,resolve_job_directory,update_job_status,read_process_identity
from .agent import apply_reviewed_proposal
from . import prepare
from tools.review.common.model_prepare_process import inspect_detached_preparation, start_detached_preparation
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation
from tools.review.common.generation_records import write_record_atomically

WRITER_ROUTE_PREFIX='/writer-agent'
MAXIMUM_REQUEST_BYTES=32000
MAXIMUM_LOG_BYTES=48000
ACTIVE_JOB_STAGES={'queued','indexing','searching','reasoning','preparing'}

class WriterAgentManager:
    def __init__(self,current_config_path=DEFAULT_WORKSPACE_CONFIG):
        self.workspace_config_path=Path(current_config_path)
        self.request_lock_handle=threading.Lock()
        self.worker_process_handle=None
        self.worker_job_identifier=None
        self.worker_prepare_flag=False
        self.csrf_token_value=uuid.uuid4().hex

    def read_workspace_state(self):
        try:
            current_manifest_record=json.loads((prepare.RUNTIME_INSTALL_ROOT/'prepared.json').read_text())
            current_ready_flag=current_manifest_record.get('backend') == 'rocm' and current_manifest_record.get('model_file_sha256') == prepare.MODEL_DOWNLOAD_SHA256 and current_manifest_record.get('embedding_file_sha256') == prepare.EMBEDDING_DOWNLOAD_SHA256 and prepare.RUNTIME_SERVER_PATH.is_file()
        except (OSError, ValueError, AttributeError):
            current_ready_flag=False
        current_state_values={'configured':self.workspace_config_path.is_file(),'ready':current_ready_flag,'csrf_token':self.csrf_token_value,'config_path':str(self.workspace_config_path),'active_job':self.worker_job_identifier if self.worker_process_handle and self.worker_process_handle.poll() is None else None,'jobs':[]}
        if not current_state_values['configured']:return current_state_values
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_index_path=Path(current_config_values['state_root'])/'rag.sqlite3'
        current_index_ready=False
        if current_index_path.is_file():
            try:
                from .index import INDEX_SCHEMA_VERSION
                with closing(sqlite3.connect(f'file:{current_index_path}?mode=ro', uri=True)) as current_index_connection:
                    current_index_ready=current_index_connection.execute("SELECT value FROM metadata WHERE key='version'").fetchone() == (INDEX_SCHEMA_VERSION,)
            except sqlite3.Error:
                pass
        current_state_values.update({'document_root':current_config_values['document_root'],'state_root':current_config_values['state_root'],'index_path':str(current_index_path),'trained':current_index_ready})
        for current_job_root in sorted((Path(current_config_values['state_root'])/'jobs').glob('*'),reverse=True)[:40]:
            if not current_job_root.is_dir() or current_job_root.is_symlink() or not (current_job_root/'status.yaml').is_file():continue
            current_status_values=read_yaml_document(current_job_root/'status.yaml')
            current_status_values=self.resolve_observed_status(current_status_values,current_job_root)
            if current_status_values['stage'] in ACTIVE_JOB_STAGES:current_state_values['active_job']=current_job_root.name
            current_state_values['jobs'].append(current_status_values)
        return current_state_values

    def resolve_observed_status(self,current_status_values,current_job_root=None):
        if current_job_root is not None and (current_status_values['stage'] in ACTIVE_JOB_STAGES or current_status_values['stage']=='failed'):
            try:
                current_queue_record=json.loads((current_job_root/'status.json').read_text())
                current_queue_error=current_queue_record.get('error')
                if current_status_values['stage'] in ACTIVE_JOB_STAGES and current_queue_record.get('status') in ('failed','cancelled'):
                    return {**current_status_values,'stage':'failed' if current_queue_record['status']=='failed' else 'interrupted','error':current_queue_error or 'GPU 대기 작업이 중지되었습니다.'}
                if current_status_values['stage']=='failed' and current_queue_record.get('status')=='failed' and isinstance(current_queue_error,str) and current_queue_error.startswith(('시스템 RAM 보호:', '시스템 RAM 감시 실패:')):
                    return {**current_status_values,'error':current_queue_error}
                if current_status_values['stage'] not in ACTIVE_JOB_STAGES:return current_status_values
                current_supervisor_record=json.loads((current_job_root/'queue-process.json').read_text())
                current_supervisor_alive=read_process_identity(current_supervisor_record['pid'])==current_supervisor_record['identity'] and current_supervisor_record['identity'] is not None
                if current_supervisor_alive:
                    if current_status_values['stage']=='queued':
                        return {**current_status_values,'queue_position':current_queue_record.get('queue_position'),'summary':current_queue_record.get('message','GPU 실행 대기')}
                    return current_status_values
            except (OSError, ValueError, TypeError, KeyError):
                pass
        if current_status_values['stage'] not in ACTIVE_JOB_STAGES:return current_status_values
        if current_status_values['id']==self.worker_job_identifier and self.worker_process_handle and self.worker_process_handle.poll() is None:return current_status_values
        current_process_identifier=current_status_values.get('process_id')
        current_process_identity=current_status_values.get('process_identity')
        if type(current_process_identifier) is int and current_process_identity and read_process_identity(current_process_identifier)==current_process_identity:return current_status_values
        return {**current_status_values,'stage':'interrupted','error':'실행 프로세스가 종료된 작업입니다. 로그를 확인하고 새 작업으로 실행하세요.'}

    def launch_writer_process(self,current_request_values):
        current_config_values=load_workspace_config(self.workspace_config_path)
        with self.request_lock_handle, (Path(current_config_values['state_root'])/'submission.lock').open('a') as current_submission_lock:
            fcntl.flock(current_submission_lock,fcntl.LOCK_EX)
            if self.read_workspace_state()['active_job']:raise ValueError('이미 작가 에이전트 작업이 실행 중이거나 대기 중입니다.')
            current_prepare_flag=current_request_values=={'mode':'prepare','prompt':''}
            current_prepare_root = WORKFLOW_REPOSITORY_ROOT/'.local/model-preparation/writer-agent'
            if inspect_detached_preparation(current_prepare_root) == 'running':
                raise ValueError('이미 작가 에이전트 모델 준비가 실행 중입니다.')
            if inspect_detached_preparation(WORKFLOW_REPOSITORY_ROOT/'.local/model-preparation/writer-model') == 'running':
                raise ValueError('작가 AI 모델 다운로드가 실행 중입니다.')
            if not current_prepare_flag and not prepare.RUNTIME_PYTHON_PATH.is_file():raise ValueError('먼저 환경 준비를 실행하세요.')
            current_job_identifier=create_writer_job(current_config_values,{'mode':'learn','prompt':''} if current_prepare_flag else current_request_values)
            current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
            if current_prepare_flag:
                save_yaml_document(current_job_root/'request.yaml',current_request_values)
                update_job_status(current_job_root,'queued',mode='prepare')
                current_command_values=[sys.executable,'-m','generators.writer_agent.prepare','--run-dir',str(current_job_root)]
            else:
                current_command_values=[str(prepare.RUNTIME_PYTHON_PATH),'-m','generators.writer_agent.jobs','--config',str(self.workspace_config_path),'--job-id',current_job_identifier]
            try:
                with (current_job_root/'worker.log').open('w') as current_worker_log:
                    self.worker_process_handle=launch_gpu_process(current_command_values,current_job_root,'writer-agent',cwd=WORKFLOW_REPOSITORY_ROOT,stdout=current_worker_log,stderr=subprocess.STDOUT,start_new_session=True)
                write_record_atomically(current_job_root/'queue-process.json',{'pid':self.worker_process_handle.pid,'identity':read_process_identity(self.worker_process_handle.pid)})
            except (OSError, ValueError) as current_launch_error:
                update_job_status(current_job_root,'failed',error=str(current_launch_error))
                raise
            self.worker_prepare_flag=current_prepare_flag
            self.worker_job_identifier=current_job_identifier
            current_worker_process=self.worker_process_handle
            def monitor_writer_process():
                current_exit_code=current_worker_process.wait()
                with self.request_lock_handle:
                    if not (current_job_root/'status.yaml').exists():return
                    current_stage_name=read_yaml_document(current_job_root/'status.yaml')['stage']
                    if current_stage_name in ACTIVE_JOB_STAGES:
                        try:current_queue_status=json.loads((current_job_root/'status.json').read_text()).get('status')
                        except (OSError,ValueError,TypeError):current_queue_status=None
                        if current_queue_status=='cancelled':
                            update_job_status(current_job_root,'interrupted',summary='사용자가 중지를 요청했습니다.',error='작업이 중지되었습니다.')
                        else:
                            update_job_status(current_job_root,'completed' if current_prepare_flag and current_exit_code==0 else 'failed',summary='환경 준비 완료' if current_prepare_flag and current_exit_code==0 else '',error='' if current_exit_code==0 else f'실행 종료 코드 {current_exit_code}. 로그에서 원인을 확인하세요.')
            threading.Thread(target=monitor_writer_process,daemon=True).start()
            return {'id':current_job_identifier,'job_path':str(current_job_root)}

    def request_writer_cancellation(self,current_job_identifier):
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
        with self.request_lock_handle:
            current_status_values=read_yaml_document(current_job_root/'status.yaml')
            if current_status_values.get('id')!=current_job_identifier or current_status_values.get('stage') not in ACTIVE_JOB_STAGES:
                raise ValueError('대기 또는 실행 중인 작가 작업만 중지할 수 있습니다.')
            try:
                current_supervisor_record=json.loads((current_job_root/'queue-process.json').read_text())
                current_supervisor_pid=current_supervisor_record['pid']
                current_supervisor_identity=current_supervisor_record['identity']
                if type(current_supervisor_pid) is not int or not isinstance(current_supervisor_identity,str) or read_process_identity(current_supervisor_pid)!=current_supervisor_identity:
                    raise ValueError('작가 작업 실행기를 확인할 수 없습니다. 상태를 다시 조회하세요.')
            except (OSError,KeyError,TypeError) as current_supervisor_error:
                raise ValueError('작가 작업 실행기를 확인할 수 없습니다. 상태를 다시 조회하세요.') from current_supervisor_error
            current_cancel_value=cancel_gpu_generation(current_job_root)
            return {'id':current_job_identifier,'status':current_cancel_value['status'],'cancel_requested':True}

    def close_writer_worker(self):
        """공용 대기열 작업은 게이트웨이 종료 후에도 계속 실행한다."""
        return

    def read_writer_detail(self,current_job_identifier):
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
        if not current_job_root.is_dir():raise ValueError('작업이 없습니다.')
        current_result_values={'id':current_job_identifier,'job_path':str(current_job_root),'status':self.resolve_observed_status(read_yaml_document(current_job_root/'status.yaml'),current_job_root),'request':read_yaml_document(current_job_root/'request.yaml')}
        for current_record_name in ('proposal','result','search','application'):
            current_record_path=current_job_root/(current_record_name+'.yaml')
            if current_record_path.exists():
                current_record_values=read_yaml_document(current_record_path)
                if isinstance(current_record_values,dict):current_record_values.pop('snapshot_hashes',None)
                current_result_values[current_record_name]=current_record_values
        current_log_path=current_job_root/'execution.log'
        if current_log_path.exists():
            with current_log_path.open('rb') as current_log_stream:
                current_log_stream.seek(max(0,current_log_path.stat().st_size-MAXIMUM_LOG_BYTES))
                current_result_values['log']=current_log_stream.read().decode(errors='replace')
        else:current_result_values['log']=''
        return current_result_values

    def search_writer_history(self,current_query_text):
        if not isinstance(current_query_text,str) or len(current_query_text)>200:raise ValueError('검색어는 200자 이하의 문자열이어야 합니다.')
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_query_terms=current_query_text.casefold().split()
        current_history_records=[]
        for current_job_root in sorted((Path(current_config_values['state_root'])/'jobs').glob('*'),reverse=True):
            if not JOB_IDENTIFIER_PATTERN.fullmatch(current_job_root.name) or current_job_root.is_symlink() or not current_job_root.is_dir() or not (current_job_root/'status.yaml').is_file():continue
            current_status_values=self.resolve_observed_status(read_yaml_document(current_job_root/'status.yaml'),current_job_root)
            if current_status_values.get('id')!=current_job_root.name:raise ValueError('작업 이력의 ID가 경로와 일치하지 않습니다.')
            current_request_values=read_yaml_document(current_job_root/'request.yaml')
            current_mode_labels={'learn':'문서 학습','write':'작성 제안','deduplicate':'중복 검토','prepare':'환경 준비'}
            current_stage_labels={'queued':'대기','indexing':'학습','searching':'탐색','reasoning':'작성 판단','review':'변경 검토 대기','completed':'완료','applied':'적용 완료','failed':'실패','interrupted':'중단','preparing':'환경 준비'}
            current_search_text=' '.join(str(current_value) for current_value in (current_status_values.get('id',''),current_status_values.get('mode',''),current_mode_labels.get(current_status_values.get('mode'),''),current_status_values.get('stage',''),current_stage_labels.get(current_status_values.get('stage'),''),current_status_values.get('summary',''),current_status_values.get('error',''),current_request_values.get('prompt',''))).casefold()
            if all(current_term in current_search_text for current_term in current_query_terms):current_history_records.append(current_status_values)
        return {'jobs':current_history_records,'query':current_query_text,'count':len(current_history_records)}

    def observe_writer_history(self,current_page_request):
        """기존 작업 ID와 기록 단계만 읽는다. 문서·요청·복구 상태는 조회하지 않는다."""
        import hashlib
        import re
        import yaml
        if not isinstance(current_page_request,dict) or set(current_page_request)-{'offset','limit','snapshot','query'}:
            raise ValueError('작가 이력 관측 필드 오류')
        current_offset_value=current_page_request.get('offset',0)
        current_limit_value=current_page_request.get('limit',10)
        current_snapshot_value=current_page_request.get('snapshot')
        current_query_text=current_page_request.get('query','')
        if not isinstance(current_query_text,str) or len(current_query_text)>80 or (current_query_text and not re.fullmatch(r'[A-Za-z0-9_-]+',current_query_text)):
            raise ValueError('작가 이력 ID 검색 오류')
        current_query_text=current_query_text.casefold()
        if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
            raise ValueError('작가 이력 페이지 오류')
        if current_snapshot_value is not None and (not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)):
            raise ValueError('작가 이력 스냅샷 오류')
        if current_offset_value and current_snapshot_value is None:
            raise ValueError('후속 페이지에는 스냅샷이 필요합니다.')
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_job_root=Path(current_config_values['state_root'])/'jobs'
        current_job_paths=sorted((current_path_value for current_path_value in current_job_root.glob('*') if JOB_IDENTIFIER_PATTERN.fullmatch(current_path_value.name) and not current_path_value.is_symlink() and current_path_value.is_dir()),reverse=True)
        if current_query_text:current_job_paths=[current_path_value for current_path_value in current_job_paths if current_query_text in current_path_value.name.casefold()]
        current_job_identifiers=[current_path_value.name for current_path_value in current_job_paths]
        current_snapshot_payload={'ids':current_job_identifiers,'query':current_query_text} if current_query_text else current_job_identifiers
        current_snapshot_hash=hashlib.sha256(json.dumps(current_snapshot_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if current_snapshot_value is not None and current_snapshot_value!=current_snapshot_hash:
            raise ValueError('작가 이력이 변경되었습니다. 첫 페이지부터 다시 조회하세요.')
        current_output_records=[]
        for current_job_path in current_job_paths[current_offset_value:current_offset_value+current_limit_value]:
            current_stage_value='unknown'
            try:
                current_status_path=current_job_path/'status.yaml'
                if current_status_path.is_symlink():raise ValueError('상태 경로 오류')
                current_status_value=read_yaml_document(current_status_path)
                if not isinstance(current_status_value,dict) or current_status_value.get('id')!=current_job_path.name:
                    raise ValueError('상태 ID 오류')
                if current_status_value.get('stage') in ('queued','preparing','indexing','searching','reasoning','review','completed','applied','failed','interrupted'):
                    current_stage_value=current_status_value['stage']
            except (OSError,ValueError,TypeError,KeyError,yaml.YAMLError):
                pass
            current_output_records.append({'id':current_job_path.name,'recorded_status':current_stage_value,'status_source':'job' if current_stage_value!='unknown' else 'unavailable'})
        current_next_offset=current_offset_value+len(current_output_records)
        return {'records':current_output_records,'total':len(current_job_identifiers),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_job_identifiers) else None,'snapshot':current_snapshot_hash,'unavailable_count':0,'note':'기록 단계이며 실제 작업 생존·원본 적용 여부는 별도 확인해야 합니다.'}

    def delete_writer_history(self,current_job_identifier):
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
        with self.request_lock_handle, (Path(current_config_values['state_root'])/'submission.lock').open('a') as current_submission_lock, lock_workspace_state(current_config_values):
            fcntl.flock(current_submission_lock,fcntl.LOCK_EX)
            if not current_job_root.is_dir():raise ValueError('작업이 없습니다.')
            current_status_values=self.resolve_observed_status(read_yaml_document(current_job_root/'status.yaml'),current_job_root)
            if current_status_values['stage'] in ACTIVE_JOB_STAGES:raise ValueError('대기 또는 실행 중인 작업은 삭제할 수 없습니다.')
            current_application_path=current_job_root/'application.yaml'
            if current_application_path.exists() and read_yaml_document(current_application_path).get('status') in ('applying','rollback_conflict'):
                raise ValueError('원본 적용 복구가 필요한 기록은 삭제할 수 없습니다.')
            current_execution_path=current_job_root/'execution.lock'
            if current_execution_path.is_symlink():raise ValueError('작업 실행 잠금이 올바르지 않습니다.')
            with current_execution_path.open('a') as current_execution_lock:
                try:fcntl.flock(current_execution_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError as current_lock_error:raise ValueError('작업 종료 기록 저장 중입니다. 잠시 후 다시 시도하세요.') from current_lock_error
                current_trash_root=Path(current_config_values['state_root'])/'.history-trash'
                current_trash_root.mkdir(mode=0o700,exist_ok=True)
                if current_trash_root.is_symlink():raise ValueError('휴지통 경로가 올바르지 않습니다.')
                current_destination_path=current_trash_root/current_job_identifier
                if current_destination_path.exists():raise ValueError('동일한 휴지통 기록이 있습니다.')
                current_job_root.rename(current_destination_path)
        return {'id':current_job_identifier,'status':'deleted','recoverable':True}

    def handle_writer_request(self,current_http_handler):
        current_url_parts=urlsplit(current_http_handler.path)
        if current_url_parts.path!=WRITER_ROUTE_PREFIX and not current_url_parts.path.startswith(WRITER_ROUTE_PREFIX+'/'):return False
        def send_writer_response(current_status_code,current_response_values,current_content_type='application/json; charset=utf-8'):
            current_response_bytes=current_response_values if isinstance(current_response_values,bytes) else json.dumps(current_response_values,ensure_ascii=False).encode()
            current_http_handler.send_response(current_status_code)
            current_http_handler.send_header('Content-Type',current_content_type)
            current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
            current_http_handler.send_header('Cache-Control','no-store')
            current_http_handler.send_header('X-Content-Type-Options','nosniff')
            current_http_handler.end_headers()
            current_http_handler.wfile.write(current_response_bytes)
        try:
            current_origin_text=f'http://127.0.0.1:{current_http_handler.server.server_port}'
            if current_http_handler.headers.get('Host')!=current_origin_text.removeprefix('http://'):raise ValueError('허용하지 않는 Host')
            current_route_path=current_url_parts.path
            if current_http_handler.command=='GET':
                if current_route_path in {WRITER_ROUTE_PREFIX,WRITER_ROUTE_PREFIX+'/',WRITER_ROUTE_PREFIX+'/embedded/'}:send_writer_response(200,Path(__file__).with_name('manager.html').read_bytes(),'text/html; charset=utf-8')
                elif current_route_path==WRITER_ROUTE_PREFIX+'/manager.js':send_writer_response(200,Path(__file__).with_name('manager.js').read_bytes(),'text/javascript; charset=utf-8')
                elif current_route_path==WRITER_ROUTE_PREFIX+'/api/state':send_writer_response(200,self.read_workspace_state())
                elif current_route_path==WRITER_ROUTE_PREFIX+'/api/token':send_writer_response(200,{'csrf_token':self.csrf_token_value})
                elif current_route_path==WRITER_ROUTE_PREFIX+'/api/job':
                    current_query_values=parse_qs(current_url_parts.query,strict_parsing=True)
                    if set(current_query_values)!={'id'} or len(current_query_values['id'])!=1:raise ValueError('작업 조회 인자 오류')
                    send_writer_response(200,self.read_writer_detail(current_query_values['id'][0]))
                else:send_writer_response(404,{'error':'지원하지 않는 경로'})
                return True
            if current_http_handler.command!='POST' or current_http_handler.headers.get('Origin')!=current_origin_text or current_http_handler.headers.get('X-Writer-Token')!=self.csrf_token_value:raise ValueError('동일 출처·작가 세션 확인 실패')
            if current_http_handler.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON 요청이 필요합니다.')
            current_body_length=int(current_http_handler.headers.get('Content-Length','0'))
            if not 1<=current_body_length<=MAXIMUM_REQUEST_BYTES:raise ValueError('요청 크기 오류')
            current_request_values=parse_unique_json(current_http_handler.rfile.read(current_body_length).decode())
            if current_route_path==WRITER_ROUTE_PREFIX+'/api/index-status':
                if current_request_values!={}:raise ValueError('색인 상태 조회에는 입력을 전달할 수 없습니다.')
                from .index import load_current_index
                try:
                    load_current_index(load_workspace_config(self.workspace_config_path))
                    current_index_status='fresh'
                except ValueError as current_index_error:
                    current_index_status='stale' if '색인이 오래되었습니다' in str(current_index_error) else 'unavailable'
                except (OSError,sqlite3.Error,TypeError,KeyError):
                    current_index_status='unavailable'
                send_writer_response(200,{'status':current_index_status})
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/detail':
                if not isinstance(current_request_values,dict) or set(current_request_values)!={'id'}:raise ValueError('작업 조회 필드 오류')
                send_writer_response(200,self.read_writer_detail(current_request_values['id']))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/cancel':
                if not isinstance(current_request_values,dict) or set(current_request_values)!={'id'}:raise ValueError('작업 중지 필드 오류')
                send_writer_response(200,self.request_writer_cancellation(current_request_values['id']))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/history/observe':
                send_writer_response(200,self.observe_writer_history(current_request_values))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/history':
                if not isinstance(current_request_values,dict) or set(current_request_values)!={'query'}:raise ValueError('이력 검색 필드 오류')
                send_writer_response(200,self.search_writer_history(current_request_values['query']))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/history/delete':
                if not isinstance(current_request_values,dict) or set(current_request_values)!={'id'}:raise ValueError('이력 삭제 필드 오류')
                send_writer_response(200,self.delete_writer_history(current_request_values['id']))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/jobs':send_writer_response(202,self.launch_writer_process(current_request_values))
            elif current_route_path==WRITER_ROUTE_PREFIX+'/api/apply':
                if not isinstance(current_request_values,dict) or set(current_request_values)!={'id','proposal_hash'}:raise ValueError('변경 적용 요청 필드 오류')
                current_config_values=load_workspace_config(self.workspace_config_path)
                current_job_root=resolve_job_directory(current_config_values,current_request_values['id'])
                with self.request_lock_handle,lock_workspace_state(current_config_values):
                    current_status_values=read_yaml_document(current_job_root/'status.yaml')
                    current_proposal_hash=calculate_content_hash((current_job_root/'proposal.yaml').read_bytes())
                    if current_status_values['stage']!='review' or current_request_values['proposal_hash']!=current_proposal_hash or current_status_values['proposal_hash']!=current_proposal_hash:raise ValueError('조회한 제안과 현재 제안이 다르거나 적용할 수 없는 상태입니다.')
                    current_application_values=apply_reviewed_proposal(current_config_values,current_job_root,read_yaml_document(current_job_root/'proposal.yaml'))
                    update_job_status(current_job_root,'applied',summary='변경 적용 완료 · 다음 작업 전 학습 갱신 필요')
                    send_writer_response(200,current_application_values)
            else:send_writer_response(404,{'error':'지원하지 않는 작업 경로'})
        except (ValueError,KeyError,TypeError,OSError,RuntimeError) as current_request_error:
            send_writer_response(400,{'error':str(current_request_error)})
        return True
