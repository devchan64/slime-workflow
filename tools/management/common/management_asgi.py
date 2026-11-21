"""추가 TCP 포트 없이 관리 화면과 기존 HTTP 계약을 같은 서버에서 제공한다."""
import asyncio
import importlib
import io
import os
from types import SimpleNamespace
from urllib.parse import parse_qs
import logging
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from starlette.responses import Response, RedirectResponse, JSONResponse

LEGACY_MANAGEMENT_PATHS = {'/image-generation-21/': 'qwen-21-generator', '/image-generation-21-circular/': 'qwen-21-circular-generator', '/vegetation-generator/': 'vegetation-generator', '/prop-generator/': 'prop-generator', '/billboard-generator/': 'billboard-generator', '/building-generator/': 'building-generator', '/writer-agent/': 'writer-agent'}
GENERATOR_PAGE_PACKAGES = {'mannequin-generator': 'mannequin-generator', 'character-generator': 'character-generator', 'qwen-21-generator': 'qwen-21', 'qwen-21-circular-generator': 'qwen-21-circular', 'expression-generator': 'expression', 'vegetation-generator': 'vegetation-generator', 'prop-generator': 'prop-generator', 'billboard-generator': 'billboard-generator', 'building-generator': 'billboard-generator'}
def execute_legacy_request(current_handler_class, current_root_path, current_request_scope, current_request_body):
    """기존 파일·게이트웨이 핸들러를 소켓 없이 호출한다."""
    current_path_bytes = current_request_scope.get('raw_path', current_request_scope['path'].encode())
    if current_request_scope.get('query_string'):
        current_path_bytes += b'?' + current_request_scope['query_string']
    current_header_bytes = b''.join(current_name + b': ' + current_value + b'\r\n' for current_name, current_value in current_request_scope['headers'] if current_name.lower() not in (b'content-length', b'transfer-encoding', b'connection'))
    current_request_bytes = current_request_scope['method'].encode() + b' ' + current_path_bytes + b' HTTP/1.0\r\n' + current_header_bytes + b'Content-Length: ' + str(len(current_request_body)).encode() + b'\r\n\r\n' + current_request_body
    current_handler_value = current_handler_class.__new__(current_handler_class)
    current_handler_value.rfile = io.BytesIO(current_request_bytes)
    current_handler_value.wfile = io.BytesIO()
    current_handler_value.client_address = current_request_scope.get('client') or ('127.0.0.1', 0)
    current_handler_value.server = SimpleNamespace(server_name='127.0.0.1', server_port=current_request_scope['server'][1])
    current_handler_value.directory = str(current_root_path)
    current_handler_value.close_connection = True
    current_handler_value.handle_one_request()
    current_response_bytes = current_handler_value.wfile.getvalue()
    current_header_block, current_response_body = current_response_bytes.split(b'\r\n\r\n', 1)
    current_header_lines = current_header_block.split(b'\r\n')
    current_response_status = int(current_header_lines[0].split()[1])
    current_response_headers = [tuple(current_line.split(b': ', 1)) for current_line in current_header_lines[1:]]
    current_response_value = Response(current_response_body, status_code=current_response_status)
    current_response_value.raw_headers = [(current_name.lower(), current_value) for current_name, current_value in current_response_headers if current_name.lower() not in (b'connection', b'transfer-encoding')]
    return current_response_value


def is_hermes_predict_diagnostic_enabled(current_root_path):
    """환경 변수 또는 최근 60초의 로컬 표식으로 요청 번호 진단을 켠다."""
    import time
    if os.environ.get('SLIME_HERMES_PREDICT_DIAGNOSTIC')=='1':return True
    current_marker_path=Path(current_root_path)/'.tmp'/'hermes-predict-diagnostic'
    try:
        if current_marker_path.is_symlink() or not current_marker_path.is_file():return False
        current_marker_age=time.time()-current_marker_path.stat().st_mtime
        return 0<=current_marker_age<=60
    except OSError:
        return False


def wrap_predict_diagnostic_receiver(current_receive_call, current_emit_function):
    """옵트인 진단은 이벤트 번호만 기록하며 요청 본문은 전달 후 폐기한다."""
    current_body_buffer = bytearray()
    current_body_overflow = False
    async def receive_predict_diagnostic():
        nonlocal current_body_overflow
        current_message_value = await current_receive_call()
        if current_message_value.get('type') == 'http.request' and not current_body_overflow:
            current_body_chunk = current_message_value.get('body', b'')
            if len(current_body_buffer) + len(current_body_chunk) > 65536:
                current_body_buffer.clear()
                current_body_overflow = True
                return current_message_value
            current_body_buffer.extend(current_body_chunk)
            if not current_message_value.get('more_body', False):
                try:
                    current_request_record = json.loads(current_body_buffer)
                    current_event_identifier = current_request_record.get('fn_index') if isinstance(current_request_record, dict) else None
                    if type(current_event_identifier) is int and 0 <= current_event_identifier < 100000:
                        current_emit_function(current_event_identifier)
                except (UnicodeError, ValueError, TypeError):
                    pass
                finally:
                    current_body_buffer.clear()
        return current_message_value
    return receive_predict_diagnostic


def build_management_application(current_handler_class, current_root_path, current_source_path, current_review_port, current_static_routes):
    os.environ['SLIME_MANAGEMENT_MENU_SOURCE'] = str(current_source_path)
    current_root_application = FastAPI()

    async def dispatch_management_request(current_request_scope, current_receive_call, current_send_call):
        current_request_path = current_request_scope['path']
        if current_request_scope['type'] == 'http' and current_request_scope.get('method') == 'GET' and current_request_path == '/management/gui-health':
            current_health_record = {'status': 'ok', 'role': 'management-gui', 'pid': os.getpid()}
            if os.environ.get('SLIME_MANAGEMENT_STACK_TOKEN'):
                current_health_record['launch_token'] = os.environ['SLIME_MANAGEMENT_STACK_TOKEN']
            return await JSONResponse(current_health_record, headers={'Cache-Control': 'no-store'})(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope['type'] == 'websocket':
            return await current_send_call({'type': 'websocket.close', 'code': 1008})
        current_query_values = parse_qs(current_request_scope.get('query_string', b'').decode())
        if (current_request_scope.get('method') in ('GET', 'HEAD')
                and current_request_path.rstrip('/') == '/management/frame/map-review'):
            kind = current_query_values.get('mapKind', [None])[0]
            if kind is None and current_query_values.get('map'):
                index = current_root_path / 'isloon-map-review' / 'block-map-index.json'
                if index.is_file():
                    import json
                    records = json.loads(index.read_text(encoding='utf-8'))
                    kind = next((row['kind'] for row in records if row['id'] == current_query_values['map'][0]), None)
            surface = {'battle': 'battlefield', 'town': 'town-map', 'field': 'field-map'}.get(kind or 'field')
            if surface is None:
                return await Response('지원하지 않는 지도 종류입니다.', status_code=400)(current_request_scope, current_receive_call, current_send_call)
            query = current_request_scope.get('query_string', b'').decode()
            target = '/management/assistant/' + surface + '/' + ('?' + query if query else '')
            return await RedirectResponse(target)(current_request_scope, current_receive_call, current_send_call)
        # Archived Qwen pages share read-only history, including the character and building aliases.
        archive_services = {**{name: name for name in GENERATOR_PAGE_PACKAGES},
                            'character-generator': 'qwen-21', 'building-generator': 'billboard-generator',
                            'expression-generator': 'expression', 'qwen-21-generator': 'qwen-21',
                            'qwen-21-circular-generator': 'qwen-21-circular'}
        path = current_request_path.rstrip('/')
        if path == '/management':
            page = (current_query_values.get('review') or current_query_values.get('tool') or [''])[0]
        else:
            page = path.removeprefix('/management/frame/') if path.startswith('/management/frame/') else LEGACY_MANAGEMENT_PATHS.get(path + '/', path.lstrip('/'))
        if page in archive_services and current_request_scope['method'] in ('GET', 'HEAD'):
            from urllib.parse import urlencode
            parameters = {key: values[0] for key, values in current_query_values.items() if key in ('session', 'job')}
            parameters['service'] = archive_services[page]
            return await RedirectResponse('/management/assistant/qwen-archive/?' + urlencode(parameters))(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.startswith('/management/frame/') and current_request_path.split('/')[3] in archive_services:
            return await Response(status_code=404)(current_request_scope, current_receive_call, current_send_call)
        direct_path = '/management/frame/hermes-direct'
        if (current_request_path.rstrip('/') == direct_path or
                (current_request_path.rstrip('/') == '/management' and
                 (current_query_values.get('review') or current_query_values.get('tool')) == ['hermes-direct'])):
            if current_request_scope['method'] not in ('GET', 'HEAD'):
                return await Response(status_code=405)(current_request_scope, current_receive_call, current_send_call)
            from urllib.parse import urlencode
            parameters = {key: values[0] for key, values in current_query_values.items() if key in ('job', 'session', 'search')}
            parameters['panel'] = 'jobs' if 'job' in parameters else 'capabilities'
            return await RedirectResponse('/management/frame/hermes-agent/?' + urlencode(parameters))(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.startswith(direct_path + '/'):
            return await Response(status_code=404)(current_request_scope, current_receive_call, current_send_call)
        history_path = '/management/frame/operations-history'
        if current_request_scope.get('method') in ('GET', 'HEAD') and (
            current_request_path.rstrip('/') == history_path or
            (current_request_path.rstrip('/') == '/management' and current_query_values.get('tool') == ['operations-history'])
        ):
            from urllib.parse import urlencode
            parameters = {'panel': 'jobs'}
            for key in ('session', 'job'):
                if current_query_values.get(key):
                    parameters[key] = current_query_values[key][0]
            return await RedirectResponse('/management/frame/hermes-agent/?' + urlencode(parameters))(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.startswith(history_path + '/'):
            return await Response(status_code=404)(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/management/frame/character-review' or current_request_path.startswith('/management/frame/character-review/') or 'character-review' in current_query_values.get('tool', []):
            return await Response('캐릭터 표현 검수 페이지는 폐기되었습니다.', status_code=410)(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope.get('method') == 'GET' and current_request_path.rstrip('/') == '/management':
            from tools.management.common.management_catalog import REACT_REVIEW_PATHS
            tool = current_query_values.get('tool', [''])[0]
            if not tool and set(current_query_values) <= {'session', 'category'}:
                tool = 'hermes-agent'
            if tool in REACT_REVIEW_PATHS:
                from urllib.parse import urlencode
                omitted = {'tool'} if tool == 'hermes-agent' else {'tool', 'category'}
                query = urlencode({key: values for key, values in current_query_values.items() if key not in omitted}, doseq=True)
                target = REACT_REVIEW_PATHS[tool] + ('?' + query if query else '')
                return await RedirectResponse(target)(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') in ('/character-animation/sprite-editor-v2', '/management/frame/sprite-editor-v2') or current_request_path.startswith('/management/frame/sprite-editor-v2/'):
            current_retired_response = Response('스프라이트 정규화 편집기 v2는 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') in ('/wan22-animate', '/wan22-animate-generator') or current_request_path.startswith(('/wan22-animate/', '/wan22-animate-generator/', '/management/frame/wan22-animate-generator')) or 'wan22-animate-generator' in current_query_values.get('tool', []):
            return await Response('Wan2.2 Animate 생성기·모델·결과는 폐기되었습니다.', status_code=410, media_type='text/plain')(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/hy-motion-generator' or current_request_path.startswith(('/hy-motion-generator/', '/management/frame/hy-motion-generator')) or 'hy-motion-generator' in current_query_values.get('tool', []):
            current_retired_response = Response('HY-Motion 생성기와 결과는 폐기되었습니다. Kimodo를 사용하세요.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/anny-attributes' or current_request_path.startswith(('/anny-attributes/', '/management/frame/anny-attributes', '/management/frame/anny-attribute-renderer')) or any(current_tool_value in ('anny-attributes','anny-attribute-renderer') for current_tool_value in current_query_values.get('tool', [])):
            current_retired_response = Response('ANNY 속성 렌더러·모델·결과는 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/anny-landmarks' or current_request_path.startswith(('/anny-landmarks/', '/management/frame/anny-landmarks')) or 'anny-landmarks' in current_query_values.get('tool', []):
            current_retired_response = Response('ANNY 해부학 기준점 페이지와 기능은 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/animation-separation' or current_request_path.startswith(('/animation-separation/', '/management/frame/animation-separation')) or 'animation-separation' in current_query_values.get('tool', []):
            current_retired_response = Response('캐릭터 레퍼런스 복장 분리 생성기와 이력은 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/outfit-transfer' or current_request_path.startswith(('/outfit-transfer/', '/management/frame/outfit-transfer-generator')) or 'outfit-transfer-generator' in current_query_values.get('tool', []):
            current_retired_response = Response('복장 착용 생성기와 이력은 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/pose-transfer' or current_request_path.startswith(('/pose-transfer/', '/management/frame/pose-transfer-generator')) or 'pose-transfer-generator' in current_query_values.get('tool', []):
            current_retired_response = Response('포즈 변환 생성기와 결과는 폐기되었습니다.', status_code=410)
            return await current_retired_response(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope.get('method')=='GET' and (current_request_path.rstrip('/') in ('/management','/management/frame/static-review') or current_request_path.endswith('/anchors.html')) and current_source_path.is_file():
            from tools.management.common.sprite_review_redirect import resolve_sprite_review_redirect
            import json
            current_sprite_redirect=resolve_sprite_review_redirect(current_request_path,current_query_values,json.loads(current_source_path.read_text()).get('pages',[]))
            if current_sprite_redirect:
                return await RedirectResponse(current_sprite_redirect)(current_request_scope,current_receive_call,current_send_call)
        if current_request_scope.get('method') in ('GET', 'HEAD'):
            from tools.management.common.management_catalog import game_review_document_path
            if current_request_path in current_static_routes and game_review_document_path(current_request_path):
                document = current_root_path / current_request_path.lstrip('/')
                if document.is_file():
                    return await FileResponse(document)(current_request_scope, current_receive_call, current_send_call)
            if current_request_path.rstrip('/') in ('/management', '/management/frame/static-review'):
                identifier = (current_query_values.get('review') or current_query_values.get('tool') or [''])[0]
                document_path = next((path for path, name in current_static_routes.items()
                                      if name == identifier and game_review_document_path(path)), None) if isinstance(current_static_routes, dict) else None
                if document_path:
                    from urllib.parse import urlencode
                    parameters = parse_qs(current_request_scope['query_string'].decode(), keep_blank_values=True)
                    query = urlencode({key: values for key, values in parameters.items()
                                       if key in ('locale', 'session', 'field', 'overview')}, doseq=True)
                    return await RedirectResponse(document_path + ('?' + query if query else ''))(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope.get('method') in ('GET', 'HEAD') and current_request_path.rstrip('/') == '/management':
            from urllib.parse import urlencode
            from tools.management.common.management_catalog import LEGACY_PAGE_IDENTIFIER_VALUES, load_manager_page_records, resolve_management_page_path
            identifier = (current_query_values.get('review') or current_query_values.get('tool') or [''])[0]
            identifier = LEGACY_PAGE_IDENTIFIER_VALUES.get(identifier, identifier)
            records = load_manager_page_records(current_source_path, current_animation_catalog=True) if identifier and current_source_path.is_file() else []
            selected = next((row for row in records if row['id'] == identifier), None)
            target = resolve_management_page_path(selected) if selected else None
            if identifier and not target:
                return await Response('등록된 관리 도구를 찾을 수 없습니다.', status_code=404)(current_request_scope, current_receive_call, current_send_call)
            destination = urlsplit(target or '/management/frame/hermes-agent/')
            parameters = parse_qs(destination.query, keep_blank_values=True)
            for key, values in current_query_values.items():
                if key not in ('tool', 'review') and (key != 'category' or not target):
                    parameters[key] = values
            query = urlencode(parameters, doseq=True)
            return await RedirectResponse(destination.path + ('?' + query if query else ''))(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.rstrip('/') == '/management/frame/static-review' or current_request_path.startswith('/management/frame/static-review/'):
            return await Response('등록된 검수 화면을 찾을 수 없습니다.', status_code=404)(current_request_scope, current_receive_call, current_send_call)
        if current_request_path in LEGACY_MANAGEMENT_PATHS:
            current_redirect_value = RedirectResponse('/management/frame/' + LEGACY_MANAGEMENT_PATHS[current_request_path] + '/?' + current_request_scope.get('query_string', b'').decode())
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.startswith('/management/frame/kimodo-generator/'):
            return await Response(status_code=404)(current_request_scope, current_receive_call, current_send_call)
        elif current_request_path == '/management' or current_request_path.startswith(('/management/config', '/management/gradio_api/', '/management/assets/', '/management/theme', '/management/favicon')) or current_request_path == '/management/':
            return await Response(status_code=404)(current_request_scope,current_receive_call,current_send_call)
        elif current_request_path == '/' and current_source_path.is_file():
            current_query_text = current_request_scope.get('query_string', b'').decode()
            current_redirect_value = RedirectResponse('/management/' + '?' + current_query_text if current_query_text else '/management/frame/hermes-agent/')
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        elif (current_request_path in current_static_routes and current_query_values.get('embedded') != ['gradio-static']) or current_request_path == '/isloon-map-review/map-review.html':
            current_redirect_value = RedirectResponse('/management/?' + current_request_scope.get('query_string', b'').decode())
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        current_request_body = bytearray()
        while True:
            current_request_message = await current_receive_call()
            if current_request_message['type'] == 'http.disconnect':
                return
            current_request_body.extend(current_request_message.get('body', b''))
            if not current_request_message.get('more_body'):
                break
        current_response_value = await asyncio.to_thread(execute_legacy_request, current_handler_class, current_root_path, current_request_scope, bytes(current_request_body))
        await current_response_value(current_request_scope, current_receive_call, current_send_call)

    from time import monotonic
    from uuid import uuid4
    from typing import Literal
    mock_jobs = {"progress": {}, "dwpose": {}, "animate2": {}}

    @current_root_application.post('/management/assistant/mock-jobs')
    async def start_mock_job(scope: Literal["progress", "dwpose", "animate2"] = "progress"):
        identifier = 'mock-' + uuid4().hex
        mock_jobs[scope][identifier] = monotonic()
        return {'id': identifier}

    @current_root_application.get('/management/assistant/mock-jobs')
    async def read_mock_jobs(scope: Literal["progress", "dwpose", "animate2"] = "progress"):
        now = monotonic()
        rows = []
        for identifier, started in reversed(mock_jobs[scope].items()):
            elapsed = now - started
            if elapsed < (7 if scope != "progress" else 5):
                state, message = 'queued', '모의 대기열'
            elif elapsed < (18 if scope != "progress" else 15):
                state, message = 'running', '모의 실행 · 1 / 2'
            else:
                state, message = 'completed', '모의 결과 표시 완료'
            rows.append({'id': identifier, 'status': state, 'message': message})
        return rows

    def require_flux_page(service):
        from fastapi import HTTPException
        if service not in ('flux-image', 'flux-prop', 'flux-vegetation', 'flux-billboard', 'flux-mannequin', 'flux-building', 'flux-character', 'flux-seamless', 'flux-expression'):
            raise HTTPException(404, '등록되지 않은 생성기 화면입니다.')

    def flux_page_manager(service):
        if service == 'flux-expression':
            from tools.management.domains.image.flux_expression_generation import FluxExpressionGenerationManager
            return FluxExpressionGenerationManager()
        from tools.management.domains.image.flux_image_generation import FluxImageGenerationManager
        return FluxImageGenerationManager(service)

    @current_root_application.get('/management/assistant/flux-expression-face')
    def flux_expression_face():
        return FileResponse(Path(__file__).resolve().parents[3] / 'baseline/player/default/default-face-front-v1.png')

    @current_root_application.get('/management/assistant/flux-defaults/{service}')
    def flux_page_defaults(service: str):
        from tools.management.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        require_flux_page(service)
        if service == 'flux-expression':
            from tools.management.domains.image.expression_generation import load_expression_configuration
            from tools.management.domains.image.flux_expression_generation import FLUX_PROMPT_BASE_TEXT
            expressions = [dict(id=item['id'], label=item['label_ko'], text=FLUX_PROMPT_BASE_TEXT.format(expression=item['movement_prompt']))
                           for item in load_expression_configuration()['expressions']]
            return dict(label='표정', description='얼굴 참조 한 장과 표정을 선택하세요.', width=768, height=512,
                        minimum=1, prompt=expressions[0]['id'], expressions=expressions)
        label, description, width, height, minimum = FLUX_IMAGE_PROFILE_RECORDS[service]
        prompt = 'Top-down repeatable ground texture with even lighting. Material: ' if service == 'flux-seamless' else ''
        if service in ('flux-prop', 'flux-vegetation'):
            source = service.removeprefix('flux-') + '-qwen-prompt.txt'
            prompt = (Path(__file__).resolve().parents[3] / 'generators/image/config' / source).read_text().strip().replace('transparent background', 'plain background')
        guide = {}
        if service == 'flux-billboard':
            from tools.management.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT
            guide = dict(layouts=BILLBOARD_LAYOUT_PROFILES, subject=BILLBOARD_DEFAULT_SUBJECT)
        if service == 'flux-character':
            body = importlib.import_module('generators.character-generator.body_references')
            guide = dict(guides=body.load_body_reference_catalog(), rolePrompt=body.BODY_REFERENCE_ROLE_PROMPT)
        if service == 'flux-building':
            from tools.management.domains.image.building_prompt import BUILDING_STRUCTURE_RECORDS, describe_building_structure_label
            guide = {'guides': [dict(id=name, label=describe_building_structure_label(name),
                                       roof=row['roof'], entrance=row['entrance'])
                                   for name, row in BUILDING_STRUCTURE_RECORDS.items()]}
        if service == 'flux-mannequin':
            presets = importlib.import_module('generators.mannequin-generator.page.interface').MANNEQUIN_PRESET_RECORDS
            guide = {'stages': [{'id': key, 'label': row[0]} for key, row in presets.items()]}
        return dict(**guide, label=label, description=description, width=width, height=height, prompt=prompt, minimum=minimum)

    @current_root_application.get('/management/assistant/flux-building-guide/{name}')
    @current_root_application.get('/management/assistant/flux-character-guide/{name}')
    def flux_reference_guide(request: Request, name: str, thumbnail: bool = False):
        from fastapi import HTTPException
        from PIL import Image
        from tools.management.domains.image.building_prompt import load_building_layout_preset
        try:
            load = load_building_layout_preset
            if request.url.path.startswith('/management/assistant/flux-character-guide/'):
                load = importlib.import_module('generators.character-generator.body_references').load_body_reference_image
            with load(name) as image, io.BytesIO() as output:
                if thumbnail:
                    image.thumbnail((320, 320), Image.Resampling.LANCZOS)
                image.save(output, format='PNG')
                return Response(output.getvalue(), media_type='image/png')
        except ValueError as error:
            raise HTTPException(404, str(error)) from error

    @current_root_application.get('/management/assistant/flux-mannequin-stage/{stage}')
    def flux_mannequin_stage(stage: str):
        import base64
        from fastapi import HTTPException
        presets = importlib.import_module('generators.mannequin-generator.page.interface')
        if stage not in presets.MANNEQUIN_PRESET_RECORDS:
            raise HTTPException(404, '등록되지 않은 마네킨 제작 단계입니다.')
        prompt, first, second = presets.load_mannequin_preset(stage)
        images = []
        for image in (first, second):
            if image is not None:
                with image, io.BytesIO() as output:
                    image.save(output, format='PNG')
                    images.append(base64.b64encode(output.getvalue()).decode('ascii'))
        width, height = (1024, 1024) if stage == 'face' else (768, 1152)
        return dict(prompt=prompt, images=images, width=width, height=height)

    @current_root_application.post('/management/assistant/flux-billboard-guide')
    def flux_billboard_guide(payload: dict):
        import io
        import base64
        from fastapi import HTTPException
        from tools.management.domains.image.billboard_guide_prompt import compose_billboard_guide_prompt, load_billboard_guide_image
        layout = payload.get('layout')
        try:
            prompt = compose_billboard_guide_prompt(layout, payload.get('subject')).replace('transparent background', 'plain background')
            with load_billboard_guide_image(layout) as image, io.BytesIO() as output:
                image.save(output, format='PNG')
                return {'prompt': prompt, 'image': base64.b64encode(output.getvalue()).decode('ascii')}
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @current_root_application.get('/management/assistant/flux-seamless-comparison/{job}')
    def flux_seamless_comparison(job: str):
        from fastapi import HTTPException
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        from tools.management.domains.image.flux_image_generation import FluxImageGenerationManager
        if not validate_service_job_identifier('flux-seamless', job):
            raise HTTPException(404, '생성 ID를 확인하세요.')
        directory = FluxImageGenerationManager('flux-seamless').job_storage_root / job
        metadata = directory / 'request.json'
        if directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
            raise HTTPException(404, '저장된 요청을 찾을 수 없습니다.')
        method = json.loads(metadata.read_text()).get('seamless_method', 'edge-blend')
        files = [('3×3 반복 검수', 'tiled-preview.png')]
        if method in ('edge-blend', 'circular-vae'):
            files.insert(0, ('일반 VAE 생성 원본', 'raw-result.png'))
        if method == 'circular-vae':
            files.append(('동일 잠재값 · 경계 보간 3×3', 'blend-preview.png'))
        return {'method': method, 'images': [
            {'label': label, 'url': f'/flux-seamless-generator/jobs/{job}/{name}'}
            for label, name in files if (directory / name).is_file() and not (directory / name).is_symlink()
        ]}

    @current_root_application.get('/management/assistant/flux-image-input/{job}')
    def flux_image_saved_input(job: str, service: str = "flux-image"):
        require_flux_page(service)
        import base64
        import io
        import json
        from fastapi import HTTPException
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        from tools.management.domains.image.flux_image_generation import FluxImageGenerationManager
        from tools.management.domains.image.flux_input_restore import restore_flux_image_inputs

        if not validate_service_job_identifier(service, job):
            raise HTTPException(404, '생성 ID를 확인하세요.')
        root = flux_page_manager(service).job_storage_root
        directory = root / job
        path = directory / 'request.json'
        if directory.is_symlink() or path.is_symlink() or not path.is_file():
            raise HTTPException(404, '저장된 입력을 찾을 수 없습니다.')
        try:
            record = {'id': job, 'request': json.loads(path.read_text())}
            if service == 'flux-expression':
                from tools.management.domains.image.flux_expression_generation import restore_flux_expression_inputs
                first, prompt, width, height, seed, tag, translation = restore_flux_expression_inputs(record, root)
                second, steps = None, 16
            else:
                restored = restore_flux_image_inputs(record, service, root)
                prompt, first, second, width, height, steps, seed, tag = restored[:8]
                translation = restored[8] if service != 'flux-building' else ''
            if not isinstance(prompt, str) or not isinstance(translation, str):
                raise ValueError('저장된 번역 입력을 확인하세요.')
            images = []
            for reference in (first, second):
                if reference is not None:
                    with io.BytesIO() as output:
                        reference.save(output, format='PNG')
                        images.append(base64.b64encode(output.getvalue()).decode('ascii'))
        except (ValueError, OSError) as error:
            raise HTTPException(422, str(error)) from error
        return {'id': job, 'request': dict(prompt=prompt, width=width, height=height, seed=seed, tag=tag,
                                           translation_source_ko=translation, steps=steps), 'images': images}

    @current_root_application.post('/management/assistant/flux-image-preview')
    def flux_image_preview(payload: dict, service: str = "flux-image"):
        require_flux_page(service)
        from fastapi import HTTPException
        from tools.management.domains.image.flux_image_generation import FluxImageGenerationManager
        if payload.get('action') != 'generate':
            raise HTTPException(422, '이미지 생성 입력을 확인하세요.')
        try:
            request = flux_page_manager(service).validate_generation_request(payload)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return {'prompt': request['prompt'], 'translation': request.get('translation_source_ko') or request.get('building_design_ko')}

    @current_root_application.get('/management/assistant/kimodo-defaults')
    def kimodo_defaults():
        from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS
        return {key: KIMODO_DEFAULT_SETTINGS[key] for key in ("prompt", "frames", "steps", "seed")}

    @current_root_application.get('/management/assistant/kimodo-generation-template')
    def kimodo_generation_template():
        from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, KIMODO_DIRECTION_RECORDS
        inputs = {key: value for key, value in KIMODO_DEFAULT_SETTINGS.items() if key != "schema_version"}
        return {"inputs": {**inputs, "camera_elevation_degrees": 0}, "directions": KIMODO_DIRECTION_RECORDS}

    @current_root_application.get('/management/assistant/kimodo-input/{job}')
    def kimodo_saved_input(job: str):
        import base64
        import json
        from fastapi import HTTPException
        from generators.kimodo.contracts import KIMODO_JOB_STORAGE
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        from tools.management.domains.kimodo.keyframe_storage import hash_kimodo_keyframe_source, validate_kimodo_job_keyframe_snapshots

        directory = KIMODO_JOB_STORAGE / job
        path = directory / "request.json"
        if not validate_service_job_identifier("kimodo", job) or directory.is_symlink() or path.is_symlink() or not path.is_file():
            raise HTTPException(404, "저장된 입력을 찾을 수 없습니다.")
        try:
            saved = json.loads(path.read_text())
            template = kimodo_generation_template()
            inputs = {key: saved.get(key, default) for key, default in template["inputs"].items()}
            if saved.get("action") == "reference-analysis":
                inputs.update(prompt="", directions=template["inputs"]["directions"])
            else:
                inputs.update(directions=saved.get("directions", ["front_left"]), openpose_scale_percent=saved.get("openpose_scale_percent", 100))
            references = []
            for index, name in enumerate(saved.get("references", []), 1):
                if index > 8 or name != f"reference-{index}.png":
                    raise ValueError("참조 PNG 기록을 확인하세요.")
                image = directory / name
                if image.is_symlink() or not image.is_file() or image.stat().st_size > 3000000:
                    raise ValueError("참조 PNG 사본을 확인하세요.")
                references.append({"name": name, "data": base64.b64encode(image.read_bytes()).decode("ascii")})
            rows = saved.get("keyframes", [])
            hashes = {}
            if rows:
                validate_kimodo_job_keyframe_snapshots(directory, saved)
                hashes = {row["id"]: hash_kimodo_keyframe_source(row["source"]["files"]) for row in saved["keyframe_snapshots"]}
            elif saved.get("endpoint_pose_id") == "relaxed-standing-v1":
                rows = [{"id": "b0000000000000000000000000000004", "frame": frame} for frame in (1, inputs["frames"])]
            elif saved.get("endpoint_pose_id"):
                raise ValueError("이전 기준 자세를 확인하세요.")
            attachments = {field: json.dumps(saved[field], ensure_ascii=False, allow_nan=False)
                           for field in ("proportion_reviewed_multiview", "proportion_face_anchor_calibration", "proportion_joint_edits")
                           if saved.get(field)}
            return {**template, "inputs": inputs, "references": references, "attachments": attachments,
                    "rows": rows, "hashes": hashes, "segments": saved.get("segment_frames", []),
                    "angles": saved.get("proportion_multiview_angles", []), "hip": saved.get("proportion_projected_hip", False)}
        except (KeyError, OSError, ValueError, TypeError) as error:
            raise HTTPException(422, str(error)) from error

    @current_root_application.post('/management/assistant/kimodo-generation-review')
    def review_kimodo_generation(inputs: dict, serialized: bool = False):
        import json
        from fastapi import HTTPException
        from generators.kimodo.contracts import validate_kimodo_request
        if inputs.keys() - {"proportion_joint_edits", "keyframes", "keyframe_source_hashes", "segment_frames", "proportion_images", "proportion_multiview_angles",
                            "proportion_reviewed_multiview", "proportion_projected_hip", "proportion_face_anchor_calibration"} != kimodo_generation_template()["inputs"].keys():
            raise HTTPException(422, "생성 폼의 입력 항목을 확인하세요.")
        request = {**inputs, "action": "generate"}
        try:
            for field in ("proportion_reviewed_multiview", "proportion_face_anchor_calibration", "proportion_joint_edits"):
                if isinstance(request.get(field), str):
                    request[field] = json.loads(request[field])
            validated = validate_kimodo_request(request)
            if "proportion_images" in request:
                request["proportion_images"] = validated["images"]
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        if serialized:
            return {"request_json": json.dumps(request, ensure_ascii=False, separators=(",", ":"), allow_nan=False)}
        return {"request": request}

    @current_root_application.post('/management/assistant/kimodo-multiview-report')
    def review_kimodo_observations(inputs: dict):
        from fastapi import HTTPException
        from generators.kimodo.multiview_review_report import build_multiview_review_report
        import base64
        import io
        from generators.kimodo.reference_review import render_bound_review_overlay, select_multiview_review_rows
        try:
            # Preserve Python numeric representations used by the observation digest.
            import json
            for key in ("observations", "skeleton", "heldout"):
                if isinstance(inputs.get(key), str):
                    inputs[key] = json.loads(inputs[key])
            report = build_multiview_review_report(inputs["observations"], inputs["skeleton"], inputs.get("heldout"))
            preview = {}
            if "image" in inputs:
                from PIL import Image
                raw = base64.b64decode(inputs["image"], validate=True)
                overlay, _ = render_bound_review_overlay(raw, inputs["skeleton"], report)
                from generators.kimodo.multiview_reviewed_bundle import REVIEWED_BUNDLE_SCHEMA_VERSION, validate_reviewed_multiview_bundle
                from tools.management.domains.image.three_reference_generation import decode_reference_image
                import hashlib
                candidate = {"schema": REVIEWED_BUNDLE_SCHEMA_VERSION, "reference_observations": inputs["observations"],
                             "skeleton": inputs["skeleton"]}
                try:
                    png = decode_reference_image(inputs["image"], composite_transparent_background=True)
                    checked = validate_reviewed_multiview_bundle(candidate, [hashlib.sha256(png).hexdigest()])
                    preview["bundle_json"] = json.dumps(checked, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                except (KeyError, TypeError, ValueError) as error:
                    preview["bundle_error"] = str(error)
                with io.BytesIO() as output:
                    overlay.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    overlay.save(output, "PNG")
                    preview["joint_weights"] = inputs["skeleton"]["joint_weight_table"]
                    preview["overlay_png"] = base64.b64encode(output.getvalue()).decode("ascii")
            return {**preview, "views": [{"angle": view["fitted_yaw_degrees"],
                               "rows": select_multiview_review_rows(report, view["observation"])}
                              for view in report["views"]], "limitations": report["limitations"]}
        except (KeyError, IndexError, AttributeError, TypeError, ValueError, OSError) as error:
            raise HTTPException(422, f"검수 입력 오류 · {error}") from error

    @current_root_application.post('/management/assistant/kimodo-joint-weights')
    def review_kimodo_weights(weights: dict):
        from fastapi import HTTPException
        from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
        try:
            validate_multiview_joint_weights(weights)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return weights

    @current_root_application.get('/management/assistant/kimodo-prompt-examples')
    def kimodo_prompt_examples():
        from generators.kimodo.form_inputs import load_kimodo_examples
        return [{key: example[key] for key in ("id", "label", "prompt")}
                for example in load_kimodo_examples().values()]

    @current_root_application.get('/management/assistant/kimodo-reference-examples')
    def kimodo_reference_examples():
        from generators.kimodo.form_inputs import load_proportion_examples
        return [{"id": key, "label": example["label"]} for key, example in load_proportion_examples().items()]

    @current_root_application.get('/management/assistant/kimodo-reference-examples/{identifier}')
    def kimodo_reference_example(identifier: str):
        import base64
        from fastapi import HTTPException
        from generators.kimodo.form_inputs import load_proportion_examples
        example = load_proportion_examples().get(identifier)
        if example is None:
            raise HTTPException(404, "신체 비율 예시를 찾을 수 없습니다.")
        return [{"name": Path(filename).name, "data": base64.b64encode(Path(filename).read_bytes()).decode("ascii")}
                for filename in example["images"]]

    @current_root_application.get('/management/assistant/kimodo-prompt-examples/{identifier}')
    def kimodo_prompt_example(identifier: str):
        from fastapi import HTTPException
        from generators.kimodo.form_inputs import load_kimodo_examples
        example = load_kimodo_examples().get(identifier)
        if example is None:
            raise HTTPException(404, "동작 예시를 찾을 수 없습니다.")
        references = kimodo_reference_example(example["reference_example"]) if example.get("reference_example") else []
        return {**example, "references": references}

    @current_root_application.post('/management/assistant/kimodo-proposal-review')
    def review_kimodo_proposal(inputs: dict):
        from fastapi import HTTPException
        from tools.management.domains.hermes_agent.delegation_proposal import validate_kimodo_proposal_inputs
        try:
            return {"request": validate_kimodo_proposal_inputs(inputs)}
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @current_root_application.get('/management/assistant/heartmula-examples')
    def heartmula_examples():
        from generators.music.examples import load_music_examples
        return load_music_examples('music-heartmula')

    def register_audio_input_routes(prefix, service):
        music = service == 'music-heartmula'

        @current_root_application.get(prefix)
        def sound_effect_defaults():
            from generators.music.contracts import load_music_defaults
            defaults = load_music_defaults(service)
            return {key: defaults[key] for key in ('prompt', 'seed', 'loop_request')} | {'tag': ''} | (dict(lyrics='', duration_seconds=defaults['duration_seconds']) if music else {})

        @current_root_application.get(prefix + '/{job}')
        def sound_effect_saved_input(job: str):
            from fastapi import HTTPException
            from generators.music.contracts import read_music_record, validate_music_request
            from tools.management.domains.music.generation import MusicGenerationManager
            try:
                directory = MusicGenerationManager(service).resolve_music_job(job)
            except ValueError as error:
                raise HTTPException(404, '오디오 작업을 찾을 수 없습니다.') from error
            path = directory / 'request.json'
            if path.is_symlink() or not path.is_file():
                raise HTTPException(404, '저장된 입력을 찾을 수 없습니다.')
            try:
                saved = read_music_record(path)
                if saved['action'] != 'generate':
                    raise ValueError('모델 준비 작업에는 생성 입력이 없습니다.')
                fields = ('prompt', 'duration_seconds', 'seed', 'loop_request', 'tag') + (('lyrics',) if music else ())
                inputs = validate_music_request(service, {key: saved[key] for key in fields})
            except (KeyError, TypeError, ValueError, OSError) as error:
                raise HTTPException(422, '저장된 오디오 생성 입력을 확인하세요.') from error
            return {'id': job, 'request': {key: inputs[key] for key in ('prompt', 'seed', 'loop_request', 'tag') + (('lyrics','duration_seconds') if music else ())}}

        @current_root_application.post(prefix)
        def sound_effect_preview(payload: dict):
            from generators.music.contracts import build_music_request
            from fastapi import HTTPException
            if payload.get('action') != 'generate':
                raise HTTPException(422, '오디오 생성 입력을 확인하세요.')
            try:
                request = build_music_request(service, payload)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            return {'final_prompt': request['final_prompt']}

    register_audio_input_routes('/management/assistant/sfx-input', 'sfx-dasheng-audiogen')
    register_audio_input_routes('/management/assistant/heartmula-input', 'music-heartmula')

    @current_root_application.get('/management/assistant/animate-input/{job}/{part}')
    def animate_input(job: str, part: Literal["request", "reference", "motion"]):
        from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier('wan22-animate2', job):
            return Response(status_code=404)
        directory = ANIMATE_JOB_STORAGE / job
        names = {"request": "request.json", "reference": "reference-1.png", "motion": "driving.mp4"}
        if directory.is_symlink() or any((directory / name).is_symlink() or not (directory / name).is_file() for name in names.values()):
            return Response(status_code=404)
        if part != "request":
            return FileResponse(directory / names[part], media_type={"reference":"image/png", "motion":"video/mp4"}[part])
        try:
            request = json.loads((directory / names[part]).read_bytes())
            fields = {key:request[key] for key in ("prompt", "frames", "steps", "seed")}
            if request["references"] != [names["reference"]] or not isinstance(fields["prompt"], str) or any(type(fields[key]) is not int for key in ("frames","steps","seed")):
                raise ValueError("입력 기록 오류")
        except (KeyError, TypeError, ValueError, OSError):
            return Response(status_code=422)
        prefix = "/management/assistant/animate-input/" + job
        return {"id":job, "request":fields, "reference":prefix+"/reference", "motion":prefix+"/motion"}

    @current_root_application.get('/management/assistant/vace-input/{job}/{part}')
    def vace_input(job: str, part: str):
        from generators.wan_vace.contracts import VACE_JOB_STORAGE, VACE_DEFAULT_SETTINGS
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier('wan22-vace', job):
            return Response(status_code=404)
        directory = VACE_JOB_STORAGE / job
        metadata = directory / 'request.json'
        if directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
            return Response(status_code=404)
        try:
            request = json.loads(metadata.read_bytes())
            fields = {key:request[key] for key in (*VACE_DEFAULT_SETTINGS, 'prompt', 'negative_prompt')}
            mode = fields['mode']
            names = {} if mode == 'text' else {'reference':'reference-1.png'}
            if mode == 'pose':
                names['pose_video'] = 'pose-video.mp4'
            if mode in ('video_edit','video_condition'):
                names['edit_video'] = 'edit-video.mp4'
            if mode == 'video_edit':
                names['edit_mask'] = 'edit-mask.mp4'
            if request['references'] != ([names['reference']] if 'reference' in names else []):
                raise ValueError('참조 사본 불일치')
        except (ValueError, OSError, TypeError, KeyError):
            return Response(status_code=422)
        if any((directory/name).is_symlink() or not (directory/name).is_file() for name in names.values()):
            return Response(status_code=404)
        if part == 'request':
            return {'id':job, 'request':fields, 'attachments':list(names)}
        if part not in names:
            return Response(status_code=404)
        return FileResponse(directory/names[part], media_type='image/png' if part=='reference' else 'video/mp4')

    @current_root_application.post('/management/assistant/billboard-registration-review')
    async def billboard_registration_review(request: Request):
        from tools.management.common.management_gateway import parse_management_request_json
        from tools.management.domains.map_assets.registration import validate_billboard_registration
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > 2_000_000:
                return JSONResponse({'error': '등록 요청 JSON은 2MB 이하여야 합니다.'}, status_code=413)
            content.extend(chunk)
        try:
            payload = parse_management_request_json(content.decode('utf-8'))
            await asyncio.to_thread(validate_billboard_registration, payload)
        except (ValueError, KeyError, TypeError, OSError) as error:
            return JSONResponse({'error': str(error)}, status_code=422)
        return JSONResponse(payload)

    @current_root_application.get('/management/assistant/field-renderer.mjs')
    def assistant_field_renderer():
        import yaml
        manifest = Path(__file__).resolve().parents[1] / 'ui/map/vendor/field-renderer/manifest.yaml'
        version = yaml.safe_load(manifest.read_text())['version']
        return RedirectResponse(f'/isloon-map-review/vendor/field-renderer/{version}/field-renderer.mjs')

    @current_root_application.get('/management/assistant/building-image/{texture}')
    def building_image(texture: str):
        import re
        from tools.management.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
        if not re.fullmatch(r'town-[a-z0-9-]+-v[1-9][0-9]*|ward-tower-v1', texture):
            return Response(status_code=404)
        root, records = load_registered_tiles()
        relative = 'assets/buildings/' + texture + '.png'
        if relative not in records:
            return Response(status_code=404)
        path, _ = resolve_registered_asset(relative, root, records, 'assets/buildings')
        return FileResponse(path, media_type='image/png')

    @current_root_application.get('/management/assistant/fun-template')
    def fun_template():
        from generators.wan_fun.contracts import FUN_DEFAULT_SETTINGS, FUN_MAX_FRAME_COUNT, FUN_MAX_SEED_VALUE
        from generators.wan_fun.page.examples import FUN_MODEL_CHOICES, load_fun_example_catalog
        return {'defaults': dict(FUN_DEFAULT_SETTINGS, model_profile='wan22-14b'),
                'maximum_frames': FUN_MAX_FRAME_COUNT, 'maximum_seed': FUN_MAX_SEED_VALUE,
                'models': [{'id': key, 'label': label} for label, key in FUN_MODEL_CHOICES],
                'examples': [{'id': key, 'label': label} for key, label in load_fun_example_catalog().items()]}

    @current_root_application.get('/management/assistant/fun-example/{identifier}')
    def fun_example(identifier: str):
        from generators.wan_fun.page.examples import load_fun_example_catalog, read_fun_example_request
        if identifier not in load_fun_example_catalog():
            return Response(status_code=404)
        from generators.wan_fun.page.examples import FUN_EXAMPLE_STORAGE_ROOT
        from generators.wan_fun.video_input import inspect_fun_pose_video
        maximum, summary = inspect_fun_pose_video(FUN_EXAMPLE_STORAGE_ROOT / identifier / 'pose-input.mp4')
        return {'id': identifier, 'request': read_fun_example_request(identifier),
                'video': {'maximum_frames': maximum, 'summary': summary}}

    @current_root_application.post('/management/assistant/fun-video-info')
    async def fun_video_info(request: Request):
        import tempfile
        from generators.wan_fun.video_input import FUN_VIDEO_MAXIMUM_BYTES, inspect_fun_pose_video
        with tempfile.NamedTemporaryFile(suffix='.mp4') as video:
            async for chunk in request.stream():
                if video.tell() + len(chunk) > FUN_VIDEO_MAXIMUM_BYTES:
                    return JSONResponse({'summary': 'MP4 최대 크기는 32MiB입니다.'}, status_code=413)
                video.write(chunk)
            video.flush()
            maximum, summary = await asyncio.to_thread(inspect_fun_pose_video, video.name)
        return JSONResponse({'maximum_frames': maximum, 'summary': summary}, status_code=200 if maximum else 422)

    @current_root_application.get('/management/assistant/fun-input/{job}')
    def fun_saved_input(job: str):
        import base64
        import hashlib
        from generators.wan_fun.contracts import validate_fun_request, reject_retired_rgb_input
        from generators.wan_fun.video_input import inspect_fun_pose_video
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        from tools.management.domains.hermes_agent.video_operations import make_hermes_video_source_manager
        if not validate_service_job_identifier('wan22-fun-control', job):
            return Response(status_code=404)
        root = Path(make_hermes_video_source_manager('wan22-fun-control').job_storage_root)
        directory = root / job
        metadata = directory / 'request.json'
        if root.is_symlink() or directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
            return Response(status_code=404)
        try:
            saved = json.loads(metadata.read_text())
            reject_retired_rgb_input(saved)
            if saved.get('pose_video_file') != 'pose-input.mp4' or saved.get('references') != ['reference-1.png']:
                raise ValueError('처리된 포즈 MP4와 참조 이미지가 있는 작업만 복원할 수 있습니다.')
            video = directory / 'pose-input.mp4'
            image = directory / 'reference-1.png'
            if video.is_symlink() or image.is_symlink():
                raise ValueError('입력 사본 경로 오류')
            data = video.read_bytes()
            if saved.get('pose_video_sha256') and hashlib.sha256(data).hexdigest() != saved['pose_video_sha256']:
                raise ValueError('입력 포즈 영상 사본이 변경되었습니다.')
            fields = ('action', 'prompt', 'negative_prompt', 'control_type', 'width', 'height',
                      'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale', 'switch_ratio')
            draft = {key: saved[key] for key in fields}
            draft.update(model_profile=saved.get('model_profile', 'wan22-14b'),
                         images=[base64.b64encode(image.read_bytes()).decode()],
                         pose_video=base64.b64encode(data).decode())
            validate_fun_request(draft)
            maximum, summary = inspect_fun_pose_video(video)
        except (OSError, KeyError, TypeError, ValueError):
            return JSONResponse({'detail': '저장된 참조 이미지 또는 포즈 영상으로 입력을 복원할 수 없습니다.'}, status_code=422)
        return JSONResponse({'id': job, 'request': draft, 'video': {'maximum_frames': maximum, 'summary': summary}},
                            headers={'Cache-Control': 'no-store'})

    @current_root_application.get('/management/assistant/fun-pose/{job}')
    def fun_pose_input(job: str):
        from tools.management.domains.hermes_agent.video_operations import make_hermes_video_source_manager
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier('wan22-fun-control', job):
            return Response(status_code=404)
        root = Path(make_hermes_video_source_manager('wan22-fun-control').job_storage_root)
        directory = root / job
        path = directory / 'pose-input.mp4'
        if root.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
            return Response(status_code=404)
        return FileResponse(path, media_type='video/mp4', headers={'Cache-Control':'no-store'})

    @current_root_application.get('/management/assistant/vace-template')
    def vace_template():
        from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS, VACE_MAXIMUM_SEED_VALUE
        from generators.wan_vace.page.inputs import VACE_INPUT_CHOICES, VACE_MODE_HELP_TEXT
        return {"defaults": VACE_DEFAULT_SETTINGS, "maximum_seed": VACE_MAXIMUM_SEED_VALUE,
                "modes": [{"id": mode, "label": label, "help": VACE_MODE_HELP_TEXT[mode]}
                          for label, mode in VACE_INPUT_CHOICES]}

    @current_root_application.get('/management/assistant/dwpose-input/{job}')
    def dwpose_input(job: str):
        from generators.dwpose.contracts import DWPOSE_JOB_STORAGE
        from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier('dwpose', job):
            return Response(status_code=404)
        directory = DWPOSE_JOB_STORAGE / job
        metadata = directory / 'request.json'
        reference = directory / 'reference-1.png'
        if directory.is_symlink() or any(path.is_symlink() or not path.is_file() for path in (metadata, reference)):
            return Response(status_code=404)
        try:
            request = json.loads(metadata.read_bytes())
            if not isinstance(request, dict):
                raise ValueError('작업 요청 형식 오류')
            options = [request.get(key, False) for key in ('pose_include_hands', 'pose_include_face')]
            if any(type(value) is not bool for value in options):
                raise ValueError('포즈 옵션 형식 오류')
            image = reference.read_bytes()
        except (ValueError, OSError):
            return Response(status_code=422)
        return Response(image, media_type='image/png', headers={
            'Cache-Control': 'no-store', 'X-Pose-Hands': json.dumps(options[0]), 'X-Pose-Face': json.dumps(options[1]),
        })

    @current_root_application.get('/management/assistant/history-services')
    def history_services():
        from tools.management.common.management_catalog import REACT_REVIEW_PATHS
        from tools.management.common.source_history_catalog import SOURCE_HISTORY_AUDIO_SERVICES, SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_VIDEO_SERVICES
        from tools.management.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        from tools.management.domains.hermes_agent.image_source_operations import IMAGE_SOURCE_SERVICES
        kinds = {
            **dict.fromkeys(SOURCE_HISTORY_AUDIO_SERVICES, 'audio'),
            **dict.fromkeys(SOURCE_HISTORY_VIDEO_SERVICES, 'video'),
            **dict.fromkeys((*FLUX_IMAGE_PROFILE_RECORDS, 'flux-expression'), 'flux'),
            **dict.fromkeys(IMAGE_SOURCE_SERVICES, 'image'),
        }
        return [
            {'service': service, 'command': 'hermes-audio-source-history' if service in SOURCE_HISTORY_AUDIO_SERVICES else 'hermes-generator-source-history'}
            | {'video_result': service in SOURCE_HISTORY_VIDEO_SERVICES, 'result_kind': kinds.get(service)}
            | ({'result_path': path} if (path := REACT_REVIEW_PATHS.get(service) or REACT_REVIEW_PATHS.get(service + '-generator')) else {})
            for service in sorted(set(SOURCE_HISTORY_GENERATOR_SERVICES) | set(SOURCE_HISTORY_AUDIO_SERVICES))
        ]

    @current_root_application.get('/management/assistant/capabilities')
    def assistant_capabilities():
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.hermes_capability_table import format_capability_table
        catalog = execute_remote_management_command('hermes-agent', 'hermes-capabilities', {})
        rows, summary = format_capability_table(catalog)
        return {'rows': rows, 'summary': summary}

    @current_root_application.get('/management/assistant/operations-priority-receipt/{identifier}')
    def operations_priority_receipt(identifier: str):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import read_operations_priority_request
        return {'notice': read_operations_priority_request(identifier, execute_remote_management_command)}

    @current_root_application.post('/management/assistant/operations-priority-review')
    def operations_priority_review(target: dict):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import prepare_operations_priority_request
        request, notice, identifier = prepare_operations_priority_request(target, execute_remote_management_command)
        return dict(request=request, notice=notice, identifier=identifier)

    @current_root_application.post('/management/assistant/operations-recovery-review')
    def operations_recovery_review(target: dict):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import prepare_operations_reservation_recovery
        request, notice, identifier = prepare_operations_reservation_recovery(target, execute_remote_management_command)
        return dict(request=request, notice=notice, identifier=identifier)

    @current_root_application.get('/management/assistant/operations-recovery-receipt/{identifier}')
    def operations_recovery_receipt(identifier: str):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import read_operations_reservation_recovery_receipt
        return {'notice': read_operations_reservation_recovery_receipt(identifier, execute_remote_management_command)}

    @current_root_application.post('/management/assistant/operations-reservation-inspect')
    def operations_reservation_inspect(target: dict):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import inspect_operations_reservation_target
        return {'notice': inspect_operations_reservation_target(target, execute_remote_management_command)}

    @current_root_application.post('/management/assistant/operations-capture-status')
    def operations_capture_status(payload: dict):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import read_operations_capture_status
        return {'notice': read_operations_capture_status(payload.get('row'), execute_remote_management_command)}

    @current_root_application.get('/management/assistant/operations-gpu')
    def operations_gpu():
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import summarize_operations_queue_snapshot, summarize_operations_reservation_snapshot, reservation_inspection_target
        try:
            snapshot = execute_remote_management_command('hermes-agent', 'hermes-management-status', {})
        except (OSError, RuntimeError, ValueError):
            snapshot = None
        jobs, counts, queue_notice = summarize_operations_queue_snapshot(snapshot)
        index, _, reservations, reservation_notice = summarize_operations_reservation_snapshot(snapshot)
        return [
            dict(title='GPU 대기열', columns=['순서', '대기열', '작업 ID', '원 서비스', '캡처 접수 ID'],
                 rows=jobs, summary=queue_notice, available=counts is not None),
            dict(title='GPU 예약', columns=['상태', '서비스', '작업 ID', '메모리(MiB)', '리더 상태', '원 서비스'],
                 rows=reservations, summary=reservation_notice, available=index is not None,
                 inspection_targets=[reservation_inspection_target(reservations, i)[0] for i in range(len(reservations))]),
        ]

    @current_root_application.post('/management/assistant/operations-diff')
    def operations_diff(payload: dict):
        from fastapi import HTTPException
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.operations_history import read_hermes_diff_page
        try:
            text, notice, cursor = read_hermes_diff_page(payload.get('id'), payload.get('cursor'), command=execute_remote_management_command)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return dict(text=text, notice=notice, cursor=cursor)

    @current_root_application.post('/management/assistant/operations-jobs')
    def operations_jobs(payload: dict):
        from fastapi import HTTPException
        from tools.management.common.operations_history import read_operations_job_history_page, OPERATIONS_HISTORY_STATUS_LABELS
        from tools.management.common.management_client import execute_remote_management_command
        query = payload.get('query', '')
        if not isinstance(query, str):
            raise HTTPException(422, '검색어를 확인하세요.')
        rows, summary, page = read_operations_job_history_page(query, payload.get('status', '전체'), payload.get('page'),
            payload.get('direction', 'first'), command=execute_remote_management_command)
        return dict(rows=rows, summary=summary, page=page, statuses=OPERATIONS_HISTORY_STATUS_LABELS)

    @current_root_application.get('/management/assistant/tools')
    def assistant_tools():
        from tools.management.domains.hermes_agent.workflow_catalog import WORKFLOW_GENERATOR_COMMANDS
        generator_pages = {name: name for name in WORKFLOW_GENERATOR_COMMANDS}
        generator_pages.update({name + '-generator': name for name in WORKFLOW_GENERATOR_COMMANDS})
        from tools.management.common.management_catalog import CATEGORY_LABEL_VALUES, resolve_management_page_path, load_manager_page_records
        return [
            {key: record[key] for key in ('id', 'label', 'category', 'description')}
            | {'workflow_generator': generator_pages.get(record['id']), 'review_path': resolve_management_page_path(record), 'category_label': CATEGORY_LABEL_VALUES.get(record['category'], record['category'])}
            for record in load_manager_page_records(current_source_path)
            if record['id'] != 'hermes-agent'
        ]

    from starlette.responses import FileResponse
    assistant_root = Path(__file__).resolve().parents[3] / 'gui'

    @current_root_application.get('/management/frame/prompt-translation')
    @current_root_application.get('/management/frame/prompt-translation/')
    @current_root_application.get('/management/frame/model-management')
    @current_root_application.get('/management/frame/model-management/')
    @current_root_application.get('/management/frame/mock-animate-validation')
    @current_root_application.get('/management/frame/mock-animate-validation/')
    @current_root_application.get('/management/frame/mock-dwpose-validation')
    @current_root_application.get('/management/frame/mock-dwpose-validation/')
    @current_root_application.get('/management/frame/mock-progress-validation')
    @current_root_application.get('/management/frame/mock-progress-validation/')
    @current_root_application.get('/management/assistant/models/')
    @current_root_application.get('/management/frame/writer-agent')
    @current_root_application.get('/management/frame/writer-agent/')
    @current_root_application.get('/management/frame/wan22-animate2-generator')
    @current_root_application.get('/management/frame/wan22-animate2-generator/')
    @current_root_application.get('/management/frame/dwpose-generator')
    @current_root_application.get('/management/frame/dwpose-generator/')
    @current_root_application.get('/management/frame/sfx-dasheng-audiogen')
    @current_root_application.get('/management/frame/sfx-dasheng-audiogen/')
    @current_root_application.get('/management/frame/music-heartmula')
    @current_root_application.get('/management/frame/music-heartmula/')
    @current_root_application.get('/management/frame/flux-expression-generator')
    @current_root_application.get('/management/frame/flux-expression-generator/')
    @current_root_application.get('/management/frame/flux-seamless-generator')
    @current_root_application.get('/management/frame/flux-seamless-generator/')
    @current_root_application.get('/management/frame/flux-character-generator')
    @current_root_application.get('/management/frame/flux-character-generator/')
    @current_root_application.get('/management/frame/flux-building-generator')
    @current_root_application.get('/management/frame/flux-building-generator/')
    @current_root_application.get('/management/frame/flux-mannequin-generator')
    @current_root_application.get('/management/frame/flux-mannequin-generator/')
    @current_root_application.get('/management/frame/flux-billboard-generator')
    @current_root_application.get('/management/frame/flux-billboard-generator/')
    @current_root_application.get('/management/frame/flux-prop-generator')
    @current_root_application.get('/management/frame/flux-prop-generator/')
    @current_root_application.get('/management/frame/flux-vegetation-generator')
    @current_root_application.get('/management/frame/flux-vegetation-generator/')
    @current_root_application.get('/management/frame/flux-image-generator')
    @current_root_application.get('/management/frame/flux-image-generator/')
    @current_root_application.get('/management/assistant/flux-image/')
    @current_root_application.get('/management/assistant/heartmula/')
    @current_root_application.get('/management/assistant/sound-effect/')
    @current_root_application.get('/management/frame/wan22-vace-generator')
    @current_root_application.get('/management/frame/wan22-vace-generator/')
    @current_root_application.get('/management/frame/wan22-fun-control-generator')
    @current_root_application.get('/management/frame/wan22-fun-control-generator/')
    @current_root_application.get('/management/frame/building-editor')
    @current_root_application.get('/management/frame/building-editor/')
    @current_root_application.get('/management/frame/effect-editor')
    @current_root_application.get('/management/frame/effect-editor/')
    @current_root_application.get('/management/frame/sprite-sheet-editor')
    @current_root_application.get('/management/frame/sprite-sheet-editor/')
    @current_root_application.get('/management/assistant/sprite-sheets/')
    @current_root_application.get('/management/assistant/effects/')
    @current_root_application.get('/management/frame/asset-editor')
    @current_root_application.get('/management/frame/asset-editor/')
    @current_root_application.get('/management/assistant/billboards/')
    @current_root_application.get('/management/assistant/buildings/')
    @current_root_application.get('/management/assistant/field-map/')
    @current_root_application.get('/management/assistant/town-map/')
    @current_root_application.get('/management/assistant/battlefield/')
    @current_root_application.get('/management/assistant/fun-control/')
    @current_root_application.get('/management/assistant/qwen-archive/')
    @current_root_application.get('/management/frame/kimodo-generator')
    @current_root_application.get('/management/frame/kimodo-generator/')
    @current_root_application.get('/management/assistant/kimodo/')
    @current_root_application.get('/management/assistant/vace/')
    @current_root_application.get('/management/assistant/dwpose/')
    @current_root_application.get('/management/assistant/translation/')
    @current_root_application.get('/management/frame/world-map')
    @current_root_application.get('/management/frame/world-map/')
    @current_root_application.get('/management/frame/hermes-agent')
    @current_root_application.get('/management/frame/hermes-agent/')
    @current_root_application.get('/management/assistant/')
    def assistant_page():
        return FileResponse(assistant_root / 'index.html', headers={'Cache-Control': 'no-cache'})

    @current_root_application.get('/management/assistant/changelog/{generator}')
    def assistant_changelog(generator: str, page: int = 0):
        from tools.management.common.generator_changelog import GENERATOR_CHANGELOG_PATHS, read_changelog_page
        if generator not in GENERATOR_CHANGELOG_PATHS:
            return Response(status_code=404)
        return read_changelog_page(generator, page)

    @current_root_application.get('/management/assistant/model-downloads/{service}')
    def model_download_progress(service: str):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.model_download_progress import MODEL_DOWNLOAD_PREFIXES, format_model_download_status
        if service not in MODEL_DOWNLOAD_PREFIXES:
            return Response(status_code=404)
        records = execute_remote_management_command('model-downloads', 'download-status', {})['records']
        lines = format_model_download_status(records, service).splitlines()
        return {'lines': [line.removeprefix('- ') for line in lines]}

    @current_root_application.get('/management/assistant/model-readiness/{service}')
    def model_readiness(service: str):
        from tools.management.common.management_client import execute_remote_management_command
        from tools.management.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
        from tools.management.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        from tools.management.common.model_preparation_controls import execute_model_preparation_command, execute_wan13_model_command
        if service == 'wan21-fun-1.3b':
            status = execute_wan13_model_command('model-status', {}, execute_remote_management_command)
            request = {'service':'wan22-fun-control', 'command':'prepare', 'payload':{'action':'prepare', 'model_profile':'wan21-1.3b'}}
        elif service in {identifier for _, identifier in MODEL_PREPARATION_SERVICES}:
            status = execute_model_preparation_command(service, 'model-status', {}, execute_remote_management_command)
            command = inspect_registered_model_operation(service, MANAGEMENT_SERVICE_COMMANDS.get(service, ()), 'prepare')
            request = {'service':service, 'command':command, 'payload':{'action':'prepare'} if command == 'prepare' else {}} if command else None
        else:
            return Response(status_code=404)
        return {**status, 'prepare_request':request}

    @current_root_application.get('/management/assistant/model-services')
    def model_services():
        from tools.management.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        return [
            {'label': label, 'id': service}
            for label, service in sorted((*MODEL_PREPARATION_SERVICES, ('Wan 2.1 Fun Control 1.3B', 'wan21-fun-1.3b')), key=lambda item: item[0].casefold())
        ]

    @current_root_application.get('/management/assistant/{asset}')
    def assistant_asset(asset: str):
        files = {'app.js': 'dist/app.js', 'app.js.LEGAL.txt': 'dist/app.js.LEGAL.txt', 'style.css': 'style.css'}
        if asset not in files:
            return Response(status_code=404)
        return FileResponse(assistant_root / files[asset], headers={'Cache-Control': 'no-cache'})

    current_root_application.mount('/', dispatch_management_request)
    return current_root_application
