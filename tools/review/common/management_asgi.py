"""추가 TCP 포트 없이 관리 화면과 기존 HTTP 계약을 같은 서버에서 제공한다."""
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
import importlib
import io
import os
from types import SimpleNamespace
from urllib.parse import parse_qs
import logging
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.responses import Response, RedirectResponse, JSONResponse

MANAGEMENT_INTERFACE_BUILDERS = {
    'operations-history': ('operations_history_app', 'build_operations_history_interface', 'none'),
    'hermes-direct': ('hermes_agent_app', 'build_hermes_direct_interface', 'none'),
    'mock-dwpose-validation': ('mock_progress_validation_app', 'build_mock_dwpose_interface', 'url'),
    'mock-animate-validation': ('mock_progress_validation_app', 'build_mock_animate_interface', 'url'),
    'kimodo-generator': ('kimodo_app', 'build_kimodo_interface', 'url'),
    'wan22-vace-generator': ('wan_vace_app', 'build_vace_interface', 'url'),
    'wan22-animate2-generator': ('wan_animate2_app', 'build_animate_interface', 'url'),
    'wan22-fun-control-generator': ('wan_fun_app', 'build_fun_interface', 'url'),
    'map-review': ('map_review_app', 'build_map_review_interface', 'port'),
    'effect-editor': ('effect_editor_app', 'build_effect_editor_interface', 'port'),
    'asset-editor': ('asset_editor_app', 'build_asset_editor_interface', 'port'),
    'building-editor': ('building_editor_panel', 'build_building_editor_interface', 'port'),
    'writer-agent': ('writer_agent_app', 'build_writer_agent_interface', 'port'),
    'sprite-sheet-editor': ('sprite_sheet_editor_app', 'build_sprite_sheet_editor_interface', 'port'),
}
LEGACY_MANAGEMENT_PATHS = {'/image-generation-21/': 'qwen-21-generator', '/image-generation-21-circular/': 'qwen-21-circular-generator', '/vegetation-generator/': 'vegetation-generator', '/prop-generator/': 'prop-generator', '/billboard-generator/': 'billboard-generator', '/building-generator/': 'building-generator', '/writer-agent/': 'writer-agent'}
GENERATOR_PAGE_PACKAGES = {'mannequin-generator': 'mannequin-generator', 'character-generator': 'character-generator', 'qwen-21-generator': 'qwen-21', 'qwen-21-circular-generator': 'qwen-21-circular', 'expression-generator': 'expression', 'vegetation-generator': 'vegetation-generator', 'prop-generator': 'prop-generator', 'billboard-generator': 'billboard-generator', 'building-generator': 'billboard-generator', 'writer-agent': 'writer_agent'}
GENERATOR_PAGE_PACKAGES['flux-expression-generator'] = 'flux-expression'
for current_flux_profile in ('flux-character','flux-building','flux-seamless'):
    GENERATOR_PAGE_PACKAGES[current_flux_profile+'-generator'] = current_flux_profile
def __getattr__(name):
    """이전 Qwen 옵션 조회자가 접근할 때만 해당 화면 모듈을 읽는다."""
    if name != 'QWEN_INTERFACE_OPTIONS':
        raise AttributeError(name)
    identifiers = (
        'mannequin-generator', 'character-generator', 'qwen-21-generator',
        'qwen-21-circular-generator', 'expression-generator', 'vegetation-generator',
        'prop-generator', 'billboard-generator', 'building-generator',
    )
    options = {
        identifier: importlib.import_module(
            f'generators.{GENERATOR_PAGE_PACKAGES[identifier]}.page.interface'
        ).GENERATOR_PAGE_OPTIONS
        for identifier in identifiers
    }
    globals()[name] = options
    return options


def build_management_blocks(current_tool_name, current_review_port, current_source_path):
    from tools.review.ui.gradio.management_menu_app import compose_management_interface, build_management_menu_interface, load_manager_page_records
    current_server_address = f'http://127.0.0.1:{current_review_port}'
    from tools.review.serve import REVIEW_LIVE_RELOAD_SCRIPT
    current_mount_options = {'allowed_paths': [], 'ssr_mode': False, 'head': REVIEW_LIVE_RELOAD_SCRIPT.decode(), 'css': '#management-sidebar.open{left:0!important;transform:none!important;transition:none!important}#management-gpu-floating{position:fixed;right:12px;bottom:12px;z-index:50;width:min(12rem,calc(100vw - 24px));max-height:45dvh;overflow-x:hidden;overflow-y:auto}#management-gpu-floating:has(>button.open){width:min(27rem,calc(100vw - 24px))}#management-gpu-floating .gr-accordion{min-width:0!important;overflow-x:hidden}#management-gpu-floating .gr-accordion>button{min-width:0;width:100%;white-space:normal;text-align:left}#management-gpu-floating .gr-accordion>button>span:first-child{min-width:0;overflow-wrap:anywhere}#management-gpu-floating .gr-accordion>button>span:last-child{flex-shrink:0;align-self:center;min-width:1.25rem;text-align:center}#management-gpu-floating [data-testid="markdown"]{overflow-wrap:anywhere}'}
    if current_tool_name == 'management':
        return build_management_menu_interface(load_manager_page_records(current_source_path), current_review_port)[0], current_mount_options
    if current_tool_name in GENERATOR_PAGE_PACKAGES:
        current_page_package = GENERATOR_PAGE_PACKAGES[current_tool_name]
        current_page_module = importlib.import_module(f'generators.{current_page_package}.page.interface')
        current_interface_blocks = current_page_module.build_generator_page(current_server_address, current_review_port)
    elif current_tool_name == 'static-review':
        from tools.review.ui.gradio.static_review_app import load_static_review_paths, build_static_review_interface, create_static_review_loader
        current_static_paths = load_static_review_paths(current_source_path)
        current_catalog_records = load_manager_page_records(current_source_path, current_animation_catalog=True)
        current_anchor_paths = [current_record['path'].split('?')[0] for current_record in current_catalog_records if current_record.get('anchorEditor') and current_record.get('uiMode') == 'gradio-static']
        current_interface_blocks = build_static_review_interface(current_static_paths, current_anchor_paths, [current_record for current_record in current_catalog_records if current_record.get('registeredAnimation')])
        current_mount_options['js'] = create_static_review_loader(current_review_port, current_static_paths, current_anchor_paths)
    else:
        current_module_name, current_builder_name, current_argument_kind = MANAGEMENT_INTERFACE_BUILDERS[current_tool_name]
        current_module_value = importlib.import_module('tools.review.ui.gradio.' + current_module_name)
        current_builder_value = getattr(current_module_value, current_builder_name)
        if current_argument_kind == 'none':
            current_interface_blocks = current_builder_value()
        else:
            current_interface_blocks = current_builder_value(current_server_address if current_argument_kind == 'url' else current_review_port)
        if current_tool_name in ('asset-editor', 'building-editor'):
            from tools.review.common.map_tile_assets import load_registered_tiles
            current_asset_directory = 'buildings' if current_tool_name == 'building-editor' else 'billboards'
            current_mount_options['allowed_paths'] = [str(load_registered_tiles()[0] / 'assets' / current_asset_directory)]
    return compose_management_interface(current_interface_blocks, current_review_port, current_source_path), current_mount_options


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


from starlette.requests import ClientDisconnect
from uvicorn.protocols.utils import ClientDisconnected


async def bridge_gradio_heartbeat(current_application, current_scope, current_receive, current_send):
    """Gradio의 heartbeat 요청과 종료 처리를 동일 서버의 WebSocket으로 전달한다."""
    current_headers = dict(current_scope.get('headers', []))
    current_origin = urlsplit(current_headers.get(b'origin', b'').decode('latin1'))
    if current_origin.scheme not in ('http', 'https') or current_origin.netloc.lower() != current_headers.get(b'host', b'').decode('latin1').lower():
        await current_send({'type': 'websocket.close', 'code': 1008})
        return
    if (await current_receive())['type'] != 'websocket.connect':
        return
    current_http_scope = dict(current_scope, type='http', method='GET', http_version='1.1', scheme='https' if current_scope['scheme'] == 'wss' else 'http')
    current_http_scope['path'] = current_scope['path'].replace('/gradio_api/heartbeat-ws/', '/gradio_api/heartbeat/', 1)
    current_http_scope['raw_path'] = current_http_scope['path'].encode()
    current_disconnected = asyncio.Event()
    current_first_request = True
    current_accepted = False

    async def receive_heartbeat_http():
        nonlocal current_first_request
        if current_first_request:
            current_first_request = False
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        await current_disconnected.wait()
        return {'type': 'http.disconnect'}

    async def send_heartbeat_http(current_message):
        nonlocal current_accepted
        if current_message['type'] == 'http.response.start':
            if current_message['status'] != 200:
                await current_send({'type': 'websocket.close', 'code': 1008})
                return
            await current_send({'type': 'websocket.accept'})
            current_accepted = True
        elif current_message['type'] == 'http.response.body' and current_accepted:
            if current_message.get('body'):
                await current_send({'type': 'websocket.send', 'bytes': current_message['body']})
            if not current_message.get('more_body', False):
                await current_send({'type': 'websocket.close', 'code': 1000})

    async def observe_heartbeat_disconnect():
        while True:
            current_message = await current_receive()
            if current_message['type'] == 'websocket.disconnect':
                current_disconnected.set()
                return

    current_disconnect_task = asyncio.create_task(observe_heartbeat_disconnect())
    try:
        await current_application(current_http_scope, receive_heartbeat_http, send_heartbeat_http)
    except (ClientDisconnect, ClientDisconnected):
        current_disconnected.set()
    finally:
        current_disconnected.set()
        current_disconnect_task.cancel()
        await asyncio.gather(current_disconnect_task, return_exceptions=True)


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
    current_mounted_apps = {}
    current_mount_lock = asyncio.Lock()
    current_lifespan_stack = AsyncExitStack()

    @asynccontextmanager
    async def manage_application_lifespan(current_application_value):
        async with current_lifespan_stack:
            yield

    current_root_application = FastAPI(lifespan=manage_application_lifespan)
    current_supported_tools = {*GENERATOR_PAGE_PACKAGES, *MANAGEMENT_INTERFACE_BUILDERS, 'management', 'static-review'}

    async def dispatch_management_request(current_request_scope, current_receive_call, current_send_call):
        current_request_path = current_request_scope['path']
        if current_request_scope['type'] == 'http' and current_request_scope.get('method') == 'GET' and current_request_path == '/management/gui-health':
            current_health_record = {'status': 'ok', 'role': 'management-gui', 'pid': os.getpid()}
            if os.environ.get('SLIME_MANAGEMENT_STACK_TOKEN'):
                current_health_record['launch_token'] = os.environ['SLIME_MANAGEMENT_STACK_TOKEN']
            return await JSONResponse(current_health_record, headers={'Cache-Control': 'no-store'})(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope['type'] == 'websocket':
            current_tool_name = current_request_path.split('/')[3] if current_request_path.startswith('/management/frame/') else 'management'
            current_application = current_mounted_apps.get(current_tool_name)
            current_path_parts = current_request_path.split('/gradio_api/heartbeat-ws/')
            if current_application is None or len(current_path_parts) != 2 or not current_path_parts[1] or '/' in current_path_parts[1]:
                return await current_send_call({'type': 'websocket.close', 'code': 1008})
            return await bridge_gradio_heartbeat(current_application, current_request_scope, current_receive_call, current_send_call)
        current_query_values = parse_qs(current_request_scope.get('query_string', b'').decode())
        if current_request_path.rstrip('/') == '/management/frame/character-review' or current_request_path.startswith('/management/frame/character-review/') or 'character-review' in current_query_values.get('tool', []):
            return await Response('캐릭터 표현 검수 페이지는 폐기되었습니다.', status_code=410)(current_request_scope, current_receive_call, current_send_call)
        if current_request_scope.get('method') == 'GET' and current_request_path.rstrip('/') == '/management':
            from tools.review.common.management_catalog import REACT_REVIEW_PATHS
            tool = current_query_values.get('tool', [''])[0]
            if tool in REACT_REVIEW_PATHS:
                from urllib.parse import urlencode
                query = urlencode({key: values for key, values in current_query_values.items() if key not in ('tool', 'category')}, doseq=True)
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
            from tools.review.common.sprite_review_redirect import resolve_sprite_review_redirect
            import json
            current_sprite_redirect=resolve_sprite_review_redirect(current_request_path,current_query_values,json.loads(current_source_path.read_text()).get('pages',[]))
            if current_sprite_redirect:
                return await RedirectResponse(current_sprite_redirect)(current_request_scope,current_receive_call,current_send_call)
        current_tool_name = None
        current_mount_path = '/management'
        if current_request_path in LEGACY_MANAGEMENT_PATHS:
            current_redirect_value = RedirectResponse('/management/frame/' + LEGACY_MANAGEMENT_PATHS[current_request_path] + '/?' + current_request_scope.get('query_string', b'').decode())
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        if current_request_path.startswith('/management/frame/'):
            current_tool_name = current_request_path.split('/')[3]
            current_mount_path = '/management/frame/' + current_tool_name
        elif current_request_path == '/management' or current_request_path.startswith(('/management/config', '/management/gradio_api/', '/management/assets/', '/management/theme', '/management/favicon')) or current_request_path == '/management/':
            current_tool_name = 'management'
        elif current_request_path == '/' and current_source_path.is_file():
            current_query_text = current_request_scope.get('query_string', b'').decode()
            current_redirect_value = RedirectResponse('/management/' + '?' + current_query_text if current_query_text else '/management/frame/hermes-agent/')
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        elif (current_request_path in current_static_routes and current_query_values.get('embedded') != ['gradio-static']) or current_request_path == '/isloon-map-review/map-review.html':
            current_redirect_value = RedirectResponse('/management/?' + current_request_scope.get('query_string', b'').decode())
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        if current_tool_name in current_supported_tools:
            async with current_mount_lock:
                if current_tool_name not in current_mounted_apps:
                    try:
                        current_interface_blocks, current_mount_options = build_management_blocks(current_tool_name, current_review_port, current_source_path)
                        import gradio as gr
                        current_tool_application = gr.mount_gradio_app(FastAPI(), current_interface_blocks.queue(), path=current_mount_path, root_path=current_mount_path, **current_mount_options)
                        await current_lifespan_stack.enter_async_context(current_tool_application.router.lifespan_context(current_tool_application))
                        current_mounted_apps[current_tool_name] = current_tool_application
                    except Exception:
                        logging.exception('관리 화면 초기화 실패: %s', current_tool_name)
                        current_failure_response = Response('관리 화면 초기화 실패. 서버 로그를 확인하세요.', status_code=503)
                        return await current_failure_response(current_request_scope, current_receive_call, current_send_call)
            current_is_document = current_request_scope.get('method') == 'GET' and current_request_path.rstrip('/') == current_mount_path
            if current_is_document:
                current_script_bytes = b'<script>'+Path(__file__).with_name('gradio_heartbeat_bridge.js').read_bytes()+b'</script>'
                current_start_message = None
                async def send_document_with_heartbeat_bridge(current_message):
                    nonlocal current_start_message
                    if current_message['type'] == 'http.response.start':
                        current_start_message = current_message
                        return
                    if current_message['type'] == 'http.response.body' and current_start_message is not None:
                        current_body_bytes = current_message.get('body', b'')
                        current_content_type = dict(current_start_message.get('headers', [])).get(b'content-type', b'')
                        if b'text/html' in current_content_type and b'<head>' in current_body_bytes:
                            current_body_bytes = current_body_bytes.replace(b'<head>', b'<head>'+current_script_bytes, 1)
                            current_start_message['headers'] = [(current_name, str(len(current_body_bytes)).encode() if current_name.lower() == b'content-length' else current_value) for current_name, current_value in current_start_message['headers']]
                        await current_send_call(current_start_message)
                        current_start_message = None
                        current_message = dict(current_message, body=current_body_bytes)
                    await current_send_call(current_message)
                return await current_mounted_apps[current_tool_name](current_request_scope, current_receive_call, send_document_with_heartbeat_bridge)
            return await current_mounted_apps[current_tool_name](current_request_scope, current_receive_call, current_send_call)
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
    mock_jobs = {}

    @current_root_application.post('/management/assistant/mock-jobs')
    async def start_mock_job():
        identifier = 'mock-' + uuid4().hex
        mock_jobs[identifier] = monotonic()
        return {'id': identifier}

    @current_root_application.get('/management/assistant/mock-jobs')
    async def read_mock_jobs():
        now = monotonic()
        rows = []
        for identifier, started in reversed(mock_jobs.items()):
            elapsed = now - started
            if elapsed < 5:
                state, message = 'queued', '모의 대기열'
            elif elapsed < 15:
                state, message = 'running', '모의 실행 · 1 / 2'
            else:
                state, message = 'completed', '모의 결과 표시 완료'
            rows.append({'id': identifier, 'status': state, 'message': message})
        return rows

    def require_flux_page(service):
        from fastapi import HTTPException
        if service not in ('flux-image', 'flux-prop', 'flux-vegetation', 'flux-billboard', 'flux-mannequin'):
            raise HTTPException(404, '등록되지 않은 생성기 화면입니다.')

    @current_root_application.get('/management/assistant/flux-defaults/{service}')
    def flux_page_defaults(service: str):
        from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        require_flux_page(service)
        label, description, width, height, minimum = FLUX_IMAGE_PROFILE_RECORDS[service]
        prompt = ''
        if service in ('flux-prop', 'flux-vegetation'):
            source = service.removeprefix('flux-') + '-qwen-prompt.txt'
            prompt = (Path(__file__).resolve().parents[3] / 'generators/image/config' / source).read_text().strip().replace('transparent background', 'plain background')
        guide = {}
        if service == 'flux-billboard':
            from tools.review.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT
            guide = dict(layouts=BILLBOARD_LAYOUT_PROFILES, subject=BILLBOARD_DEFAULT_SUBJECT)
        if service == 'flux-mannequin':
            presets = importlib.import_module('generators.mannequin-generator.page.interface').MANNEQUIN_PRESET_RECORDS
            guide = {'stages': [{'id': key, 'label': row[0]} for key, row in presets.items()]}
        return dict(**guide, label=label, description=description, width=width, height=height, prompt=prompt, minimum=minimum)

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
        from tools.review.domains.image.billboard_guide_prompt import compose_billboard_guide_prompt, load_billboard_guide_image
        layout = payload.get('layout')
        try:
            prompt = compose_billboard_guide_prompt(layout, payload.get('subject')).replace('transparent background', 'plain background')
            with load_billboard_guide_image(layout) as image, io.BytesIO() as output:
                image.save(output, format='PNG')
                return {'prompt': prompt, 'image': base64.b64encode(output.getvalue()).decode('ascii')}
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @current_root_application.get('/management/assistant/flux-image-input/{job}')
    def flux_image_saved_input(job: str, service: str = "flux-image"):
        require_flux_page(service)
        import base64
        import io
        import json
        from fastapi import HTTPException
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        from tools.review.domains.image.flux_input_restore import restore_flux_image_inputs

        if not validate_service_job_identifier(service, job):
            raise HTTPException(404, '생성 ID를 확인하세요.')
        root = FluxImageGenerationManager(service).job_storage_root
        directory = root / job
        path = directory / 'request.json'
        if directory.is_symlink() or path.is_symlink() or not path.is_file():
            raise HTTPException(404, '저장된 입력을 찾을 수 없습니다.')
        try:
            record = {'id': job, 'request': json.loads(path.read_text())}
            prompt, first, second, width, height, _, seed, tag, translation = restore_flux_image_inputs(record, service, root)
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
                                           translation_source_ko=translation), 'images': images}

    @current_root_application.post('/management/assistant/flux-image-preview')
    def flux_image_preview(payload: dict, service: str = "flux-image"):
        require_flux_page(service)
        from fastapi import HTTPException
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        if payload.get('action') != 'generate':
            raise HTTPException(422, '이미지 생성 입력을 확인하세요.')
        try:
            request = FluxImageGenerationManager(service).validate_generation_request(payload)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return {'prompt': request['prompt'], 'translation': request.get('translation_source_ko')}

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
            from tools.review.domains.music.generation import MusicGenerationManager
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

    @current_root_application.get('/management/assistant/dwpose-input/{job}')
    def dwpose_input(job: str):
        from generators.dwpose.contracts import DWPOSE_JOB_STORAGE
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
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
        from tools.review.common.management_catalog import REACT_REVIEW_PATHS
        from tools.review.common.source_history_catalog import SOURCE_HISTORY_AUDIO_SERVICES, SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_VIDEO_SERVICES
        from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        from tools.review.domains.hermes_agent.image_source_operations import IMAGE_SOURCE_SERVICES
        kinds = {
            **dict.fromkeys(SOURCE_HISTORY_AUDIO_SERVICES, 'audio'),
            **dict.fromkeys(SOURCE_HISTORY_VIDEO_SERVICES, 'video'),
            **dict.fromkeys((*FLUX_IMAGE_PROFILE_RECORDS, 'flux-expression'), 'flux'),
            **dict.fromkeys(IMAGE_SOURCE_SERVICES, 'image'),
        }
        return [
            {'service': service, 'command': 'hermes-audio-source-history' if service in SOURCE_HISTORY_AUDIO_SERVICES else 'hermes-generator-source-history'}
            | {'video_result': service in SOURCE_HISTORY_VIDEO_SERVICES, 'result_kind': kinds.get(service)}
            | ({'result_path': REACT_REVIEW_PATHS[service]} if service == 'prompt-translation' else {})
            for service in sorted(set(SOURCE_HISTORY_GENERATOR_SERVICES) | set(SOURCE_HISTORY_AUDIO_SERVICES))
        ]

    @current_root_application.get('/management/assistant/capabilities')
    def assistant_capabilities():
        from tools.review.common.management_client import execute_remote_management_command
        from tools.review.common.hermes_capability_table import format_capability_table
        catalog = execute_remote_management_command('hermes-agent', 'hermes-capabilities', {})
        rows, summary = format_capability_table(catalog)
        return {'rows': rows, 'summary': summary}

    @current_root_application.get('/management/assistant/tools')
    def assistant_tools():
        from tools.review.common.management_catalog import REACT_REVIEW_PATHS, load_manager_page_records
        return [
            {key: record[key] for key in ('id', 'label', 'category', 'description')}
            | {'review_path': REACT_REVIEW_PATHS.get(record['id'])}
            for record in load_manager_page_records(current_source_path)
            if record['id'] != 'hermes-agent'
        ]

    from starlette.responses import FileResponse
    assistant_root = Path(__file__).resolve().parents[1] / 'ui' / 'assistant'

    @current_root_application.get('/management/frame/prompt-translation')
    @current_root_application.get('/management/frame/prompt-translation/')
    @current_root_application.get('/management/frame/model-management')
    @current_root_application.get('/management/frame/model-management/')
    @current_root_application.get('/management/frame/mock-progress-validation')
    @current_root_application.get('/management/frame/mock-progress-validation/')
    @current_root_application.get('/management/assistant/models/')
    @current_root_application.get('/management/frame/dwpose-generator')
    @current_root_application.get('/management/frame/dwpose-generator/')
    @current_root_application.get('/management/frame/sfx-dasheng-audiogen')
    @current_root_application.get('/management/frame/sfx-dasheng-audiogen/')
    @current_root_application.get('/management/frame/music-heartmula')
    @current_root_application.get('/management/frame/music-heartmula/')
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
        from tools.review.common.generator_changelog import GENERATOR_CHANGELOG_PATHS, read_changelog_page
        if generator not in GENERATOR_CHANGELOG_PATHS:
            return Response(status_code=404)
        return read_changelog_page(generator, page)

    @current_root_application.get('/management/assistant/model-downloads/{service}')
    def model_download_progress(service: str):
        from tools.review.common.management_client import execute_remote_management_command
        from tools.review.common.model_download_progress import MODEL_DOWNLOAD_PREFIXES, format_model_download_status
        if service not in MODEL_DOWNLOAD_PREFIXES:
            return Response(status_code=404)
        records = execute_remote_management_command('model-downloads', 'download-status', {})['records']
        lines = format_model_download_status(records, service).splitlines()
        return {'lines': [line.removeprefix('- ') for line in lines]}

    @current_root_application.get('/management/assistant/model-readiness/{service}')
    def model_readiness(service: str):
        from tools.review.common.management_client import execute_remote_management_command
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
        from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        from tools.review.common.model_preparation_controls import execute_model_preparation_command, execute_wan13_model_command
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
        from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
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
