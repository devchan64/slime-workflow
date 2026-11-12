"""영상 작업 실행기가 비정상 종료된 상태를 보수적으로 복구한다."""
import fcntl
import json
import os
from pathlib import Path

from tools.review.common.generation_records import write_record_atomically


def has_live_video_worker(current_job_directory, current_command_record):
    """같은 사용자 프로세스의 명령 인자에서 해당 작업자를 찾는다."""
    current_command_values = current_command_record['command']
    if not isinstance(current_command_values, list) or len(current_command_values) < 4:
        raise ValueError('실행 명령을 확인할 수 없어 상태를 복구하지 않습니다.')
    current_expected_worker = str(Path(current_command_values[1]).resolve())
    current_expected_job = str(current_job_directory.resolve())
    for current_process_path in Path('/proc').iterdir():
        if not current_process_path.name.isdecimal():
            continue
        try:
            if current_process_path.stat().st_uid != os.getuid():
                continue
            current_arguments = (current_process_path / 'cmdline').read_bytes().split(b'\0')
        except FileNotFoundError:
            continue
        except OSError as current_read_error:
            raise ValueError(f'프로세스 확인 실패로 상태 복구 중단: {current_process_path}') from current_read_error
        current_arguments = [os.fsdecode(current_argument) for current_argument in current_arguments if current_argument]
        if len(current_arguments) >= 4 and current_arguments[1] == current_expected_worker:
            for current_argument_index, current_argument in enumerate(current_arguments[:-1]):
                if current_argument == '--job-dir' and str(Path(current_arguments[current_argument_index + 1]).resolve()) == current_expected_job:
                    return True
    return False


def recover_interrupted_video_job(current_job_directory):
    """실행기 잠금과 독립 작업자가 모두 없을 때만 running을 failed로 바꾼다."""
    current_job_directory = Path(current_job_directory)
    current_status_path = current_job_directory / 'status.json'
    if not current_status_path.is_file() or json.loads(current_status_path.read_text()).get('status') != 'running':
        return
    current_lock_path = current_job_directory / 'execution.lock'
    current_command_path = current_job_directory / 'gpu-command.json'
    if not current_lock_path.is_file() or current_lock_path.is_symlink() or not current_command_path.is_file():
        return
    with (current_job_directory / 'resume.lock').open('a') as current_resume_lock:
        fcntl.flock(current_resume_lock, fcntl.LOCK_EX)
        with current_lock_path.open('r+') as current_execution_lock:
            try:
                fcntl.flock(current_execution_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            current_status_record = json.loads(current_status_path.read_text())
            if current_status_record.get('status') != 'running':
                return
            current_command_record = json.loads(current_command_path.read_text())
            if has_live_video_worker(current_job_directory, current_command_record):
                return
            current_status_record.update(status='failed', recovered_interrupted=True, error='실행기와 작업자가 예기치 않게 종료되어 상태를 복구했습니다. 종료 원인은 로그와 시스템 기록을 확인하세요.')
            write_record_atomically(current_status_path, current_status_record)


def normalize_recovered_video_metrics(current_status_record):
    """마지막 표본은 보존하되 종료된 작업의 예상시간을 현재 값으로 표시하지 않는다."""
    if not current_status_record.get('recovered_interrupted'):
        return
    for current_metrics_key in ('metrics', 'worker_metrics'):
        current_metrics_record = current_status_record.get(current_metrics_key)
        if not isinstance(current_metrics_record, dict):
            continue
        current_metrics_record['status'] = 'failed'
        for current_estimate_key in ('estimate', 'inference_estimate'):
            current_estimate_record = current_metrics_record.get(current_estimate_key)
            if isinstance(current_estimate_record, dict):
                current_estimate_record.update(remaining=None, completion=None, estimated_progress=None, basis='실행기 비정상 종료로 추정 중단 · 마지막 관측 보존')
    current_estimate_record = current_status_record.get('estimate')
    if isinstance(current_estimate_record, dict):
        current_estimate_record.update(remaining=None, completion=None, estimated_progress=None, basis='실행기 비정상 종료로 추정 중단 · 마지막 관측 보존')
