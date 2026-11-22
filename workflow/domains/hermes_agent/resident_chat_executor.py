"""검증된 상주 GPU 예약을 공유하는 대화의 독립 실행과 취소."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from workflow.common.generation_records import write_record_atomically
from workflow.common.gpu_job_queue import HERMES_PIDFD_GROUP_FLAG, stop_hermes_worker_process_group


def launch_resident_chat(job_directory, resident_id, session_id, *, log):
    directory = Path(job_directory).resolve(strict=True)
    command = [sys.executable, str(Path(__file__).resolve()), str(directory), resident_id, session_id]
    write_record_atomically(directory / 'gpu-command.json', {'command':command, 'service':'hermes-agent'})
    write_record_atomically(directory / 'status.json', {'status':'queued', 'message':'상주 모델 사용권 대기'})
    try:
        return subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    except BaseException as error:
        write_record_atomically(directory / 'status.json', {'status':'failed', 'error':str(error)})
        raise


def execute_resident_chat(job_directory, resident_id, session_id):
    directory = Path(job_directory).resolve(strict=True)
    lock_path = directory / 'execution.lock'
    if lock_path.is_symlink():
        raise ValueError('대화 실행 잠금 경로 오류')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fields = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()
        boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        write_record_atomically(directory / 'resident-executor.json', {'pid':os.getpid(), 'pid_start_token':fields[19], 'boot_id':boot_id})
        child = None
        pidfd = None
        gate_read = gate_write = None
        cancelled = False
        signal.signal(signal.SIGTERM, lambda *_: (directory / 'cancel.request').touch())
        try:
            if (directory / 'cancel.request').exists():
                write_record_atomically(directory / 'status.json', {'status':'cancelled'})
                return 0
            gate_read, gate_write = os.pipe()
            child = subprocess.Popen([sys.executable, str(ROOT / 'workflow/domains/hermes_agent/resident_chat_child.py'),
                str(directory), resident_id, session_id, str(os.getpid()), str(gate_read)],
                cwd=ROOT, pass_fds=(gate_read,), start_new_session=True)
            os.close(gate_read); gate_read = None
            pidfd = os.pidfd_open(child.pid)
            signal.pidfd_send_signal(pidfd, 0, None, HERMES_PIDFD_GROUP_FLAG)
            write_record_atomically(directory / 'status.json', {'status':'running'})
            os.write(gate_write, b'1')
            os.close(gate_write); gate_write = None
            while child.poll() is None:
                if (directory / 'cancel.request').exists():
                    cancelled = True
                    try:
                        signal.pidfd_send_signal(pidfd, signal.SIGTERM, None, HERMES_PIDFD_GROUP_FLAG)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass
                    break
                time.sleep(.25)
            stop_hermes_worker_process_group(child.pid, pidfd)
            child.wait()
            status = 'cancelled' if cancelled or (directory / 'cancel.request').exists() else 'completed' if child.returncode == 0 else 'failed'
            write_record_atomically(directory / 'status.json', {'status':status, 'exit_code':child.returncode})
            return 0 if status == 'completed' else 1
        except BaseException as error:
            write_record_atomically(directory / 'status.json', {'status':'failed', 'error':str(error)})
            raise
        finally:
            for fd in (gate_read, gate_write):
                if fd is not None:
                    os.close(fd)
            if child is not None:
                if pidfd is not None:
                    stop_hermes_worker_process_group(child.pid, pidfd)
                    os.close(pidfd)
                elif child.poll() is None:
                    child.kill()
                child.wait()


def observe_resident_chat_status(directory, status):
    """실행기가 사라진 기록을 실행 중으로 표시하지 않고 확인 필요로 보존한다."""
    if not isinstance(status, dict) or status.get('status') not in ('queued', 'running'):
        return status
    from workflow.common.gpu_job_queue import inspect_gpu_ticket_executor_identity
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    try:
        identity = read_bounded_delegation_record(Path(directory) / 'resident-executor.json')
        if inspect_gpu_ticket_executor_identity(identity) == 'verified':
            return status
    except (OSError, ValueError, TypeError):
        pass
    return {'status':'unknown', 'message':'상주 대화 실행기 상태를 확인할 수 없습니다. 자동으로 재접수하지 않습니다.'}


if __name__ == '__main__':
    sys.exit(execute_resident_chat(*sys.argv[1:]))
