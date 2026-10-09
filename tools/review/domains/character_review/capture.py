"""공용 브라우저 렌더러로 캐릭터 검수 PNG와 설정을 기록한다."""
import base64
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from PIL import Image
import yaml

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
CAPTURE_STORAGE_DIRECTORY=WORKFLOW_ROOT_DIRECTORY/'.tmp/test/character-review-capture'
CAPTURE_TIMEOUT_SECONDS=120
CAPTURE_INTERNAL_RESOLUTION_SCALE=2
CAPTURE_DEFAULT_SETTINGS={'ground':'paving','zoom':2.0,'column':1,'row':1,'rotation':0,'outline':True,'outline_width':1,'rim':True,'shadow':True,'shadow_profile':'contrast','contrast':'original','saturation_reduced':False,'brightness_reduced':False,'width':768,'height':576}


def validate_capture_settings(command_payload_value):
    if not isinstance(command_payload_value,dict) or set(command_payload_value)-set(CAPTURE_DEFAULT_SETTINGS):
        raise ValueError('알 수 없는 캡처 설정입니다.')
    current_setting_values=CAPTURE_DEFAULT_SETTINGS|command_payload_value
    for current_field_name,current_allowed_values in {'ground':('paving','grass','meadow-road'),'shadow_profile':('baseline','contrast','broad'),'contrast':('original','soft')}.items():
        if current_setting_values[current_field_name] not in current_allowed_values:raise ValueError('캡처 설정 오류: '+current_field_name)
    for current_field_name in ('outline','rim','shadow','saturation_reduced','brightness_reduced'):
        if type(current_setting_values[current_field_name]) is not bool:raise ValueError('참/거짓 설정 필요: '+current_field_name)
    for current_field_name,current_minimum_value,current_maximum_value in [('column',0,2),('row',0,2),('rotation',0,3),('width',256,1600),('height',256,1200)]:
        current_field_value=current_setting_values[current_field_name]
        if type(current_field_value) is not int or not current_minimum_value<=current_field_value<=current_maximum_value:raise ValueError('캡처 범위 오류: '+current_field_name)
    if type(current_setting_values['outline_width']) not in (int,float) or not 1<=current_setting_values['outline_width']<=4:raise ValueError('외곽선 폭은 1–4px입니다.')
    if type(current_setting_values['zoom']) not in (int,float) or not .05<=current_setting_values['zoom']<=4:raise ValueError('배율 범위는 0.05–4입니다.')
    return current_setting_values


def capture_character_review(command_payload_value):
    current_setting_values=validate_capture_settings(command_payload_value)
    current_browser_path=shutil.which('google-chrome') or shutil.which('chromium')
    if not current_browser_path:raise ValueError('PNG 캡처에 필요한 Chrome 또는 Chromium이 없습니다.')
    current_output_directory=CAPTURE_STORAGE_DIRECTORY/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    current_output_directory.mkdir(parents=True,exist_ok=False)
    current_result_record={'status':'running','settings':current_setting_values,'directory':str(current_output_directory)}
    current_record_path=current_output_directory/'result.yaml'
    current_stop_event=threading.Event()
    current_capture_event=threading.Event()
    current_capture_payload={}
    current_capture_token=secrets.token_urlsafe(24)
    current_server_instance=None
    current_browser_process=None
    def write_capture_trace(current_stage_name,current_message_text):
        with (current_output_directory/'worker.log').open('a') as current_log_stream:
            current_log_stream.write(f'{datetime.now().isoformat()}/character-review/{current_stage_name} {current_message_text}\n')
    def emit_capture_heartbeat():
        while not current_stop_event.wait(5):write_capture_trace('heartbeat','캡처 준비·브라우저 렌더링 진행 중')
    threading.Thread(target=emit_capture_heartbeat,daemon=True).start()
    try:
        write_capture_trace('start',f'output={current_output_directory} settings={current_setting_values}')
        from tools.review.build_block_map_review import build_block_map_review
        current_bundle_directory=build_block_map_review(current_output_directory/'web',character_review_only=True)
        current_setting_document=current_setting_values|{'token':current_capture_token}
        (current_bundle_directory/'capture-settings.json').write_text(json.dumps(current_setting_document))
        (current_bundle_directory/'capture.html').write_text('''<!doctype html><meta charset="utf-8"><title>캐릭터 렌더 캡처</title>
<div id="map-title"></div><div id="status"></div><output id="zoom-level"></output><ul id="applied-tile-list"></ul>
<canvas id="character-baseline-map"></canvas><canvas id="map" data-character-review="true" data-capture="true"></canvas>
<script type="module">try{await import('./block-map-review.js')}catch(error){const settings=await(await fetch('./capture-settings.json')).json();await fetch('/capture-result',{method:'POST',headers:{'Content-Type':'application/json','X-Capture-Token':settings.token},body:JSON.stringify({error:String(error.stack||error)})})}</script>''')
        class CaptureAssetHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                from tools.review.common.map_asset_http import read_map_asset_response
                current_request_path=urlsplit(self.path).path
                if current_request_path=='/management/map-assets/textures':
                    self.path='/block-textures.json';super().do_GET();return
                if current_request_path.startswith('/management/map-assets/'):
                    try:current_content_bytes,current_content_type=read_map_asset_response(current_request_path)
                    except (ValueError,OSError,KeyError) as current_asset_error:self.send_error(404,str(current_asset_error));return
                    self.send_response(200);self.send_header('Content-Type',current_content_type);self.end_headers();self.wfile.write(current_content_bytes);return
                super().do_GET()
            def do_POST(self):
                if self.path!='/capture-result' or self.headers.get('X-Capture-Token')!=current_capture_token:self.send_error(403);return
                current_body_length=int(self.headers.get('Content-Length','0'))
                if not 0<current_body_length<30_000_000:self.send_error(400);return
                try:
                    current_response_record=json.loads(self.rfile.read(current_body_length))
                    if not isinstance(current_response_record,dict) or set(current_response_record) not in ({'baseline','adjusted'},{'error'}):raise ValueError('캡처 응답 형식 오류')
                    current_capture_payload.update(current_response_record)
                    self.send_response(200);self.end_headers();current_capture_event.set()
                except (ValueError,TypeError):self.send_error(400)
            def log_message(self,current_message_format,*current_message_arguments):
                write_capture_trace('http',current_message_format%current_message_arguments)
        current_server_instance=ThreadingHTTPServer(('127.0.0.1',0),partial(CaptureAssetHandler,directory=str(current_bundle_directory)))
        threading.Thread(target=current_server_instance.serve_forever,daemon=True).start()
        current_browser_arguments=[current_browser_path,'--headless=new','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check',f'--user-data-dir={current_output_directory}/browser-profile',f'http://127.0.0.1:{current_server_instance.server_port}/capture.html']
        with (current_output_directory/'browser.log').open('w') as current_browser_log:
            current_browser_process=subprocess.Popen(current_browser_arguments,stdout=current_browser_log,stderr=current_browser_log)
            current_deadline_time=time.monotonic()+CAPTURE_TIMEOUT_SECONDS
            while not current_capture_event.wait(1):
                if current_browser_process.poll() is not None:raise ValueError('캡처 브라우저 종료: browser.log를 확인하세요.')
                if time.monotonic()>current_deadline_time:raise ValueError('렌더링 완료 대기 시간 초과: worker.log·browser.log를 확인하세요.')
        if 'error' in current_capture_payload:raise ValueError('브라우저 렌더 오류: '+str(current_capture_payload['error']))
        current_image_records=[]
        for current_image_name in ('baseline','adjusted'):
            current_image_data=current_capture_payload[current_image_name]
            if not isinstance(current_image_data,str) or not current_image_data.startswith('data:image/png;base64,'):raise ValueError('PNG 캡처 형식 오류')
            current_image_bytes=base64.b64decode(current_image_data.split(',',1)[1],validate=True)
            current_image_object=Image.open(io.BytesIO(current_image_bytes))
            if current_image_object.format!='PNG' or current_image_object.size!=(current_setting_values['width']*CAPTURE_INTERNAL_RESOLUTION_SCALE,current_setting_values['height']*CAPTURE_INTERNAL_RESOLUTION_SCALE):raise ValueError('PNG 캡처 크기 오류')
            (current_output_directory/f'{current_image_name}.png').write_bytes(current_image_bytes)
            current_image_records.append(current_image_object.convert('RGBA'))
        current_comparison_image=Image.new('RGBA',(current_setting_values['width']*2*CAPTURE_INTERNAL_RESOLUTION_SCALE,current_setting_values['height']*CAPTURE_INTERNAL_RESOLUTION_SCALE))
        for current_image_index,current_image_object in enumerate(current_image_records):current_comparison_image.paste(current_image_object,(current_image_index*current_setting_values['width']*CAPTURE_INTERNAL_RESOLUTION_SCALE,0))
        current_comparison_image.save(current_output_directory/'comparison.png')
        current_result_record.update(status='completed',images={current_image_name:str(current_output_directory/f'{current_image_name}.png') for current_image_name in ('baseline','adjusted','comparison')})
        write_capture_trace('completed','원본·조정본·비교 PNG 저장 완료')
        return current_result_record
    except Exception as current_capture_error:
        current_result_record.update(status='failed',error=str(current_capture_error));write_capture_trace('failed',str(current_capture_error));raise
    finally:
        if current_browser_process and current_browser_process.poll() is None:
            current_browser_process.terminate()
            try:current_browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:current_browser_process.kill();current_browser_process.wait()
        if current_server_instance:current_server_instance.shutdown();current_server_instance.server_close()
        current_stop_event.set()
        current_record_path.write_text(yaml.safe_dump(current_result_record,allow_unicode=True,sort_keys=False))
        shutil.rmtree(current_output_directory/'browser-profile',ignore_errors=True)


def handle_character_capture_request(current_http_handler):
    from tools.review.common.management_transport import send_management_json_response
    if current_http_handler.command!='POST' or urlsplit(current_http_handler.path).path!='/character-review/capture':return False
    try:
        current_request_payload=json.loads(current_http_handler.rfile.read(int(current_http_handler.headers['Content-Length'])))
        send_management_json_response(current_http_handler,200,capture_character_review(current_request_payload))
    except Exception as current_capture_error:
        send_management_json_response(current_http_handler,400,{'error':str(current_capture_error)})
    return True
