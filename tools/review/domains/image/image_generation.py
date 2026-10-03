"""로컬 관리도구의 고정 이미지 생성 API. 작업은 직렬 실행한다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
import json
import re
import subprocess
import threading
import uuid
import os
import signal
import shutil
from tools.review.domains.image.image_runtime import validate_image_runtime
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation, resume_gpu_generation

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[4]
IMAGE_JOB_ROOT = WORKFLOW_ROOT_PATH / '.tmp/test/qwen-image-2512'
IMAGE_REQUEST_LIMIT = 32768
MANAGER_HISTORY_ROOT = WORKFLOW_ROOT_PATH / ".tmp/manager-current"
MANAGER_HISTORY_LOCK = threading.Lock()


def parse_unique_request(current_pair_values):
    current_request_record = {}
    for current_key_name, current_key_value in current_pair_values:
        if current_key_name in current_request_record:
            raise ValueError('중복 요청 필드')
        current_request_record[current_key_name] = current_key_value
    return current_request_record


def validate_image_request(current_request_record):
    if isinstance(current_request_record,dict) and current_request_record.get('action')=='generate':
        current_request_record=dict(current_request_record)
        current_request_record.setdefault('seed',251204)
        if type(current_request_record['seed']) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('seed는 0~4294967295 범위의 정수여야 합니다.')
    if not isinstance(current_request_record, dict):
        raise ValueError('JSON 객체가 필요합니다.')
    if current_request_record.get('action') == 'prepare' and set(current_request_record) == {'action'}:
        return current_request_record
    if set(current_request_record)-{'action','prompt','width','height','steps','seed','tag'} or not {'action','prompt','width','height','steps','seed'} <= set(current_request_record) or current_request_record['action'] != 'generate':
        raise ValueError('요청 필드 오류')
    from tools.review.common.generation_records import validate_history_tag
    current_request_record['tag']=validate_history_tag(current_request_record.get('tag',''))
    if not isinstance(current_request_record['prompt'],str) or not 1 <= len(current_request_record['prompt'].strip()) <= 8000:
        raise ValueError('프롬프트는 1~8000자여야 합니다.')
    if type(current_request_record['steps']) is not int or current_request_record['steps'] not in (4,30):
        raise ValueError('생성 스텝은 4 또는 30이어야 합니다.')
    for current_size_key in ('width','height'):
        current_size_value = current_request_record[current_size_key]
        if type(current_size_value) is not int or not 256 <= current_size_value <= 1664 or current_size_value % 16 != 0:
            raise ValueError('지원하지 않는 해상도입니다.')
    return current_request_record


def summarize_generation_progress(current_log_text, current_job_status):
    current_step_matches = re.findall(r'(?:denoise |heartbeat[^\n]*?)?step=(\d+)/(\d+)', current_log_text)
    current_log_text = current_log_text.replace("'stage': '", 'stage=')
    current_stage_matches = re.findall(r'stage[=\": ]+[\"\']?([a-z-]+)', current_log_text)
    current_stage_value = current_stage_matches[-1] if current_stage_matches else 'starting'
    if current_step_matches:
        current_step_value, total_step_count = map(int,current_step_matches[-1])
        return {'stage':current_job_status if current_job_status!='running' else ('saving' if current_step_value==total_step_count else 'inference'), 'step':current_step_value,'total':total_step_count,'percent':round(current_step_value*100/total_step_count) if total_step_count else None}
    return {'stage':current_job_status if current_job_status!='running' else current_stage_value,'step':0,'total':None,'percent':100 if current_job_status=='completed' else None}


class ImageGenerationManager:
    def __init__(self, *, three_reference_mode=False):
        self.three_reference_mode = three_reference_mode
        self.route_prefix_value = "/image-generation-2511" if three_reference_mode else "/image-generation"
        self.job_storage_root = WORKFLOW_ROOT_PATH / ".tmp/test/qwen-image-2511-three-reference" if three_reference_mode else IMAGE_JOB_ROOT
        self.current_worker_process = None
        self.current_job_identifier = None
        self.current_request_lock = threading.Lock()

    def enrich_generation_status(self, current_job_root, current_status_record):
        return current_status_record

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        """작업 로그 끝부분에서 확인 가능한 진행 정보만 상태에 보강한다."""
        current_status_path=current_job_root/'status.json'
        current_status_record=json.loads(current_status_path.read_text()) if current_status_path.exists() else (fallback_status_record or {'status':'missing'})
        current_log_path=current_job_root/'worker.log'
        if current_log_path.exists() and (include_log_value or current_status_record['status'] in ('queued','running')):
            with current_log_path.open('rb') as current_log_handle:
                current_log_handle.seek(max(0,current_log_path.stat().st_size-12000))
                current_status_record['log']=current_log_handle.read().decode(errors='replace')
        current_progress_record=summarize_generation_progress(current_status_record.get('log',''),current_status_record['status'])
        if current_status_record['status']=='queued' and isinstance(current_status_record.get('queue_position'),int):
            current_progress_record['queue_position']=current_status_record['queue_position']
        current_status_record['progress']=current_progress_record
        current_status_record['log_updated_at']=current_log_path.stat().st_mtime if current_log_path.exists() else None
        return current_status_record

    def validate_generation_request(self, request_record_value):
        if self.three_reference_mode:
            from tools.review.domains.image.three_reference_generation import validate_three_reference_request
            return validate_three_reference_request(request_record_value)
        return validate_image_request(request_record_value)

    def validate_generation_resume(self, selected_job_directory):
        """도메인별 재개 가능 기록을 GPU 명령 실행 전에 검증한다."""

    def validate_generation_runtime(self, saved_request_record=None):
        validate_image_runtime()

    def select_generation_runner(self, saved_request_record=None):
        saved_request_record = saved_request_record or {}
        if self.three_reference_mode or saved_request_record.get('references'):
            return 'generators/image/run_qwen_2511_three_reference.py'
        return 'generators/image/run_qwen_2512.py'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / ('qwen-2511' if self.three_reference_mode else 'qwen-2512')

    def reset_generation_history(self):
        return self.clear_image_generation_files()

    def clear_image_generation_files(self):
        """현재 생성기의 종료된 작업 폴더와 이력을 함께 삭제한다."""
        with self.current_request_lock, MANAGER_HISTORY_LOCK:
            if self.current_worker_process is not None and self.current_worker_process.poll() is None:
                raise ValueError('생성 중에는 초기화할 수 없습니다. 완료 또는 취소 후 다시 실행하세요.')
            if self.job_storage_root.is_symlink():
                raise ValueError('심볼릭 링크 작업 저장소는 초기화할 수 없습니다.')
            deletion_target_paths = []
            for current_job_root in self.job_storage_root.iterdir() if self.job_storage_root.is_dir() else []:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-(?:[a-f0-9]{8}|prepare)', current_job_root.name):
                    continue
                if current_job_root.is_symlink():
                    raise ValueError('심볼릭 링크 작업 경로는 삭제할 수 없습니다.')
                if not current_job_root.is_dir():
                    continue
                current_status_path = current_job_root / 'status.json'
                if not current_status_path.is_file():
                    raise ValueError(f'작업 상태 파일이 없어 초기화할 수 없습니다: {current_job_root.name}')
                current_status_value = json.loads(current_status_path.read_text()).get('status')
                if current_status_value not in ('completed', 'failed', 'cancelled'):
                    raise ValueError(f'종료되지 않은 작업이 있어 초기화할 수 없습니다: {current_job_root.name} ({current_status_value})')
                deletion_target_paths.append(current_job_root)
            for current_job_root in deletion_target_paths:
                shutil.rmtree(current_job_root)
            for current_record_path in self.history_storage_path().glob('*.json'):
                current_record_path.unlink()
            self.current_job_identifier = None

    def delete_generation_history(self, generation_job_identifier):
        """선택한 종료 작업의 입력·결과·로그와 이력을 함께 삭제한다."""
        if not isinstance(generation_job_identifier, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', generation_job_identifier):
            raise ValueError('삭제할 생성 ID 형식이 올바르지 않습니다.')
        current_history_path = self.history_storage_path() / (generation_job_identifier + '.json')
        current_job_root = self.job_storage_root / generation_job_identifier
        with self.current_request_lock, MANAGER_HISTORY_LOCK:
            if self.job_storage_root.is_symlink() or current_job_root.is_symlink():
                raise ValueError('심볼릭 링크 작업 경로는 삭제할 수 없습니다.')
            if not current_job_root.is_dir():
                raise ValueError('생성 작업 경로를 찾을 수 없습니다.')
            current_status_path = current_job_root / 'status.json'
            if not current_status_path.is_file():
                raise ValueError('작업 상태 파일이 없어 삭제할 수 없습니다.')
            current_status_record = json.loads(current_status_path.read_text())
            if current_status_record.get('status') not in ('completed', 'failed', 'cancelled'):
                raise ValueError('종료되지 않은 작업은 먼저 중지한 뒤 삭제하세요.')
            shutil.rmtree(current_job_root)
            current_history_path.unlink(missing_ok=True)
            if self.current_job_identifier == generation_job_identifier:
                self.current_job_identifier = None
        return {'deleted': generation_job_identifier, 'files_preserved': False}

    def list_generation_history(self):
        current_history_records = []
        with MANAGER_HISTORY_LOCK:
            for current_record_path in sorted(self.history_storage_path().glob('*.json'), reverse=True):
                current_history_record = json.loads(current_record_path.read_text())
                current_job_root = self.job_storage_root / current_history_record['id']
                current_history_record['path'] = str(current_job_root.resolve())
                current_history_record['status'] = self.read_generation_status_record(current_job_root,current_history_record.get('status',{'status':'missing'}))
                current_history_record['progress'] = current_history_record['status']['progress']
                current_history_record['image'] = f"{self.route_prefix_value}/jobs/{current_history_record['id']}/result.png" if (current_job_root/'result.png').exists() else None
                current_history_records.append(current_history_record)
        return current_history_records

    def handle_image_request(self, current_http_handler):
        current_url_path = urlsplit(current_http_handler.path).path
        if not (current_url_path==self.route_prefix_value or current_url_path.startswith(self.route_prefix_value+'/')):
            return False
        def send_response_data(current_status_code, current_response_value, current_content_type='application/json; charset=utf-8'):
            current_response_bytes = current_response_value if isinstance(current_response_value,bytes) else json.dumps(current_response_value,ensure_ascii=False).encode()
            current_http_handler.send_response(current_status_code)
            current_http_handler.send_header('Content-Type',current_content_type)
            current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
            current_http_handler.send_header('Cache-Control','no-store')
            current_http_handler.end_headers()
            current_http_handler.wfile.write(current_response_bytes)
        try:
            expected_origin_value = f'http://127.0.0.1:{current_http_handler.server.server_port}'
            if current_http_handler.headers.get('Host') != expected_origin_value.removeprefix('http://'):
                raise ValueError('허용하지 않는 Host')
            if current_http_handler.command == 'POST':
                if current_http_handler.headers.get('Origin') != expected_origin_value:
                    raise ValueError('동일 출처 요청만 허용합니다.')
                history_delete_match=re.fullmatch(re.escape(self.route_prefix_value)+r'/history/([0-9]{4}-[0-9-]{5}_[0-9-]{8}-[a-f0-9]{8})/delete',current_url_path)
                if (current_url_path not in (self.route_prefix_value+'/jobs',self.route_prefix_value+'/history/reset',self.route_prefix_value+'/cancel',self.route_prefix_value+'/resume') and history_delete_match is None) or current_http_handler.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise ValueError('요청 경로 또는 형식 오류')
                current_body_length = int(current_http_handler.headers.get('Content-Length','0'))
                if not 1 <= current_body_length <= (getattr(self, 'reference_request_limit', 12_100_000) if self.three_reference_mode or getattr(self,'reference_upload_enabled',False) else IMAGE_REQUEST_LIMIT):
                    raise ValueError('요청 크기 오류')
                current_request_record = json.loads(current_http_handler.rfile.read(current_body_length),object_pairs_hook=parse_unique_request)
                if current_url_path in (self.route_prefix_value+'/cancel',self.route_prefix_value+'/resume'):
                    if not isinstance(current_request_record,dict) or set(current_request_record)!={'id'} or not re.fullmatch(r'[0-9a-f_-]+',current_request_record['id']):
                        raise ValueError('작업 ID 형식 오류')
                    selected_job_directory=self.job_storage_root/current_request_record['id']
                    if current_url_path.endswith('/resume'):
                        saved_request_record=json.loads((selected_job_directory/'request.json').read_text())
                        self.validate_generation_runtime(saved_request_record)
                    if current_url_path.endswith('/resume'):
                        self.validate_generation_resume(selected_job_directory)
                    if current_url_path.endswith('/resume') and not (selected_job_directory/'gpu-command.json').exists():
                        saved_request_record=json.loads((selected_job_directory/'request.json').read_text())
                        saved_command_values=[str(WORKFLOW_ROOT_PATH/'.venv/bin/python'),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(saved_request_record)),'--job-dir',str(selected_job_directory)]
                        (selected_job_directory/'gpu-command.json').write_text(json.dumps({'command':saved_command_values,'service':'image'}))
                    selected_operation_result=(resume_gpu_generation if current_url_path.endswith('/resume') else cancel_gpu_generation)(selected_job_directory)
                    send_response_data(200,selected_operation_result)
                    return True
                if current_url_path == self.route_prefix_value+'/history/reset':
                    if current_request_record != {'action':'reset'}:
                        raise ValueError('초기화 요청 필드 오류')
                    self.reset_generation_history()
                    send_response_data(200,{'status':'cleared'})
                    return True
                if history_delete_match is not None:
                    generation_job_identifier=history_delete_match.group(1)
                    if current_request_record != {'id':generation_job_identifier}:
                        raise ValueError('이력 삭제 요청 필드 오류')
                    send_response_data(200,self.delete_generation_history(generation_job_identifier))
                    return True
                current_request_record=self.validate_generation_request(current_request_record)
                self.validate_generation_runtime(current_request_record)
                with self.current_request_lock:
                    current_job_identifier = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
                    current_job_root = self.job_storage_root / current_job_identifier
                    current_job_root.mkdir(parents=True,exist_ok=False)
                    if self.three_reference_mode or current_request_record.get('images'):
                        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
                        reference_request_record=save_three_reference_inputs(current_job_root,current_request_record)
                        current_request_record={**{key:value for key,value in current_request_record.items() if key!='images'},**reference_request_record}
                    else:
                        current_request_record.pop('images',None)
                    (current_job_root/'request.json').write_text(json.dumps(current_request_record,ensure_ascii=False))
                    (current_job_root/'status.json').write_text('{"status":"running"}')
                    with MANAGER_HISTORY_LOCK:
                        self.history_storage_path().mkdir(parents=True,exist_ok=True)
                        (self.history_storage_path()/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier,'created_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'request':current_request_record,'status':{'status':'running'},'job_path':str(current_job_root)},ensure_ascii=False))
                    with (current_job_root/'worker.log').open('w') as current_log_handle:
                        self.current_worker_process = launch_gpu_process([str(WORKFLOW_ROOT_PATH/'.venv/bin/python'),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_record)),'--job-dir',str(current_job_root)],current_job_root,'image',stdout=current_log_handle,stderr=subprocess.STDOUT,start_new_session=True)
                    self.current_job_identifier = current_job_identifier
                    current_worker_process = self.current_worker_process
                    def watch_worker_exit():
                        current_exit_code = current_worker_process.wait()
                        with self.current_request_lock:
                            current_status_record = json.loads((current_job_root/'status.json').read_text())
                            if current_status_record['status'] in ('running','queued'):
                                (current_job_root/'status.json').write_text(json.dumps({'status':'failed','error':f'작업자 종료 코드 {current_exit_code}. 로그를 확인하세요.'},ensure_ascii=False))
                            with MANAGER_HISTORY_LOCK:
                                current_history_path=self.history_storage_path()/(current_job_identifier+'.json')
                                if current_history_path.exists():
                                    current_history_record=json.loads(current_history_path.read_text())
                                    current_history_record['status']=json.loads((current_job_root/'status.json').read_text())
                                    current_history_path.write_text(json.dumps(current_history_record,ensure_ascii=False))
                    threading.Thread(target=watch_worker_exit,daemon=True).start()
                current_status_record=json.loads((current_job_root/'status.json').read_text())
                send_response_data(202,{'id':current_job_identifier,'status':current_status_record['status']})
            elif current_url_path == self.route_prefix_value+'/active':
                active_history_records=[record_value for record_value in self.list_generation_history() if record_value.get('status',{}).get('status') in ('queued','running')]
                send_response_data(200,{'running':bool(active_history_records),'id':active_history_records[0]['id'] if active_history_records else None})
            elif current_url_path == self.route_prefix_value+'/history':
                send_response_data(200,{'records':self.list_generation_history()})
            elif current_url_path == self.route_prefix_value+'/model-status':
                if self.select_generation_runner().endswith('run_qwen_21_reference.py'):
                    try:
                        self.validate_generation_runtime()
                        send_response_data(200, {'ready': True, 'message': 'Qwen Image 2.1 로컬 모델·실행 환경 준비됨'})
                    except (ValueError, OSError) as current_model_error:
                        send_response_data(200, {'ready': False, 'message': str(current_model_error)})
                elif self.select_generation_runner().endswith('run_qwen_2511_three_reference.py'):
                    send_response_data(200,{'ready':False,'message':'2511 모델 준비 상태는 생성 시 검증합니다.'})
                else:
                    import sys
                    sys.path.insert(0,str(WORKFLOW_ROOT_PATH/'generators/image'))
                    from qwen_2512 import validate_qwen_2512_assets
                    try:
                        validate_qwen_2512_assets(verify_adapter_hash=False)
                        send_response_data(200,{'ready':True,'message':'모델·Lightning 파일 준비됨. 생성 시 해시를 검증합니다.'})
                    except (ValueError,FileNotFoundError) as current_model_error:
                        send_response_data(200,{'ready':False,'message':str(current_model_error)})
            elif current_url_path in (self.route_prefix_value,self.route_prefix_value+'/'):
                send_response_data(410,{'error':'이전 관리 화면은 폐기되었습니다. /management/에서 Gradio 화면을 여세요.'})
            else:
                current_path_match = re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/([0-9]{4}-[0-9-]{5}_[0-9-]{8}-[a-f0-9]{8})(/grid-input.png|/grid-edited.png|/tiled-preview.png|/result.png|/single-tile.png|/square-crop.png|/center-tile.png|/quadrilateral.png|/border-crop.png|/worker.log|/reference-(?:[1-9]|10)\.png)?',current_url_path)
                if not current_path_match:
                    send_response_data(404,{'error':'작업 경로 없음'})
                    return True
                current_job_root = self.job_storage_root/current_path_match[1]
                if current_path_match[2]:
                    current_output_name=current_path_match[2][1:]
                    send_response_data(200,(current_job_root/current_output_name).read_bytes(),'image/png' if current_output_name.endswith('.png') else 'text/plain; charset=utf-8')
                else:
                    current_status_record=self.read_generation_status_record(current_job_root,include_log_value=True)
                    current_status_record['log_url']=f'{self.route_prefix_value}/jobs/{current_path_match[1]}/worker.log'
                    current_status_record['image']=f'{self.route_prefix_value}/jobs/{current_path_match[1]}/result.png' if (current_job_root/'result.png').exists() else None
                    send_response_data(200,self.enrich_generation_status(current_job_root,current_status_record))
        except (ValueError,FileNotFoundError) as current_error_value:
            send_response_data(400,{'error':str(current_error_value)})
        return True
