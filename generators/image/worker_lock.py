"""공용 대기열 작업은 공유 잠금, 직접 실행은 배타 잠금으로 보호한다."""
import fcntl
import json
import os
from pathlib import Path
import time
from datetime import datetime


def has_queue_reservation():
    reservation_file_value = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    if not reservation_file_value:
        return False
    reservation_file_path = Path(reservation_file_value)
    expected_directory_path = Path(__file__).resolve().parents[2]/'.tmp/gpu-queue/active'
    try:
        if reservation_file_path.resolve().parent != expected_directory_path.resolve():
            return False
        reservation_record_value = json.loads(reservation_file_path.read_text())
        # 자식 렌더러도 예약 소유 실행기의 프로세스 트리인지 확인한다.
        ancestor_process_id = os.getpid()
        while ancestor_process_id > 1:
            if ancestor_process_id == reservation_record_value['pid']:
                return True
            ancestor_process_id = int(Path(f'/proc/{ancestor_process_id}/stat').read_text().rsplit(') ',1)[1].split()[1])
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return False


def acquire_worker_lock(current_lock_handle, current_wait_stage):
    selected_lock_mode = fcntl.LOCK_SH if current_wait_stage == 'waiting-gpu' and has_queue_reservation() else fcntl.LOCK_EX
    while True:
        try:
            fcntl.flock(current_lock_handle,selected_lock_mode|fcntl.LOCK_NB)
            return
        except BlockingIOError:
            print(f'{datetime.now().isoformat()}/image-worker/stage={current_wait_stage} 다른 작업 완료 대기 중',flush=True)
            time.sleep(5)
