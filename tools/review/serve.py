"""워크플로우 실행 결과·제작 자산의 로컬 읽기 전용 공통 검수 서버."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.ui_assets import resolve_review_ui_asset
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import io
import hashlib
import json
import shutil
import subprocess
import threading
import time
import traceback
import signal

REVIEW_SERVER_HOST = '127.0.0.1'
REVIEW_SERVER_PORT = 8770
DEFAULT_FRONTEND_REPOSITORY = Path(__file__).resolve().parents[3]/'slime-frontend'
REVIEW_ALLOWED_SUFFIXES = {'.html', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.js', '.css', '.mp4', '.svg', '.woff', '.woff2'}
REVIEW_HEARTBEAT_SECONDS = 5
REVIEW_SERVER_RETRY_SECONDS = 3
REVIEW_LIVE_RELOAD_PATH = '/__review_live_reload__'
REVIEW_LIVE_RELOAD_SCRIPT = b'''<script id="review-live-reload">(()=>{let instanceId;const poll=async()=>{try{const response=await fetch('/__review_live_reload__',{cache:'no-store'});if(!response.ok)throw new Error('watch unavailable');const nextInstanceId=(await response.json()).instanceId;if(instanceId&&instanceId!==nextInstanceId){location.reload();return}instanceId=nextInstanceId}catch(_error){}finally{setTimeout(poll,1000)}};poll()})()</script>'''

def is_review_live_reload_request(request_path):
    return urlsplit(request_path).path == REVIEW_LIVE_RELOAD_PATH

def inject_review_live_reload(html_content):
    if b'id="review-live-reload"' in html_content:
        return html_content
    closing_body_index = html_content.lower().rfind(b'</body>')
    if closing_body_index == -1:
        return html_content + REVIEW_LIVE_RELOAD_SCRIPT
    return html_content[:closing_body_index] + REVIEW_LIVE_RELOAD_SCRIPT + html_content[closing_body_index:]


def resolve_review_request(review_root_directory, requested_url_path, review_entry_path="preview.html"):
    decoded_request_path = unquote(urlsplit(requested_url_path).path)
    if decoded_request_path == '/': decoded_request_path = '/'+review_entry_path
    relative_request_parts = Path(decoded_request_path.lstrip('/')).parts
    if any(path_part_value.startswith('.') for path_part_value in relative_request_parts):
        raise ValueError('숨김 파일 또는 경로 이동 요청은 허용하지 않습니다.')
    resolved_asset_path = (review_root_directory/decoded_request_path.lstrip('/')).resolve()
    if not resolved_asset_path.is_relative_to(review_root_directory) or not resolved_asset_path.is_file() or resolved_asset_path.suffix.lower() not in REVIEW_ALLOWED_SUFFIXES:
        raise ValueError('허용된 검수 파일이 아닙니다.')
    return resolved_asset_path

def parse_review_arguments(command_argument_values=None):
    argument_value_parser=argparse.ArgumentParser(description=__doc__)
    source_argument_group=argument_value_parser.add_mutually_exclusive_group()
    source_argument_group.add_argument('--frontend-repo',type=Path,help='프론트엔드 저장소 (기본: 워크플로우 옆 slime-frontend)' )
    source_argument_group.add_argument('--root',type=Path,help='기존 검수 또는 관리도구 폴더')
    source_argument_group.add_argument('--walking',type=Path,help='관리도구에 묶을 걷기 검수 폴더')
    argument_value_parser.add_argument('--standing',type=Path,help='관리도구에 묶을 스탠딩 검수 폴더 (--walking과 함께 사용)')
    argument_value_parser.add_argument('--entry',default='preview.html',help='--root 폴더 기준 HTML 진입 페이지')
    argument_value_parser.add_argument('--port',type=int,default=REVIEW_SERVER_PORT,help='로컬 서버 포트 (기본: 8770)')
    argument_value_parser.add_argument('--ui-bundle',type=Path,help='프론트엔드에서 전달한 UI 검수 빌드 폴더')
    argument_value_parser.add_argument('--writer-agent-config',type=Path,help='작가 에이전트의 로컬 작업 공간 YAML')
    argument_value_parser.add_argument('--watch',action='store_true',help='소스 변경 시 검수 빌드를 다시 만들고 서버를 재시작')
    parsed_argument_values=argument_value_parser.parse_args(command_argument_values)
    if not any((parsed_argument_values.root, parsed_argument_values.walking, parsed_argument_values.frontend_repo, parsed_argument_values.standing)):
        parsed_argument_values.frontend_repo=DEFAULT_FRONTEND_REPOSITORY
    if parsed_argument_values.ui_bundle and not parsed_argument_values.frontend_repo:
        argument_value_parser.error('--ui-bundle은 프론트엔드 관리도구 생성 모드에서 사용하세요.')
    if bool(parsed_argument_values.walking) != bool(parsed_argument_values.standing):
        argument_value_parser.error('--walking과 --standing을 함께 지정하세요.')
    if (parsed_argument_values.walking or parsed_argument_values.frontend_repo) and parsed_argument_values.entry != 'preview.html':
        argument_value_parser.error('관리도구 생성 모드에서는 --entry를 변경할 수 없습니다.')
    if not 1024 <= parsed_argument_values.port <= 65535:
        argument_value_parser.error('포트는 1024~65535여야 합니다.')
    return parsed_argument_values

def collect_review_watch_paths(parsed_argument_values):
    workflow_repo_root = Path(__file__).resolve().parents[2]
    watch_paths = [Path(__file__).resolve(), workflow_repo_root/'tools/review', workflow_repo_root/'generators/animation', workflow_repo_root/'generators/worldbuilding', workflow_repo_root/'generators/writer_agent']
    current_writer_config=parsed_argument_values.writer_agent_config or workflow_repo_root/'.local/writer-agent/workspace.yaml'
    watch_paths.append(current_writer_config)
    if parsed_argument_values.frontend_repo:
        watch_paths.append(Path(parsed_argument_values.frontend_repo).resolve()/'src/assets')
    if parsed_argument_values.root:
        watch_paths.append(Path(parsed_argument_values.root).resolve())
    if parsed_argument_values.walking:
        watch_paths.extend([Path(parsed_argument_values.walking).resolve(), Path(parsed_argument_values.standing).resolve()])
    return tuple(path for path in watch_paths if path.exists())

def snapshot_review_watch_paths(watch_paths):
    watched_file_records = []
    for current_root_path in watch_paths:
        current_file_paths = [current_root_path] if current_root_path.is_file() else current_root_path.rglob('*')
        for current_file_path in current_file_paths:
            if not current_file_path.is_file() or current_file_path.suffix.lower() not in {'.py', '.html', '.css', '.js', '.json', '.yaml', '.yml', '.png', '.jpg', '.jpeg', '.webp'}:
                continue
            if any(current_path_part.startswith('.') for current_path_part in current_file_path.relative_to(current_root_path if current_root_path.is_dir() else current_root_path.parent).parts):
                continue
            watched_file_records.append((str(current_file_path), current_file_path.stat().st_mtime_ns, current_file_path.stat().st_size))
    return tuple(sorted(watched_file_records))

def run_review_watch_mode(parsed_argument_values):
    watch_paths = collect_review_watch_paths(parsed_argument_values)
    previous_watch_snapshot = snapshot_review_watch_paths(watch_paths)
    watch_command_arguments = [current_argument for current_argument in sys.argv[1:] if current_argument != '--watch']
    try:
        while True:
            review_server_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *watch_command_arguments])
            try:
                while review_server_process.poll() is None:
                    time.sleep(0.5)
                    current_watch_snapshot = snapshot_review_watch_paths(watch_paths)
                    if current_watch_snapshot != previous_watch_snapshot:
                        print(f'{datetime.now().isoformat()}/asset-review-server/watch 변경 감지, 검수 서버를 다시 시작합니다.', flush=True)
                        previous_watch_snapshot = current_watch_snapshot
                        review_server_process.terminate()
                        review_server_process.wait(timeout=5)
                        break
                else:
                    if review_server_process.returncode != 0:
                        print(f'{datetime.now().isoformat()}/asset-review-server/retry 서버가 종료 코드 {review_server_process.returncode}로 끝났습니다. {REVIEW_SERVER_RETRY_SECONDS}초 후 다시 시작합니다.', flush=True)
                        for retry_interval_index in range(REVIEW_SERVER_RETRY_SECONDS * 2):
                            time.sleep(0.5)
                            current_watch_snapshot = snapshot_review_watch_paths(watch_paths)
                            if current_watch_snapshot != previous_watch_snapshot:
                                previous_watch_snapshot = current_watch_snapshot
                                print(f'{datetime.now().isoformat()}/asset-review-server/watch 재시도 대기 중 변경 감지', flush=True)
                                break
                        continue
                    return
            finally:
                if review_server_process.poll() is None:
                    review_server_process.terminate()
                    review_server_process.wait(timeout=5)
            time.sleep(0.2)
    except KeyboardInterrupt:
        if 'review_server_process' in locals() and review_server_process.poll() is None:
            review_server_process.terminate()
            review_server_process.wait(timeout=5)
        print(f'{datetime.now().isoformat()}/asset-review-server/stop 감시 종료', flush=True)


def calculate_frontend_review_source_hash(frontend_repository_path):
    frontend_repository_path = Path(frontend_repository_path).resolve()
    source_file_paths = [frontend_repository_path/'package.json', frontend_repository_path/'package-lock.json', frontend_repository_path/'scripts/build_ui_review.sh', frontend_repository_path/'scripts/build-ui-review.mjs']
    source_file_paths.extend(sorted((frontend_repository_path/'src').rglob('*')))
    source_file_paths.extend(sorted((frontend_repository_path/'review').rglob('*')))
    digest_builder = hashlib.sha256()
    for source_file_path in source_file_paths:
        if source_file_path.is_file():
            digest_builder.update(source_file_path.relative_to(frontend_repository_path).as_posix().encode())
            digest_builder.update(source_file_path.read_bytes())
    return digest_builder.hexdigest()

def find_latest_ui_review_bundle(frontend_repository_path):
    workflow_temporary_root = Path(__file__).resolve().parents[2]/'.tmp'
    if __package__:
        from .import_ui_bundle import load_ui_bundle
    else:
        from import_ui_bundle import load_ui_bundle
    candidate_bundle_paths = sorted((current_path for current_path in workflow_temporary_root.glob('*/ui-review') if current_path.is_dir()), reverse=True)
    validation_errors = []
    for candidate_bundle_path in candidate_bundle_paths:
        try:
            load_ui_bundle(candidate_bundle_path)
            return candidate_bundle_path
        except (OSError, ValueError) as current_validation_error:
            validation_errors.append(f'{candidate_bundle_path}: {current_validation_error}')
    if not candidate_bundle_paths:
        raise ValueError('검증 가능한 UI 검수 빌드를 찾지 못했습니다.')
    raise ValueError('검증 가능한 UI 검수 빌드를 찾지 못했습니다. '+validation_errors[-1])

def ensure_frontend_ui_review_bundle(frontend_repository_path):
    frontend_repository_path = Path(frontend_repository_path).resolve()
    workflow_temporary_root = Path(__file__).resolve().parents[2]/'.tmp'
    ui_review_snapshot_root = workflow_temporary_root/'ui-review'
    source_hash_value = calculate_frontend_review_source_hash(frontend_repository_path)
    for current_bundle_path in sorted(ui_review_snapshot_root.glob('*/ui-review'), reverse=True):
        source_hash_path = current_bundle_path.parent/'ui-review-source.json'
        if source_hash_path.is_file():
            source_hash_record = json.loads(source_hash_path.read_text())
            if source_hash_record.get('sourceHash') == source_hash_value:
                return current_bundle_path
    print(f'{datetime.now().isoformat()}/asset-review-server/ui-build 프론트엔드 UI 검수 빌드를 생성합니다.', flush=True)
    subprocess.run(['npm', 'run', 'build:review'], cwd=frontend_repository_path, check=True)
    frontend_temporary_root = frontend_repository_path/'.tmp'
    source_bundle_candidates = sorted((current_path for current_path in frontend_temporary_root.glob('*/ui-review') if current_path.is_dir()), reverse=True)
    if not source_bundle_candidates:
        raise ValueError('npm run build:review 결과에서 ui-review 사본을 찾지 못했습니다.')
    source_bundle_path = source_bundle_candidates[0]
    snapshot_directory = ui_review_snapshot_root/(datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')+'-'+source_hash_value[:12])
    snapshot_directory.mkdir(parents=True, exist_ok=False)
    destination_bundle_path = snapshot_directory/'ui-review'
    shutil.copytree(source_bundle_path, destination_bundle_path)
    source_record = {'sourceHash': source_hash_value, 'sourceRepository': str(frontend_repository_path), 'sourceBundle': str(source_bundle_path), 'snapshotBundle': str(destination_bundle_path)}
    (snapshot_directory/'ui-review-source.json').write_text(json.dumps(source_record, ensure_ascii=False, indent=2))
    (ui_review_snapshot_root/'latest.json').write_text(json.dumps(source_record, ensure_ascii=False, indent=2))
    return destination_bundle_path


def prepare_review_directory(parsed_argument_values):
    if parsed_argument_values.frontend_repo:
        if __package__:
            from .build_frontend_review import build_frontend_review
        else:
            from build_frontend_review import build_frontend_review
        selected_ui_bundle_path = parsed_argument_values.ui_bundle or ensure_frontend_ui_review_bundle(parsed_argument_values.frontend_repo)
        return build_frontend_review(parsed_argument_values.frontend_repo, ui_bundle_directory=selected_ui_bundle_path)
    if parsed_argument_values.walking:
        if __package__:
            from .build_frame_manager import build_frame_manager
        else:
            from build_frame_manager import build_frame_manager
        return build_frame_manager(parsed_argument_values)
    return parsed_argument_values.root.resolve()


def run_review_server(parsed_argument_values):
    review_root_directory = prepare_review_directory(parsed_argument_values)
    workflow_repo_root = Path(__file__).resolve().parents[2]
    allowed_review_roots = [workflow_repo_root/current_root_name for current_root_name in ('.tmp','.result','assets')]
    if not any(review_root_directory.is_relative_to(allowed_root_path) and review_root_directory != allowed_root_path for allowed_root_path in allowed_review_roots):
        raise ValueError('워크플로우 .tmp, .result 또는 assets 아래 개별 검수 폴더를 지정하세요.')
    if Path(parsed_argument_values.entry).is_absolute() or Path(parsed_argument_values.entry).suffix.lower() != '.html':
        raise ValueError('진입 페이지는 검수 폴더 기준 상대 HTML 경로여야 합니다.')
    resolve_review_request(review_root_directory,'/'+parsed_argument_values.entry)
    if not 1024 <= parsed_argument_values.port <= 65535: raise ValueError('포트는 1024~65535여야 합니다.')
    # 관리도구 빌드는 review_root_directory 자체를 교체할 수 있으므로 서버 로그는 별도 안정 경로에 둔다.
    server_log_directory = workflow_repo_root/'.tmp'/'review-server-logs'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    server_log_directory.mkdir(parents=True,exist_ok=False)
    server_log_path = server_log_directory/'review-server.log'
    trace_write_lock = threading.Lock()
    server_stop_event = threading.Event()
    request_counter_value = [0]
    review_server_instance_id = f'{time.time_ns():x}'
    manager_source_path = review_root_directory/'manager-source.json'
    def emit_server_trace(trace_stage_name, trace_message_text):
        trace_line_text = f'{datetime.now().isoformat()}/asset-review-server/{trace_stage_name} {trace_message_text}'
        with trace_write_lock:
            print(trace_line_text,flush=True)
            with server_log_path.open('a') as trace_file_stream: trace_file_stream.write(trace_line_text+'\n')
    from tools.review.domains.image.image_generation import ImageGenerationManager
    if str(workflow_repo_root) not in sys.path:sys.path.insert(0,str(workflow_repo_root))
    from generators.writer_agent.management import WriterAgentManager
    from generators.writer_agent.documents import DEFAULT_WORKSPACE_CONFIG
    writer_agent_service=WriterAgentManager(parsed_argument_values.writer_agent_config or DEFAULT_WORKSPACE_CONFIG)
    image_generation_service = ImageGenerationManager()
    from tools.review.domains.tile.tile_generation import TileGenerationManager
    tile_generation_service = TileGenerationManager()
    from tools.review.domains.anny.anny_attributes import AnnyAttributeManager
    anny_attribute_service = AnnyAttributeManager()
    from tools.review.domains.momask.momask_generation import MoMaskGenerationManager
    momask_generation_service = MoMaskGenerationManager()
    three_reference_service = ImageGenerationManager(three_reference_mode=True)
    from tools.review.common.management_gateway import ManagementCommandGateway
    from tools.review.domains.character_animation.character_animation import CharacterAnimationManager
    character_animation_service = CharacterAnimationManager()
    management_command_gateway = ManagementCommandGateway({'tile-map':tile_generation_service.handle_image_request,'character-animation':character_animation_service.handle,'momask':momask_generation_service.handle,'qwen-2512':image_generation_service.handle_image_request,'qwen-2511':three_reference_service.handle_image_request})
    from tools.review.common.record_folders import handle_record_folder_request
    from tools.review.domains.character_animation.character_animation_jobs import GENERATION_ROOT_DIRECTORY, resolve_generation_directory
    from tools.review.domains.anny.anny_attributes import JOBS as ANNY_RECORD_DIRECTORY
    record_folder_routes = {
        '/tile-map-generator': (tile_generation_service.job_storage_root, lambda record_identifier_value: tile_generation_service.job_storage_root/record_identifier_value),
        '/character-animation': (GENERATION_ROOT_DIRECTORY, resolve_generation_directory),
        '/anny-attributes': (ANNY_RECORD_DIRECTORY, lambda record_identifier_value: ANNY_RECORD_DIRECTORY/record_identifier_value),
        '/image-generation': (image_generation_service.job_storage_root, lambda record_identifier_value: image_generation_service.job_storage_root/record_identifier_value),
        '/image-generation-2511': (three_reference_service.job_storage_root, lambda record_identifier_value: three_reference_service.job_storage_root/record_identifier_value),
    }
    class ReviewRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self,*request_handler_arguments,**request_handler_options):
            super().__init__(*request_handler_arguments,directory=str(review_root_directory),**request_handler_options)
        def do_GET(self):
            if urlsplit(self.path).path=='/' and manager_source_path.is_file():
                from tools.review.common.gradio_process import ensure_management_menu_server
                try:
                    management_menu_url=ensure_management_menu_server(self.server.server_port,manager_source_path)
                except ValueError as gradio_error_value:
                    self.send_error(503,str(gradio_error_value))
                    return
                self.send_response(302);self.send_header('Location',management_menu_url);self.send_header('Cache-Control','no-store');self.end_headers()
                return
            if urlsplit(self.path).path=='/management/gpu-status':
                from tools.review.common.gpu_status import read_gpu_status
                response_content=json.dumps(read_gpu_status(),ensure_ascii=False).encode()
                self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(response_content)));self.end_headers();self.wfile.write(response_content)
                return
            if urlsplit(self.path).path=='/management/gpu-status.js':
                response_content=(Path(__file__).parent/'ui/shared/gpu-status.js').read_bytes()
                self.send_response(200);self.send_header('Content-Type','text/javascript');self.send_header('Content-Length',str(len(response_content)));self.end_headers();self.wfile.write(response_content)
                return
            if urlsplit(self.path).path in ('/management/style.css','/management/studio.css'):
                response_content=resolve_review_ui_asset('management.css').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/css; charset=utf-8')
                self.send_header('Content-Length',str(len(response_content)))
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(response_content)
                return
            if urlsplit(self.path).path=='/management/workflow-ui.js':
                response_content=resolve_review_ui_asset('management-workflow.js').read_bytes()
                self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(response_content)));self.end_headers();self.wfile.write(response_content)
                return
            if is_review_live_reload_request(self.path):
                encoded_record = json.dumps({'instanceId': review_server_instance_id}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(encoded_record)))
                self.end_headers()
                self.wfile.write(encoded_record)
                return
            if management_command_gateway.handle(self):return
            if character_animation_service.handle(self):return
            if anny_attribute_service.handle(self):return
            if writer_agent_service.handle_writer_request(self):return
            if momask_generation_service.handle(self):return
            if three_reference_service.handle_image_request(self):
                return
            if tile_generation_service.handle_image_request(self):return
            if image_generation_service.handle_image_request(self):
                return
            super().do_GET()
        def do_POST(self):
            if handle_record_folder_request(self,record_folder_routes):return
            if management_command_gateway.handle(self):return
            if anny_attribute_service.handle(self):return
            if writer_agent_service.handle_writer_request(self):return
            if momask_generation_service.handle(self):return
            if three_reference_service.handle_image_request(self):
                return
            if tile_generation_service.handle_image_request(self):return
            if image_generation_service.handle_image_request(self):
                return
            self.send_error(404, '지원하지 않는 작업 경로')
        def send_head(self):
            try:
                validated_request_path = resolve_review_request(review_root_directory,self.path,parsed_argument_values.entry)
            except ValueError:
                self.send_error(404,'Review asset not found')
                return None
            self.path = '/'+validated_request_path.relative_to(review_root_directory).as_posix()
            if validated_request_path.suffix.lower() == '.html':
                response_content = inject_review_live_reload(validated_request_path.read_bytes())
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(response_content)))
                self.end_headers()
                return io.BytesIO(response_content)
            return super().send_head()
        def list_directory(self,requested_directory_path):
            self.send_error(403,'Directory listing disabled')
            return None
        def end_headers(self):
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cross-Origin-Resource-Policy','same-origin')
            super().end_headers()
        def log_message(self,request_message_format,*request_message_arguments):
            # 자동 새로고침 상태 확인은 각 iframe에서 반복되므로 서버 로그·요청 수에서 제외한다.
            if is_review_live_reload_request(self.path):
                return
            request_counter_value[0]+=1
            emit_server_trace('request',(request_message_format % request_message_arguments).replace('\n',' '))
    def emit_server_heartbeat():
        while not server_stop_event.wait(REVIEW_HEARTBEAT_SECONDS):
            try: log_size_value=server_log_path.stat().st_size
            except FileNotFoundError: log_size_value=0
            emit_server_trace('heartbeat',f'requests={request_counter_value[0]} root={review_root_directory.name} log_bytes={log_size_value}')
    def terminate_review_server(current_signal_number,current_stack_frame):
        raise KeyboardInterrupt
    previous_termination_handler=signal.signal(signal.SIGTERM,terminate_review_server)
    try:
        with ThreadingHTTPServer((REVIEW_SERVER_HOST,parsed_argument_values.port),ReviewRequestHandler) as review_http_server:
            emit_server_trace('start',f'http://{REVIEW_SERVER_HOST}:{parsed_argument_values.port}/ root={review_root_directory} entry={parsed_argument_values.entry} log={server_log_path}')
            heartbeat_worker_thread = threading.Thread(target=emit_server_heartbeat,daemon=True)
            heartbeat_worker_thread.start()
            try: review_http_server.serve_forever(poll_interval=0.5)
            except KeyboardInterrupt: emit_server_trace('stop','사용자 종료')
            finally: server_stop_event.set();heartbeat_worker_thread.join(timeout=1)
    except Exception:
        emit_server_trace('failure',traceback.format_exc())
        print('\n'.join(server_log_path.read_text().splitlines()[-20:]),flush=True)
        raise
    finally:
        writer_agent_service.close_writer_worker()
        signal.signal(signal.SIGTERM,previous_termination_handler)

if __name__ == '__main__':
    parsed_argument_values = parse_review_arguments()
    if parsed_argument_values.watch:
        run_review_watch_mode(parsed_argument_values)
    else:
        run_review_server(parsed_argument_values)
