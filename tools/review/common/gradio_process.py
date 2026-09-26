"""관리 서버 수명에 연결된 로컬 Gradio UI 프로세스."""
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[3]
GRADIO_PROCESS_LOCK=threading.Lock()
GRADIO_SERVER_PROCESSES={}

def ensure_gradio_application(review_server_port, application_name, application_source_path=None):
    with GRADIO_PROCESS_LOCK:
        application_definitions={
            'management-menu':('management_menu_app.py',100,'/management/'),
            'momask':('momask_app.py',101,'/management/frame/momask-generator/'),
            'character-animation':('character_animation_app.py',102,'/management/frame/character-animation/'),
        }
        if application_name not in application_definitions:raise ValueError('지원하지 않는 Gradio 관리 화면')
        application_filename,port_offset_value,application_root_path=application_definitions[application_name]
        gradio_server_port=review_server_port+port_offset_value
        gradio_page_url=f'http://127.0.0.1:{gradio_server_port}{application_root_path}?__theme=dark'
        gradio_config_url=f'http://127.0.0.1:{gradio_server_port}/config'
        process_key_value=(review_server_port,application_name)
        process_record_value=GRADIO_SERVER_PROCESSES.get(process_key_value)
        if process_record_value is not None and process_record_value.poll() is None:
            return gradio_page_url
        try:
            with urllib.request.urlopen(gradio_config_url,timeout=.3) as response_value:
                if response_value.status==200:return gradio_page_url
        except OSError:
            pass
        log_directory_path=WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current'
        log_directory_path.mkdir(parents=True,exist_ok=True)
        with (log_directory_path/'gradio.log').open('a') as log_output_stream:
            application_command_values=[str(WORKFLOW_ROOT_DIRECTORY/'.venv-management/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio'/application_filename),'--port',str(gradio_server_port),'--review-port',str(review_server_port),'--owner-pid',str(os.getpid()),'--root-path',application_root_path]
            if application_source_path is not None:application_command_values.extend(['--source-file',str(application_source_path)])
            process_record_value=subprocess.Popen(application_command_values,cwd=WORKFLOW_ROOT_DIRECTORY,stdout=log_output_stream,stderr=subprocess.STDOUT,env={**os.environ,'GRADIO_ANALYTICS_ENABLED':'False'})
        GRADIO_SERVER_PROCESSES[process_key_value]=process_record_value
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
