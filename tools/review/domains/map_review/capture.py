"""관리 화면을 열지 않고 공용 WebGL 렌더러로 전체 맵을 캡처한다."""
import base64
import io
import re
from urllib.parse import urlsplit
from PIL import Image

MAP_CAPTURE_DEFAULT_SETTINGS = {'show_character': True, 'show_safe_boundary': True, 'edges': False, 'tile_edges': False}
MAP_CAPTURE_MAXIMUM_EDGE = 4096


def validate_map_capture_settings(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) - ({'map'} | set(MAP_CAPTURE_DEFAULT_SETTINGS)):
        raise ValueError('알 수 없는 맵 캡처 설정입니다.')
    current_map_identifier = current_request_payload.get('map')
    if not isinstance(current_map_identifier, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', current_map_identifier):
        raise ValueError('등록된 맵 ID가 필요합니다.')
    current_setting_values = MAP_CAPTURE_DEFAULT_SETTINGS | current_request_payload
    if any(type(current_setting_values[current_option_name]) is not bool for current_option_name in MAP_CAPTURE_DEFAULT_SETTINGS):
        raise ValueError('맵 표시 옵션은 참/거짓이어야 합니다.')
    return current_setting_values


def capture_map_review(current_request_payload):
    from tools.review.domains.character_review.capture import execute_review_capture
    from tools.review.build_block_map_review import build_registered_map_review
    current_setting_values = validate_map_capture_settings(current_request_payload)
    build_registered_map_review(current_setting_values['map'])
    return execute_review_capture(current_setting_values, current_map_capture=True)


def build_map_capture_document():
    return '''<!doctype html><meta charset="utf-8"><title>전체 맵 PNG 캡처</title>
<div id="map-title"></div><div id="status"></div><output id="zoom-level"></output>
<ul id="applied-tile-list"></ul><ul id="applied-building-list"></ul><ul id="applied-billboard-list"></ul><ul id="applied-structure-list"></ul>
<div style="width:1024px;height:768px"><canvas id="map"></canvas></div>
<script type="module">
const currentCaptureSettings=await(await fetch('./capture-settings.json')).json();
let currentCaptureResult;
try{
 await import('./block-map-review.js');
 window.mapReviewDisplayOptions(currentCaptureSettings.show_character,currentCaptureSettings.show_safe_boundary,currentCaptureSettings.edges,'contrast',currentCaptureSettings.tile_edges);
 const currentCaptureImage=await window.mapReviewCreateExportImage();
 currentCaptureResult={map:currentCaptureImage.src};
}catch(currentCaptureError){currentCaptureResult={error:String(currentCaptureError.stack||currentCaptureError)};}
const currentCaptureResponse=await fetch('./capture-result',{method:'POST',headers:{'Content-Type':'application/json','X-Capture-Token':currentCaptureSettings.token},body:JSON.stringify(currentCaptureResult)});
if(!currentCaptureResponse.ok)throw Error('맵 PNG 응답 저장 실패');
</script>'''


def save_map_capture_result(current_capture_payload, current_output_directory):
    if set(current_capture_payload) != {'map'}:
        raise ValueError('맵 PNG 응답 형식 오류')
    current_image_data = current_capture_payload['map']
    if not isinstance(current_image_data, str) or not current_image_data.startswith('data:image/png;base64,'):
        raise ValueError('맵 PNG 데이터 형식 오류')
    current_image_bytes = base64.b64decode(current_image_data.split(',', 1)[1], validate=True)
    current_image_object = Image.open(io.BytesIO(current_image_bytes))
    if current_image_object.format != 'PNG' or current_image_object.mode != 'RGBA' or max(current_image_object.size) > MAP_CAPTURE_MAXIMUM_EDGE:
        raise ValueError('맵 PNG 규격 오류')
    if current_image_object.getchannel('A').getbbox() is None:
        raise ValueError('맵 PNG가 비어 있습니다.')
    current_output_path = current_output_directory/'map.png'
    current_output_path.write_bytes(current_image_bytes)
    return {'map': str(current_output_path)}


def handle_map_capture_request(current_http_handler):
    import json
    from tools.review.common.management_transport import send_management_json_response
    if current_http_handler.command != 'POST' or urlsplit(current_http_handler.path).path != '/map-review/capture':
        return False
    try:
        current_request_payload = json.loads(current_http_handler.rfile.read(int(current_http_handler.headers['Content-Length'])))
        send_management_json_response(current_http_handler, 200, capture_map_review(current_request_payload))
    except Exception as current_capture_error:
        send_management_json_response(current_http_handler, 400, {'error': str(current_capture_error)})
    return True
