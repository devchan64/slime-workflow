"""추가 TCP 포트 없이 관리 화면과 기존 HTTP 계약을 같은 서버에서 제공한다."""
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
import importlib
import io
import os
from types import SimpleNamespace
import logging

from fastapi import FastAPI
from starlette.responses import Response, RedirectResponse
import gradio as gr

QWEN_INTERFACE_OPTIONS = {
    'billboard-generator': {'qwen21_mode_enabled': True, 'prop_mode_enabled': True, 'billboard_guide_enabled': True},
    'pose-transfer-generator': {'qwen21_mode_enabled': True, 'pose_transfer_enabled': True},
    'outfit-transfer-generator': {'qwen21_mode_enabled': True, 'outfit_transfer_enabled': True},
    'vegetation-generator': {'qwen21_mode_enabled': True, 'vegetation_mode_enabled': True},
    'prop-generator': {'qwen21_mode_enabled': True, 'prop_mode_enabled': True},
    'building-generator': {'qwen21_mode_enabled': True, 'building_mode_enabled': True},
    'qwen-21-generator': {'qwen21_mode_enabled': True},
    'qwen-21-circular-generator': {'qwen21_mode_enabled': True, 'circular_mode_enabled': True},
    'expression-generator': {'expression_mode_enabled': True},
}
MANAGEMENT_INTERFACE_BUILDERS = {
    'kimodo-generator': ('kimodo_app', 'build_kimodo_interface', 'url'),
    'wan22-vace-generator': ('wan_vace_app', 'build_vace_interface', 'url'),
    'wan22-animate-generator': ('wan_animate_app', 'build_animate_interface', 'url'),
    'hy-motion-generator': ('hy_motion_app', 'build_hymotion_interface', 'url'),
    'animation-separation': ('animation_separation_app', 'build_separation_interface', 'url'),
    'wan22-fun-control-generator': ('wan_fun_app', 'build_fun_interface', 'url'),
    'map-review': ('map_review_app', 'build_map_review_interface', 'port'),
    'character-review': ('map_review_app', 'build_map_review_interface', 'character'),
    'effect-editor': ('effect_editor_app', 'build_effect_editor_interface', 'port'),
    'asset-editor': ('asset_editor_app', 'build_asset_editor_interface', 'port'),
    'world-map': ('world_map_app', 'build_world_review_interface', 'port'),
    'writer-agent': ('writer_agent_app', 'build_writer_agent_interface', 'port'),
    'anny-attributes': ('anny_attributes_app', 'build_anny_attribute_interface', 'port'),
    'anny-landmarks': ('anny_landmarks_app', 'build_landmark_interface', 'none'),
    'sprite-editor-v2': ('sprite_editor_v2_app', 'build_sprite_v2_interface', 'none'),
}
LEGACY_MANAGEMENT_PATHS = {'/hy-motion-generator/': 'hy-motion-generator', '/animation-separation/': 'animation-separation', '/image-generation-21/': 'qwen-21-generator', '/image-generation-21-circular/': 'qwen-21-circular-generator', '/pose-transfer/': 'pose-transfer-generator', '/outfit-transfer/': 'outfit-transfer-generator', '/vegetation-generator/': 'vegetation-generator', '/prop-generator/': 'prop-generator', '/billboard-generator/': 'billboard-generator', '/building-generator/': 'building-generator', '/anny-attributes/': 'anny-attributes', '/writer-agent/': 'writer-agent', '/character-animation/sprite-editor-v2': 'sprite-editor-v2'}
MUSIC_INTERFACE_SERVICES = ('music-heartmula', 'sfx-dasheng-audiogen')


def build_management_blocks(current_tool_name, current_review_port, current_source_path):
    from tools.review.ui.gradio.management_menu_app import compose_management_interface, build_management_menu_interface, load_manager_page_records
    current_server_address = f'http://127.0.0.1:{current_review_port}'
    from tools.review.serve import REVIEW_LIVE_RELOAD_SCRIPT
    current_mount_options = {'allowed_paths': [], 'ssr_mode': False, 'head': REVIEW_LIVE_RELOAD_SCRIPT.decode()}
    if current_tool_name == 'management':
        return build_management_menu_interface(load_manager_page_records(current_source_path), current_review_port)[0], current_mount_options
    if current_tool_name in QWEN_INTERFACE_OPTIONS:
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        current_interface_blocks = build_qwen_2511_interface(current_server_address, **QWEN_INTERFACE_OPTIONS[current_tool_name])
    elif current_tool_name in MUSIC_INTERFACE_SERVICES:
        from tools.review.ui.gradio.music_app import build_music_interface
        current_interface_blocks = build_music_interface(current_tool_name, current_server_address)
    elif current_tool_name == 'static-review':
        from tools.review.ui.gradio.static_review_app import load_static_review_paths, build_static_review_interface, create_static_review_loader
        current_static_paths = load_static_review_paths(current_source_path)
        current_catalog_records = load_manager_page_records(current_source_path, current_animation_catalog=True)
        current_anchor_paths = [current_record['path'].split('?')[0] for current_record in current_catalog_records if current_record.get('anchorEditor') and current_record.get('uiMode') == 'gradio-static']
        current_interface_blocks = build_static_review_interface(current_static_paths, current_anchor_paths, [current_record for current_record in current_catalog_records if current_record['category'] == 'animation'])
        current_mount_options['js'] = create_static_review_loader(current_review_port, current_static_paths, current_anchor_paths)
    else:
        current_module_name, current_builder_name, current_argument_kind = MANAGEMENT_INTERFACE_BUILDERS[current_tool_name]
        current_module_value = importlib.import_module('tools.review.ui.gradio.' + current_module_name)
        current_builder_value = getattr(current_module_value, current_builder_name)
        if current_argument_kind == 'none':
            current_interface_blocks = current_builder_value()
        elif current_argument_kind == 'character':
            current_interface_blocks = current_builder_value(current_review_port, character_review_enabled=True)
        else:
            current_interface_blocks = current_builder_value(current_server_address if current_argument_kind == 'url' else current_review_port)
        if current_tool_name == 'anny-attributes':
            current_mount_options['js'] = current_module_value.create_anny_attribute_loader(current_review_port)
        elif current_tool_name == 'anny-landmarks':
            current_mount_options['js'] = current_module_value.create_landmark_loader()
        elif current_tool_name == 'sprite-editor-v2':
            import re
            current_markup_text = current_module_value.resolve_review_ui_asset('sprite-editor-v2.html').read_text()
            current_mount_options['css'] = re.search(r'<style>(.*?)</style>', current_markup_text, re.S).group(1)
            current_mount_options['js'] = current_module_value.create_sprite_v2_loader(current_review_port)
        elif current_tool_name == 'asset-editor':
            from tools.review.common.map_tile_assets import load_registered_tiles
            current_mount_options['allowed_paths'] = [str(load_registered_tiles()[0] / 'assets/billboards')]
    return compose_management_interface(current_interface_blocks, current_review_port), current_mount_options


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
    current_supported_tools = {*QWEN_INTERFACE_OPTIONS, *MANAGEMENT_INTERFACE_BUILDERS, *MUSIC_INTERFACE_SERVICES, 'management', 'static-review'}

    async def dispatch_management_request(current_request_scope, current_receive_call, current_send_call):
        current_request_path = current_request_scope['path']
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
            current_redirect_value = RedirectResponse('/management/' + ('?' + current_query_text if current_query_text else ''))
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        elif current_request_path in current_static_routes or current_request_path == '/isloon-map-review/map-review.html':
            current_redirect_value = RedirectResponse('/management/?' + current_request_scope.get('query_string', b'').decode())
            return await current_redirect_value(current_request_scope, current_receive_call, current_send_call)
        if current_tool_name in current_supported_tools:
            async with current_mount_lock:
                if current_tool_name not in current_mounted_apps:
                    try:
                        current_interface_blocks, current_mount_options = build_management_blocks(current_tool_name, current_review_port, current_source_path)
                        current_tool_application = gr.mount_gradio_app(FastAPI(), current_interface_blocks.queue(), path=current_mount_path, root_path=current_mount_path, **current_mount_options)
                        await current_lifespan_stack.enter_async_context(current_tool_application.router.lifespan_context(current_tool_application))
                        current_mounted_apps[current_tool_name] = current_tool_application
                    except Exception:
                        logging.exception('관리 화면 초기화 실패: %s', current_tool_name)
                        current_failure_response = Response('관리 화면 초기화 실패. 서버 로그를 확인하세요.', status_code=503)
                        return await current_failure_response(current_request_scope, current_receive_call, current_send_call)
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

    current_root_application.mount('/', dispatch_management_request)
    return current_root_application
