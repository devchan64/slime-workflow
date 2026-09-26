"""등록 생성기의 실행 폴더만 로컬 파일 관리자로 연다."""
import json
import re
import subprocess
from urllib.parse import urlsplit


def resolve_record_folder(folder_service_routes, selected_service_route, selected_record_identifier):
    if selected_service_route not in folder_service_routes:
        raise ValueError('지원하지 않는 생성기입니다.')
    if not isinstance(selected_record_identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', selected_record_identifier):
        raise ValueError('기록 ID가 올바르지 않습니다.')
    allowed_root_directory, resolve_folder_function = folder_service_routes[selected_service_route]
    resolved_record_directory = resolve_folder_function(selected_record_identifier).resolve()
    if not resolved_record_directory.is_relative_to(allowed_root_directory.resolve()) or not resolved_record_directory.is_dir() or not (resolved_record_directory/'status.json').is_file():
        raise ValueError('기록 폴더가 없거나 허용된 경로 밖입니다.')
    return resolved_record_directory


def handle_record_folder_request(current_http_handler, folder_service_routes):
    if urlsplit(current_http_handler.path).path != '/management/record-folder/open':
        return False
    try:
        expected_origin_value = f'http://127.0.0.1:{current_http_handler.server.server_port}'
        if current_http_handler.headers.get('Host') != expected_origin_value.removeprefix('http://') or current_http_handler.headers.get('Origin') != expected_origin_value:
            raise ValueError('같은 관리도구 화면에서만 폴더를 열 수 있습니다.')
        if current_http_handler.headers.get('Content-Type','').split(';')[0] != 'application/json':
            raise ValueError('JSON 요청이 필요합니다.')
        request_content_length = int(current_http_handler.headers.get('Content-Length','0'))
        if not 0 < request_content_length <= 1024:
            raise ValueError('요청 크기가 올바르지 않습니다.')
        request_record_values = json.loads(current_http_handler.rfile.read(request_content_length))
        if not isinstance(request_record_values,dict) or set(request_record_values) != {'route','id'} or not isinstance(request_record_values['route'],str):
            raise ValueError('생성기와 기록 ID를 지정하세요.')
        resolved_record_directory = resolve_record_folder(folder_service_routes,request_record_values['route'],request_record_values['id'])
        subprocess.run(['xdg-open',str(resolved_record_directory)],check=True,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        response_record_values = {'path':str(resolved_record_directory),'message':'파일 관리자에 기록 폴더 열기를 요청했습니다.'}
        response_status_code = 200
    except (ValueError,TypeError,OSError,subprocess.SubprocessError) as request_error_value:
        response_record_values = {'error':'폴더 열기 실패: '+str(request_error_value)+' 경로를 복사하여 파일 관리자에서 여세요.'}
        response_status_code = 400
    response_payload_bytes = json.dumps(response_record_values,ensure_ascii=False).encode()
    current_http_handler.send_response(response_status_code)
    current_http_handler.send_header('Content-Type','application/json; charset=utf-8')
    current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)))
    current_http_handler.send_header('Cache-Control','no-store')
    current_http_handler.end_headers()
    current_http_handler.wfile.write(response_payload_bytes)
    return True
