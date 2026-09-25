"""캐릭터 애니메이션 GUI와 공용 명령 서비스의 HTTP 어댑터."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from tools.review.ui_assets import resolve_review_ui_asset
import json
import mimetypes
from urllib.parse import urlsplit, unquote
from tools.review.domains.character_animation.character_animation_jobs import execute_animation_command, resolve_generation_directory
from tools.review.domains.character_animation.character_animation_assets import prepare_animation_request, resolve_asset_path, resolve_motion_preview
from tools.review.common.management_gateway import identify_management_command
from tools.review.common.management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT

REVIEW_SOURCE_DIRECTORY=Path(__file__).resolve().parent

class CharacterAnimationManager:
    def handle(self,current_http_handler):
        request_route_path=unquote(urlsplit(current_http_handler.path).path)
        if not request_route_path.startswith('/character-animation/'):return False
        try:
            command_route_record=identify_management_command(current_http_handler.path,current_http_handler.command)
            if command_route_record:
                command_payload_value=json.loads(current_http_handler.rfile.read(int(current_http_handler.headers['Content-Length']))) if current_http_handler.command=='POST' else command_route_record[2]
                response_record_value=execute_animation_command(command_route_record[1],command_payload_value)
                response_payload_bytes=response_record_value.encode() if isinstance(response_record_value,str) else json.dumps(response_record_value,ensure_ascii=False).encode()
                response_content_type='text/plain' if isinstance(response_record_value,str) else 'application/json'
            elif current_http_handler.command=='GET':
                static_file_mapping={'':'character-animation.html','app.js':'character-animation.js','studio.css':'generation-studio.css','history.js':'generation-history.js','asset-player.js':'character-animation-assets.js'}
                request_route_suffix=request_route_path.removeprefix('/character-animation/')
                if request_route_suffix in static_file_mapping:
                    response_file_path=resolve_review_ui_asset(static_file_mapping[request_route_suffix])
                    response_payload_bytes=response_file_path.read_bytes()
                    response_content_type=mimetypes.guess_type(response_file_path)[0] or 'text/plain'
                elif request_route_suffix=='log-viewer.js':
                    response_payload_bytes=MANAGEMENT_LOG_VIEWER_SCRIPT.encode();response_content_type='text/javascript'
                elif request_route_suffix.startswith('files/'):
                    request_path_parts=request_route_suffix.split('/')
                    generation_job_path=resolve_generation_directory(request_path_parts[1]).resolve()
                    response_file_path=(generation_job_path/('/'.join(request_path_parts[2:]))).resolve()
                    if not response_file_path.is_relative_to(generation_job_path) or response_file_path.suffix!='.png' or not response_file_path.is_file():raise ValueError('허용하지 않는 결과 파일')
                    response_payload_bytes=response_file_path.read_bytes();response_content_type='image/png'
                elif request_route_suffix.startswith('asset/'):
                    request_path_parts=request_route_suffix.split('/')
                    if len(request_path_parts)!=5:raise ValueError('모션 프레임 조회 형식 오류')
                    _,selected_motion_name,selected_source_kind,selected_direction_name,selected_frame_text=request_path_parts
                    response_file_path=resolve_motion_preview(selected_motion_name,selected_source_kind,selected_direction_name,int(selected_frame_text))
                    response_payload_bytes=response_file_path.read_bytes();response_content_type='image/png'
                elif request_route_suffix.startswith('reference/'):
                    request_path_parts=request_route_suffix.split('/')
                    if len(request_path_parts)!=6:raise ValueError('참조 조회 형식 오류')
                    _,selected_motion_name,selected_character_name,selected_source_kind,selected_direction_name,selected_reference_role=request_path_parts
                    if selected_reference_role not in ('pose','character'):raise ValueError('참조 종류 오류')
                    reference_request_record=prepare_animation_request({'motion':selected_motion_name,'character':selected_character_name,'source':selected_source_kind,'directions':[selected_direction_name]})
                    response_payload_bytes=resolve_asset_path(reference_request_record['frames'][0][selected_reference_role+'_path']).read_bytes();response_content_type='image/png'
                else:raise ValueError('등록되지 않은 경로')
            else:raise ValueError('지원하지 않는 요청')
            current_http_handler.send_response(200)
        except (ValueError,KeyError,TypeError,OSError,IndexError) as request_error_value:
            response_payload_bytes=json.dumps({'error':str(request_error_value)},ensure_ascii=False).encode();response_content_type='application/json'
            current_http_handler.send_response(400)
        current_http_handler.send_header('Content-Type',response_content_type+'; charset=utf-8')
        current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)))
        current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_bytes)
        return True
