"""부모 실행기의 생존과 상주 모델 사용권에 묶인 대화 작업자."""
import ctypes
import os
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from workflow.domains.hermes_agent.worker import execute_resident_hermes_job, interrupt_hermes_gpu_job


def main(job_directory, resident_id, session_id, expected_parent, gate_fd):
    signal.signal(signal.SIGTERM, interrupt_hermes_gpu_job)
    # 설치와 부모 확인 사이에 부모가 죽은 경우도 거부한다.
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), '부모 종료 감시를 설정할 수 없습니다.')
    if os.getppid() != expected_parent:
        raise RuntimeError('대화 실행기가 이미 종료되었습니다.')
    with os.fdopen(gate_fd, 'rb', buffering=0) as gate:
        if gate.read(1) != b'1' or os.getppid() != expected_parent:
            raise RuntimeError('대화 실행기의 프로세스 신원을 확인할 수 없습니다.')
    execute_resident_hermes_job(job_directory, resident_id, session_id)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
