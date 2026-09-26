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

def ensure_gradio_server(review_server_port):
    with GRADIO_PROCESS_LOCK:
        gradio_server_port=review_server_port+100
        process_record_value=GRADIO_SERVER_PROCESSES.get(review_server_port)
        if process_record_value is not None and process_record_value.poll() is None:
            return f'http://127.0.0.1:{gradio_server_port}/?__theme=dark'
        log_directory_path=WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current'
        log_directory_path.mkdir(parents=True,exist_ok=True)
        with (log_directory_path/'gradio.log').open('a') as log_output_stream:
            process_record_value=subprocess.Popen([str(WORKFLOW_ROOT_DIRECTORY/'.venv-management/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/gradio/momask_app.py'),'--port',str(gradio_server_port),'--review-port',str(review_server_port),'--owner-pid',str(os.getpid())],cwd=WORKFLOW_ROOT_DIRECTORY,stdout=log_output_stream,stderr=subprocess.STDOUT,env={**os.environ,'GRADIO_ANALYTICS_ENABLED':'False'})
        GRADIO_SERVER_PROCESSES[review_server_port]=process_record_value
        for attempt_index_value in range(100):
            if process_record_value.poll() is not None:raise ValueError('Gradio 시작 실패: .tmp/manager-current/gradio.log를 확인하세요.')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{gradio_server_port}/config',timeout=.3) as response_value:
                    if response_value.status==200:return f'http://127.0.0.1:{gradio_server_port}/?__theme=dark'
            except OSError:time.sleep(.1)
        process_record_value.terminate()
        process_record_value.wait(timeout=5)
        raise ValueError('Gradio 시작 제한 시간 초과')
