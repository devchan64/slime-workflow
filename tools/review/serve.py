"""워크플로우 실행 결과·제작 자산의 로컬 읽기 전용 공통 검수 서버."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import threading
import traceback

REVIEW_SERVER_HOST = '127.0.0.1'
REVIEW_SERVER_PORT = 8770
DEFAULT_FRONTEND_REPOSITORY = Path(__file__).resolve().parents[3]/'slime-frontend'
REVIEW_ALLOWED_SUFFIXES = {'.html', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.js', '.css', '.mp4'}
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
    source_argument_group.add_argument('--frontend-repo',type=Path,help='프론트엔드 저장소 (기본: 워크플로우 옆 slime-frontend)' )
    source_argument_group.add_argument('--root',type=Path,help='기존 검수 또는 관리도구 폴더')
    source_argument_group.add_argument('--walking',type=Path,help='관리도구에 묶을 걷기 검수 폴더')
    argument_value_parser.add_argument('--standing',type=Path,help='관리도구에 묶을 스탠딩 검수 폴더 (--walking과 함께 사용)')
    argument_value_parser.add_argument('--entry',default='preview.html',help='--root 폴더 기준 HTML 진입 페이지')
    argument_value_parser.add_argument('--port',type=int,default=REVIEW_SERVER_PORT,help='로컬 서버 포트 (기본: 8770)')
    parsed_argument_values=argument_value_parser.parse_args(command_argument_values)
    if not any((parsed_argument_values.root, parsed_argument_values.walking, parsed_argument_values.frontend_repo, parsed_argument_values.standing)):
        parsed_argument_values.frontend_repo=DEFAULT_FRONTEND_REPOSITORY
    if bool(parsed_argument_values.walking) != bool(parsed_argument_values.standing):
        argument_value_parser.error('--walking과 --standing을 함께 지정하세요.')
    if (parsed_argument_values.walking or parsed_argument_values.frontend_repo) and parsed_argument_values.entry != 'preview.html':
        argument_value_parser.error('관리도구 생성 모드에서는 --entry를 변경할 수 없습니다.')
    if not 1024 <= parsed_argument_values.port <= 65535:
        argument_value_parser.error('포트는 1024~65535여야 합니다.')
    return parsed_argument_values


def prepare_review_directory(parsed_argument_values):
    if parsed_argument_values.frontend_repo:
        if __package__:
            from .build_frontend_review import build_frontend_review
        else:
            from build_frontend_review import build_frontend_review
        return build_frontend_review(parsed_argument_values.frontend_repo)
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
    server_log_directory = review_root_directory if (parsed_argument_values.walking or parsed_argument_values.frontend_repo) else workflow_repo_root/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    if not (parsed_argument_values.walking or parsed_argument_values.frontend_repo):
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
    class ReviewRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self,*request_handler_arguments,**request_handler_options):
            super().__init__(*request_handler_arguments,directory=str(review_root_directory),**request_handler_options)
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

if __name__ == '__main__':
    run_review_server(parse_review_arguments())
