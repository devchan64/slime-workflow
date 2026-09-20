"""선택한 .tmp 검수 폴더만 제공하는 로컬 읽기 전용 정적 웹서버."""
from pathlib import Path
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import threading
import traceback

REVIEW_SERVER_HOST = '127.0.0.1'
REVIEW_SERVER_PORT = 8765
REVIEW_ALLOWED_SUFFIXES = {'.html', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.js', '.css', '.mp4'}
REVIEW_HEARTBEAT_SECONDS = 5

def resolve_review_request(review_root_directory, requested_url_path):
    decoded_request_path = unquote(urlsplit(requested_url_path).path)
    if decoded_request_path == '/': decoded_request_path = '/preview.html'
    relative_request_parts = Path(decoded_request_path.lstrip('/')).parts
    if any(path_part_value.startswith('.') for path_part_value in relative_request_parts):
        raise ValueError('숨김 파일 또는 경로 이동 요청은 허용하지 않습니다.')
    resolved_asset_path = (review_root_directory/decoded_request_path.lstrip('/')).resolve()
    if not resolved_asset_path.is_relative_to(review_root_directory) or not resolved_asset_path.is_file() or resolved_asset_path.suffix.lower() not in REVIEW_ALLOWED_SUFFIXES:
        raise ValueError('허용된 검수 파일이 아닙니다.')
    return resolved_asset_path

def run_review_server(parsed_argument_values):
    review_root_directory = parsed_argument_values.root.resolve()
    workflow_temporary_root = Path(__file__).resolve().parents[2]/'.tmp'
    if not review_root_directory.is_relative_to(workflow_temporary_root) or review_root_directory == workflow_temporary_root or not (review_root_directory/'preview.html').is_file():
        raise ValueError('preview.html이 있는 개별 워크플로우 .tmp 검수 폴더를 지정하세요.')
    if not 1024 <= parsed_argument_values.port <= 65535: raise ValueError('포트는 1024~65535여야 합니다.')
    server_log_path = review_root_directory/'review-server.log'
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
                validated_request_path = resolve_review_request(review_root_directory,self.path)
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
            emit_server_trace('start',f'http://{REVIEW_SERVER_HOST}:{parsed_argument_values.port}/ root={review_root_directory}')
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
    argument_value_parser=argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--root',type=Path,required=True)
    argument_value_parser.add_argument('--port',type=int,default=REVIEW_SERVER_PORT)
    run_review_server(argument_value_parser.parse_args())
