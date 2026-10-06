"""관리 서버 수명에 연결된 로컬 Gradio UI 프로세스."""
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import urllib.request
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, resolve_management_environment

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[3]
GRADIO_PROCESS_LOCK=threading.Lock()
GRADIO_SERVER_PROCESSES={}
GRADIO_SERVER_SOURCE_FINGERPRINTS={}
GRADIO_UI_SOURCE_SUFFIXES=('.css','.html','.js','.py')


def create_gradio_process_marker_path(review_server_port,application_name):
    marker_directory_path=WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current'
    return marker_directory_path/f'gradio-{review_server_port}-{application_name}.json'


def write_gradio_process_marker(marker_path_value, process_identifier_value, source_fingerprint_value):
    marker_path_value.parent.mkdir(parents=True,exist_ok=True)
    marker_path_value.write_text(json.dumps({'pid':process_identifier_value,'fingerprint':source_fingerprint_value}),encoding='utf-8')


def read_gradio_process_marker(marker_path_value):
    try:
        marker_record_value=json.loads(marker_path_value.read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):
        return None
    if not isinstance(marker_record_value,dict) or not isinstance(marker_record_value.get('pid'),int):
        return None
    return marker_record_value


def list_orphaned_gradio_processes(application_file_path,gradio_server_port):
    process_listing_value=subprocess.run(['ps','-eo','pid=,args='],capture_output=True,text=True,check=True).stdout.splitlines()
    application_path_text=str(application_file_path)
    port_argument_text=f'--port {gradio_server_port}'
    process_identifier_values=[]
    for process_line_text in process_listing_value:
        process_parts_value=process_line_text.strip().split(maxsplit=1)
        if len(process_parts_value)!=2 or application_path_text not in process_parts_value[1] or port_argument_text not in process_parts_value[1]:
            continue
        process_identifier_values.append(int(process_parts_value[0]))
    return process_identifier_values


def stop_orphaned_gradio_processes(application_file_path,gradio_server_port,marker_path_value):
    process_identifier_values=list_orphaned_gradio_processes(application_file_path,gradio_server_port)
    if not process_identifier_values:
        raise ValueError(f'Gradio 포트 {gradio_server_port}를 사용하는 기존 프로세스를 확인할 수 없습니다.')
    for process_identifier_value in process_identifier_values:
        if process_identifier_value!=os.getpid():
            os.kill(process_identifier_value,signal.SIGTERM)
    for attempt_index_value in range(50):
        if not list_orphaned_gradio_processes(application_file_path,gradio_server_port):
            marker_path_value.unlink(missing_ok=True)
            return
        time.sleep(.1)
    raise ValueError(f'기존 Gradio 프로세스를 종료하지 못했습니다: 포트 {gradio_server_port}')

def create_gradio_source_fingerprint(application_source_path,application_file_path):
    gradio_source_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio'
    common_source_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/common'
    shared_ui_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/shared'
    tracked_source_paths={application_file_path,application_source_path}
    if application_file_path.name=='anny_attributes_app.py':
        tracked_source_paths.add(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/anny/anny-attributes.html')
    if application_file_path.name=='seamless_tile_app.py':
        image_domain_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/domains/image'
        tracked_source_paths.update(image_domain_directory/current_file_name for current_file_name in ('seamless_pattern.py','seamless_generation.py','seamless_directional.py'))
    if application_file_path.name=='animation_separation_app.py':
        tracked_source_paths.add(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/character_animation/separation-preview.html')
        tracked_source_paths.add(WORKFLOW_ROOT_DIRECTORY/'generators/image/config/animation_separation.yaml')
    if application_file_path.name=='sprite_editor_v2_app.py':
        tracked_source_paths.update(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/character_animation'/current_file_name for current_file_name in ('sprite-editor-v2.html','sprite-editor-v2.js'))
    if application_file_path.name=='sprite_editor_app.py':
        sprite_editor_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/character_animation'
        tracked_source_paths.update(sprite_editor_directory/current_file_name for current_file_name in ('sprite-editor.html','sprite-editor.js'))
    tracked_source_paths.update(common_source_directory.glob('gradio_*.py'))
    tracked_source_paths.update(common_source_directory/current_file_name for current_file_name in ('management_client.py','management_transport.py','management_environment.py'))
    for source_directory_path in (gradio_source_directory,shared_ui_directory):
        tracked_source_paths.update(current_source_path for current_source_path in source_directory_path.iterdir() if current_source_path.suffix in GRADIO_UI_SOURCE_SUFFIXES)
    return tuple((str(current_source_path),current_source_path.stat().st_mtime_ns if current_source_path is not None and current_source_path.is_file() else None) for current_source_path in sorted(tracked_source_paths,key=lambda current_source_path:str(current_source_path))) + (('gateway-url',os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS)),('management-environment',str(resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH','.venv-management'))))

def ensure_gradio_application(review_server_port, application_name, application_source_path=None):
    with GRADIO_PROCESS_LOCK:
        application_definitions={
            'management-menu':('management_menu_app.py',100,'/management/'),
            'momask':('momask_app.py',101,'/management/frame/momask-generator/'),
            'character-animation':('character_animation_app.py',102,'/management/frame/character-animation/'),
            'qwen-2512':('qwen_2512_app.py',103,'/management/frame/image-generator/'),
            'qwen-21-circular':('qwen_circular_app.py',118,'/management/frame/qwen-21-circular-generator/'),
            'pose-transfer':('pose_transfer_app.py',119,'/management/frame/pose-transfer-generator/'),
            'outfit-transfer':('outfit_transfer_app.py',120,'/management/frame/outfit-transfer-generator/'),
            'qwen-21':('qwen_21_app.py',116,'/management/frame/qwen-21-generator/'),
            'seamless-tile':('seamless_tile_app.py',115,'/management/frame/seamless-tile-generator/'),
            'expression':('expression_app.py',114,'/management/frame/expression-generator/'),
            'qwen-2511':('qwen_2511_app.py',104,'/management/frame/three-reference-generator/'),
            'floor-tile':('floor_tile_app.py',113,'/management/frame/floor-tile-generator/'),
            'animation-separation':('animation_separation_app.py',117,'/management/frame/animation-separation/'),
            'sprite-editor-v2':('sprite_editor_v2_app.py',121,'/management/frame/sprite-editor-v2/'),
            'sprite-editor':('sprite_editor_app.py',106,'/management/frame/sprite-editor/'),
            'map-review':('map_review_app.py',107,'/management/frame/map-review/'),
            'anny-attributes':('anny_attributes_app.py',108,'/management/frame/anny-attributes/'),
            'writer-agent':('writer_agent_app.py',109,'/management/frame/writer-agent/'),
            'static-review':('static_review_app.py',112,'/management/frame/static-review/'),
        }
        if application_name not in application_definitions:raise ValueError('지원하지 않는 Gradio 관리 화면')
        application_filename,port_offset_value,application_root_path=application_definitions[application_name]
        application_file_path=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio'/application_filename
        gradio_server_port=review_server_port+port_offset_value
        gradio_page_url=f'http://127.0.0.1:{gradio_server_port}{application_root_path}'
        gradio_config_url=f'http://127.0.0.1:{gradio_server_port}/config'
        process_key_value=(review_server_port,application_name)
        process_marker_path=create_gradio_process_marker_path(review_server_port,application_name)
        process_record_value=GRADIO_SERVER_PROCESSES.get(process_key_value)
        source_fingerprint_value=create_gradio_source_fingerprint(application_source_path,application_file_path)
        if process_record_value is not None and process_record_value.poll() is None:
            if GRADIO_SERVER_SOURCE_FINGERPRINTS.get(process_key_value)==source_fingerprint_value:
                return gradio_page_url
            process_record_value.terminate()
            process_record_value.wait(timeout=5)
            GRADIO_SERVER_PROCESSES.pop(process_key_value,None)
            GRADIO_SERVER_SOURCE_FINGERPRINTS.pop(process_key_value,None)
            process_marker_path.unlink(missing_ok=True)
        try:
            with urllib.request.urlopen(gradio_config_url,timeout=.3) as response_value:
                if response_value.status==200:
                    marker_record_value=read_gradio_process_marker(process_marker_path)
                    if marker_record_value is not None and marker_record_value.get('fingerprint')==json.loads(json.dumps(source_fingerprint_value)):
                        return gradio_page_url
                    stop_orphaned_gradio_processes(application_file_path,gradio_server_port,process_marker_path)
        except OSError:
            pass
        log_directory_path=WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current'
        log_directory_path.mkdir(parents=True,exist_ok=True)
        with (log_directory_path/'gradio.log').open('a') as log_output_stream:
            application_command_values=[str(resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH','.venv-management')/'bin/python'),str(application_file_path),'--port',str(gradio_server_port),'--review-port',str(review_server_port),'--owner-pid',str(os.getpid()),'--root-path',application_root_path]
            if application_source_path is not None:application_command_values.extend(['--source-file',str(application_source_path)])
            process_record_value=subprocess.Popen(application_command_values,cwd=WORKFLOW_ROOT_DIRECTORY,stdout=log_output_stream,stderr=subprocess.STDOUT,env={**os.environ,'GRADIO_ANALYTICS_ENABLED':'False'})
        GRADIO_SERVER_PROCESSES[process_key_value]=process_record_value
        GRADIO_SERVER_SOURCE_FINGERPRINTS[process_key_value]=source_fingerprint_value
        write_gradio_process_marker(process_marker_path,process_record_value.pid,source_fingerprint_value)
        for attempt_index_value in range(100):
            if process_record_value.poll() is not None:raise ValueError('Gradio 시작 실패: .tmp/manager-current/gradio.log를 확인하세요.')
            try:
                with urllib.request.urlopen(gradio_config_url,timeout=.3) as response_value:
                    if response_value.status==200:return gradio_page_url
            except OSError:time.sleep(.1)
        process_record_value.terminate()
        process_record_value.wait(timeout=5)
        raise ValueError('Gradio 시작 제한 시간 초과')

def ensure_gradio_server(review_server_port):
    return ensure_gradio_application(review_server_port,'momask')

def ensure_management_menu_server(review_server_port, manager_source_path):
    return ensure_gradio_application(review_server_port,'management-menu',manager_source_path)

def ensure_character_animation_server(review_server_port):
    return ensure_gradio_application(review_server_port,'character-animation')

def ensure_qwen_2512_server(review_server_port):
    return ensure_gradio_application(review_server_port,'qwen-2512')

def ensure_qwen_2511_server(review_server_port):
    return ensure_gradio_application(review_server_port,'qwen-2511')

def ensure_sprite_editor_server(review_server_port):
    return ensure_gradio_application(review_server_port,'sprite-editor')

def ensure_map_review_server(review_server_port):
    return ensure_gradio_application(review_server_port,'map-review')

def ensure_anny_attributes_server(review_server_port):
    return ensure_gradio_application(review_server_port,'anny-attributes')

def ensure_writer_agent_server(review_server_port):
    return ensure_gradio_application(review_server_port,'writer-agent')


def ensure_static_review_server(review_server_port, manager_source_path):
    return ensure_gradio_application(review_server_port,'static-review',manager_source_path)

def ensure_floor_tile_server(review_server_port):
    return ensure_gradio_application(review_server_port,'floor-tile')
