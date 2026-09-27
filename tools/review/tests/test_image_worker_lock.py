"""대기열 허가와 직접 실행의 잠금 분리 검증."""
import fcntl
import tempfile
import unittest
from unittest.mock import patch
from generators.image import worker_lock

class ImageWorkerLockTests(unittest.TestCase):
    def test_queue_workers_share_gpu_lock(self):
        with tempfile.TemporaryFile() as handle, patch.object(worker_lock,'has_queue_reservation',return_value=True), patch.object(worker_lock.fcntl,'flock') as lock:
            worker_lock.acquire_worker_lock(handle,'waiting-gpu')
            lock.assert_called_once_with(handle,fcntl.LOCK_SH|fcntl.LOCK_NB)

    def test_direct_and_download_workers_remain_exclusive(self):
        for reserved,stage in [(False,'waiting-gpu'),(True,'waiting-download')]:
            with tempfile.TemporaryFile() as handle, patch.object(worker_lock,'has_queue_reservation',return_value=reserved), patch.object(worker_lock.fcntl,'flock') as lock:
                worker_lock.acquire_worker_lock(handle,stage)
                lock.assert_called_once_with(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_missing_reservation_is_not_authorization(self):
        with patch.dict(worker_lock.os.environ,{'SLIME_GPU_RESERVATION_PATH':'/tmp/missing-reservation'}):
            self.assertFalse(worker_lock.has_queue_reservation())
