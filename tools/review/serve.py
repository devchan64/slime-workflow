"""워크플로우 실행 결과·제작 자산의 로컬 읽기 전용 공통 검수 서버."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json
import shutil
import subprocess
import threading
import time
import traceback
import sys

REVIEW_SERVER_HOST = '127.0.0.1'
REVIEW_SERVER_PORT = 8770
DEFAULT_FRONTEND_REPOSITORY = Path(__file__).resolve().parents[3]/'slime-frontend'
REVIEW_ALLOWED_SUFFIXES = {'.html', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.js', '.css', '.mp4', '.svg', '.woff', '.woff2'}
REVIEW_HEARTBEAT_SECONDS = 5

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
    source_argument_group.add_argument('--worldbuilding-only',action='store_true',dest='worldbuilding_only_mode',help='에셋 검수 빌드 없이 세계관 관리 화면만 실행')
    source_argument_group.add_argument('--frontend-repo',type=Path,help='프론트엔드 저장소 (기본: 워크플로우 옆 slime-frontend)' )
    source_argument_group.add_argument('--root',type=Path,help='기존 검수 또는 관리도구 폴더')
    source_argument_group.add_argument('--walking',type=Path,help='관리도구에 묶을 걷기 검수 폴더')
    argument_value_parser.add_argument('--standing',type=Path,help='관리도구에 묶을 스탠딩 검수 폴더 (--walking과 함께 사용)')
    argument_value_parser.add_argument('--entry',default='preview.html',help='--root 폴더 기준 HTML 진입 페이지')
    argument_value_parser.add_argument('--port',type=int,default=REVIEW_SERVER_PORT,help='로컬 서버 포트 (기본: 8770)')
    argument_value_parser.add_argument('--ui-bundle',type=Path,help='프론트엔드에서 전달한 UI 검수 빌드 폴더')
    argument_value_parser.add_argument('--worldbuilding-config',type=Path,help='비공개 세계관 작업 공간 설정 YAML')
    argument_value_parser.add_argument('--watch',action='store_true',help='소스 변경 시 검수 빌드를 다시 만들고 서버를 재시작')
    parsed_argument_values=argument_value_parser.parse_args(command_argument_values)
    if not any((parsed_argument_values.root, parsed_argument_values.walking, parsed_argument_values.frontend_repo, parsed_argument_values.standing, parsed_argument_values.worldbuilding_only_mode)):
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
    watch_paths = [Path(__file__).resolve(), workflow_repo_root/'tools/review', workflow_repo_root/'generators/animation']
    if parsed_argument_values.frontend_repo:
        watch_paths.append(Path(parsed_argument_values.frontend_repo).resolve()/'src/assets')
    if parsed_argument_values.root:
        watch_paths.append(Path(parsed_argument_values.root).resolve())
    if parsed_argument_values.walking:
        watch_paths.extend([Path(parsed_argument_values.walking).resolve(), Path(parsed_argument_values.standing).resolve()])
    return tuple(path for path in watch_paths if path.exists())

def snapshot_review_watch_paths(watch_paths):
    return tuple(sorted((str(current_file), current_file.stat().st_mtime_ns, current_file.stat().st_size)
        for current_root_path in watch_paths
        for current_file in ([current_root_path] if current_root_path.is_file() else current_root_path.rglob('*'))
        if current_file.is_file() and current_file.suffix.lower() in {'.py', '.html', '.css', '.js', '.json', '.yaml', '.yml', '.png', '.jpg', '.jpeg', '.webp'}))

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
                        raise RuntimeError(f'검수 서버가 비정상 종료되었습니다: {review_server_process.returncode}')
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
    if getattr(parsed_argument_values, 'worldbuilding_only_mode', False):
        worldbuilding_review_root = Path(__file__).resolve().parents[2]/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')/'worldbuilding-manager'
        worldbuilding_review_root.mkdir(parents=True,exist_ok=False)
        document_manager_template=Path(__file__).with_name('frame-manager.html').read_text()
        document_manager_styles=Path(__file__).with_name('review-ui.css').read_text()
        isloon_review_root = worldbuilding_review_root / 'isloon'
        if __package__:
            from .build_isloon_map_review import build_isloon_map_review
        else:
            from build_isloon_map_review import build_isloon_map_review
        build_isloon_map_review(output_root=isloon_review_root)
        manager_page_records = [{'id':'map-review','label':'타일맵검수','path':'isloon/map-review.html','category':'tile-review','anchorEditor':False,'description':'YAML 타일 조립 결과·연결 규칙·건물 충돌 검수'}]
        manager_html = document_manager_template.replace('__MANAGER_PAGES__',json.dumps(manager_page_records,ensure_ascii=False).replace('<','\\u003c'))
        (worldbuilding_review_root/'preview.html').write_text(manager_html.replace('</style>','</style><style>'+document_manager_styles+'</style>',1))
        return worldbuilding_review_root
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
    server_log_directory = review_root_directory if (parsed_argument_values.walking or parsed_argument_values.frontend_repo or getattr(parsed_argument_values, 'worldbuilding_only_mode', False)) else workflow_repo_root/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    if not (parsed_argument_values.walking or parsed_argument_values.frontend_repo or getattr(parsed_argument_values, 'worldbuilding_only_mode', False)):
        server_log_directory.mkdir(parents=True,exist_ok=False)
    server_log_path = server_log_directory/'review-server.log'
    trace_write_lock = threading.Lock()
    server_stop_event = threading.Event()
    request_counter_value = [0]
    def emit_server_trace(trace_stage_name, trace_message_text):
        trace_line_text = f'{datetime.now().isoformat()}/asset-review-server/{trace_stage_name} {trace_message_text}'
        with trace_write_lock:
            print(trace_line_text,flush=True)
            with server_log_path.open('a') as trace_file_stream: trace_file_stream.write(trace_line_text+'\n')
    worldbuilding_management_service = None
    worldbuilding_config_path = getattr(parsed_argument_values, 'worldbuilding_config', None) or workflow_repo_root/'.local/worldbuilding/workspace.yaml'
    if getattr(parsed_argument_values, 'worldbuilding_only_mode', False) and not worldbuilding_config_path.exists():
        raise ValueError('세계관 작업 공간 설정 파일이 없습니다.')
    if worldbuilding_config_path.exists():
        sys.path.insert(0, str(workflow_repo_root))
        from generators.worldbuilding.management import WorldbuildingManagement
    elif getattr(parsed_argument_values, 'worldbuilding_config', None):
        raise ValueError('세계관 작업 공간 설정 파일이 없습니다.')
    if __package__:
        from .image_generation import ImageGenerationManager
    else:
        from image_generation import ImageGenerationManager
    image_generation_service = ImageGenerationManager()
    three_reference_service = ImageGenerationManager(three_reference_mode=True)
    class ReviewRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self,*request_handler_arguments,**request_handler_options):
            super().__init__(*request_handler_arguments,directory=str(review_root_directory),**request_handler_options)
        def do_GET(self):
            if three_reference_service.handle_image_request(self):
                return
            if image_generation_service.handle_image_request(self):
                return
            if worldbuilding_management_service and worldbuilding_management_service.handle_management_request(self):
                return
            super().do_GET()
        def do_POST(self):
            if three_reference_service.handle_image_request(self):
                return
            if image_generation_service.handle_image_request(self):
                return
            if worldbuilding_management_service and worldbuilding_management_service.handle_management_request(self):
                return
            self.send_error(404, '지원하지 않는 작업 경로')
        def send_head(self):
            try:
                validated_request_path = resolve_review_request(review_root_directory,self.path,parsed_argument_values.entry)
            except ValueError:
                self.send_error(404,'Review asset not found')
                return None
            self.path = '/'+validated_request_path.relative_to(review_root_directory).as_posix()
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
            request_counter_value[0]+=1
            emit_server_trace('request',(request_message_format % request_message_arguments).replace('\n',' '))
    def emit_server_heartbeat():
        while not server_stop_event.wait(REVIEW_HEARTBEAT_SECONDS):
            emit_server_trace('heartbeat',f'requests={request_counter_value[0]} root={review_root_directory.name} log_bytes={server_log_path.stat().st_size}')
    try:
        with ThreadingHTTPServer((REVIEW_SERVER_HOST,parsed_argument_values.port),ReviewRequestHandler) as review_http_server:
            if worldbuilding_config_path.exists():
                worldbuilding_management_service = WorldbuildingManagement(worldbuilding_config_path)
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
        if worldbuilding_management_service:
            worldbuilding_management_service.close_management_worker()

if __name__ == '__main__':
    parsed_argument_values = parse_review_arguments()
    if parsed_argument_values.watch:
        run_review_watch_mode(parsed_argument_values)
    else:
        run_review_server(parsed_argument_values)
