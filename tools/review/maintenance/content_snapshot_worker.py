"""독립 프로세스에서 공용 게이트웨이의 파일 스냅샷 명령을 주기 실행한다."""
import argparse
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import signal
import sys
from threading import Event, Thread
import time

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from tools.review.common.management_gateway import execute_management_command

CONTENT_SNAPSHOT_INTERVAL_SECONDS = 60
CONTENT_SNAPSHOT_HEARTBEAT_SECONDS = 5
CONTENT_SNAPSHOT_LOG_DIRECTORY = Path(__file__).resolve().parents[3]/'.tmp/content-snapshot-worker'


def run_content_snapshot_worker(current_server_address,current_interval_seconds,current_run_once=False):
    if current_interval_seconds<5:
        raise ValueError('스냅샷 주기는 5초 이상이어야 합니다.')
    CONTENT_SNAPSHOT_LOG_DIRECTORY.mkdir(parents=True,exist_ok=True)
    current_worker_logger=logging.getLogger('content-snapshot-worker')
    current_worker_logger.setLevel(logging.INFO)
    current_log_formatter=logging.Formatter('%(asctime)s/content-snapshot/%(message)s')
    for current_log_handler in (logging.StreamHandler(),TimedRotatingFileHandler(
            CONTENT_SNAPSHOT_LOG_DIRECTORY/'worker.log',when='midnight',backupCount=7,encoding='utf-8')):
        current_log_handler.setFormatter(current_log_formatter)
        current_worker_logger.addHandler(current_log_handler)
    current_stop_event=Event()
    current_heartbeat_stop=Event()
    current_worker_state={'phase':'starting','last_result':None,'last_error':None}
    def request_snapshot_worker_stop(current_signal_number,current_stack_frame):
        current_stop_event.set()
    for current_signal_number in (signal.SIGINT,signal.SIGTERM):
        signal.signal(current_signal_number,request_snapshot_worker_stop)
    def emit_snapshot_worker_heartbeat():
        while not current_heartbeat_stop.wait(CONTENT_SNAPSHOT_HEARTBEAT_SECONDS):
            current_worker_logger.info('heartbeat %s',current_worker_state)
    current_heartbeat_thread=Thread(target=emit_snapshot_worker_heartbeat,daemon=True)
    current_heartbeat_thread.start()
    current_failure_count=0
    try:
        while not current_stop_event.is_set():
            current_worker_state['phase']='snapshot'
            current_worker_logger.info('start 파일 스냅샷 요청')
            try:
                current_result_record=execute_management_command('map-assets','database-snapshot',{},current_server_address)
                current_worker_state.update(last_result=current_result_record,last_error=None,phase='waiting')
                current_worker_logger.info('complete %s',current_result_record)
                current_failure_count=0
            except Exception as current_worker_error:
                current_failure_count+=1
                current_worker_state.update(last_error=str(current_worker_error),phase='retry-wait')
                current_worker_logger.exception('failure 스냅샷 실패; 기존 DB와 마지막 파일 세대 보존')
                if current_run_once:
                    raise
            if current_run_once:
                return current_worker_state['last_result']
            current_retry_delay=min(current_interval_seconds*max(1,2**min(current_failure_count,4)),900)
            current_stop_event.wait(current_retry_delay)
    finally:
        current_heartbeat_stop.set()
        current_heartbeat_thread.join()
        current_worker_logger.info('finish 종료')


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--server',required=True)
    current_argument_parser.add_argument('--interval',type=int,default=CONTENT_SNAPSHOT_INTERVAL_SECONDS)
    current_argument_parser.add_argument('--once',action='store_true')
    current_command_options=current_argument_parser.parse_args()
    run_content_snapshot_worker(current_command_options.server,current_command_options.interval,current_command_options.once)
