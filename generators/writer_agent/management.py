"""로컬 관리도구의 작가 에이전트 요청·작업·변경 미리보기 API."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json
import os
import signal
import subprocess
import sys
import threading
import uuid
from .documents import (DEFAULT_WORKSPACE_CONFIG,WORKFLOW_REPOSITORY_ROOT,load_workspace_config,read_yaml_document,save_yaml_document,parse_unique_json,calculate_content_hash,lock_workspace_state)
from .jobs import create_writer_job,resolve_job_directory,update_job_status
from .agent import apply_reviewed_proposal
from . import prepare

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
        self.csrf_token_value=uuid.uuid4().hex

    def read_workspace_state(self):
        current_ready_flag=(prepare.RUNTIME_INSTALL_ROOT/'prepared.json').is_file()
        current_state_values={'configured':self.workspace_config_path.is_file(),'ready':current_ready_flag,'csrf_token':self.csrf_token_value,'config_path':str(self.workspace_config_path),'active_job':self.worker_job_identifier if self.worker_process_handle and self.worker_process_handle.poll() is None else None,'jobs':[]}
        if not current_state_values['configured']:return current_state_values
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_state_values.update({'document_root':current_config_values['document_root'],'state_root':current_config_values['state_root'],'index_path':str(Path(current_config_values['state_root'])/'rag.sqlite3'),'trained':(Path(current_config_values['state_root'])/'rag.sqlite3').is_file()})
        for current_job_root in sorted((Path(current_config_values['state_root'])/'jobs').glob('*'),reverse=True)[:40]:
            if not current_job_root.is_dir() or current_job_root.is_symlink() or not (current_job_root/'status.yaml').is_file():continue
            current_status_values=read_yaml_document(current_job_root/'status.yaml')
            if current_status_values['stage'] in ACTIVE_JOB_STAGES and current_job_root.name!=current_state_values['active_job']:
                current_status_values={**current_status_values,'stage':'interrupted','error':'실행 프로세스와 연결되지 않은 작업입니다. 로그를 확인하고 새 작업으로 실행하세요.'}
            current_state_values['jobs'].append(current_status_values)
        return current_state_values

    def launch_writer_process(self,current_request_values):
        current_config_values=load_workspace_config(self.workspace_config_path)
        with self.request_lock_handle:
            if self.worker_process_handle and self.worker_process_handle.poll() is None:raise ValueError('이미 작가 에이전트 작업이 실행 중입니다.')
            current_prepare_flag=current_request_values=={'mode':'prepare','prompt':''}
            if not current_prepare_flag and not prepare.RUNTIME_PYTHON_PATH.is_file():raise ValueError('먼저 환경 준비를 실행하세요.')
            current_job_identifier=create_writer_job(current_config_values,{'mode':'learn','prompt':''} if current_prepare_flag else current_request_values)
            current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
            if current_prepare_flag:
                save_yaml_document(current_job_root/'request.yaml',current_request_values)
                update_job_status(current_job_root,'preparing',mode='prepare')
                current_command_values=[sys.executable,str(Path(__file__).with_name('prepare.py')),'--run-dir',str(current_job_root)]
            else:current_command_values=[str(prepare.RUNTIME_PYTHON_PATH),'-m','generators.writer_agent.jobs','--config',str(self.workspace_config_path),'--job-id',current_job_identifier]
            with (current_job_root/'worker.log').open('w') as current_worker_log:
                self.worker_process_handle=subprocess.Popen(current_command_values,cwd=WORKFLOW_REPOSITORY_ROOT,stdout=current_worker_log,stderr=subprocess.STDOUT,start_new_session=True)
            self.worker_job_identifier=current_job_identifier
            current_worker_process=self.worker_process_handle
            def monitor_writer_process():
                current_exit_code=current_worker_process.wait()
                with self.request_lock_handle:
                    current_stage_name=read_yaml_document(current_job_root/'status.yaml')['stage']
                    if current_stage_name in ACTIVE_JOB_STAGES:
                        update_job_status(current_job_root,'completed' if current_prepare_flag and current_exit_code==0 else 'failed',summary='환경 준비 완료' if current_prepare_flag and current_exit_code==0 else '',error='' if current_exit_code==0 else f'실행 종료 코드 {current_exit_code}. 로그에서 원인을 확인하세요.')
            threading.Thread(target=monitor_writer_process,daemon=True).start()
            return {'id':current_job_identifier,'job_path':str(current_job_root)}

    def close_writer_worker(self):
        with self.request_lock_handle:
            current_worker_process=self.worker_process_handle
            if current_worker_process and current_worker_process.poll() is None:
                os.killpg(current_worker_process.pid,signal.SIGTERM)
                try:current_worker_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(current_worker_process.pid,signal.SIGKILL)
                    current_worker_process.wait()

    def read_writer_detail(self,current_job_identifier):
        current_config_values=load_workspace_config(self.workspace_config_path)
        current_job_root=resolve_job_directory(current_config_values,current_job_identifier)
        if not current_job_root.is_dir():raise ValueError('작업이 없습니다.')
        current_result_values={'id':current_job_identifier,'job_path':str(current_job_root),'status':read_yaml_document(current_job_root/'status.yaml'),'request':read_yaml_document(current_job_root/'request.yaml')}
        for current_record_name in ('proposal','result','search','application'):
            current_record_path=current_job_root/(current_record_name+'.yaml')
            if current_record_path.exists():
                current_record_values=read_yaml_document(current_record_path)
                if isinstance(current_record_values,dict):current_record_values.pop('snapshot_hashes',None)
                current_result_values[current_record_name]=current_record_values
        current_log_path=current_job_root/'worker.log'
        if current_log_path.exists():
            with current_log_path.open('rb') as current_log_stream:
                current_log_stream.seek(max(0,current_log_path.stat().st_size-MAXIMUM_LOG_BYTES))
                current_result_values['log']=current_log_stream.read().decode(errors='replace')
        else:current_result_values['log']=''
        return current_result_values

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
                if current_route_path in {WRITER_ROUTE_PREFIX,WRITER_ROUTE_PREFIX+'/'}:send_writer_response(200,Path(__file__).with_name('manager.html').read_bytes(),'text/html; charset=utf-8')
                elif current_route_path==WRITER_ROUTE_PREFIX+'/manager.js':send_writer_response(200,Path(__file__).with_name('manager.js').read_bytes(),'text/javascript; charset=utf-8')
                elif current_route_path==WRITER_ROUTE_PREFIX+'/api/state':send_writer_response(200,self.read_workspace_state())
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
            if current_route_path==WRITER_ROUTE_PREFIX+'/api/jobs':send_writer_response(202,self.launch_writer_process(current_request_values))
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
