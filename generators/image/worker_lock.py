"""GPU 生成 작업 잠금 대기와 5초 간격 상태 기록."""
import fcntl
import time
from datetime import datetime


def acquire_worker_lock(current_lock_handle, current_wait_stage):
    while True:
        try:
            fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return
        except BlockingIOError:
            print(f'{datetime.now().isoformat()}/image-worker/stage={current_wait_stage} 다른 작업 완료 대기 중',flush=True)
            time.sleep(5)
