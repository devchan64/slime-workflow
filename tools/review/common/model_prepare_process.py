"""게이트웨이와 수명이 분리된 모델 준비 프로세스."""
import fcntl
import json
import os
from pathlib import Path
import subprocess

from tools.review.common.generation_records import write_record_atomically


def inspect_detached_preparation(current_state_root):
    current_state_root.mkdir(parents=True, exist_ok=True)
    with (current_state_root/'worker.lock').open('a') as current_lock_file:
        try:
            fcntl.flock(current_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'running'
        else:
            fcntl.flock(current_lock_file, fcntl.LOCK_UN)
    current_status_path = current_state_root/'status.json'
    try:
        current_status_value = json.loads(current_status_path.read_text(encoding='utf-8')).get('status', 'idle')
    except (OSError, ValueError, AttributeError):
        return 'idle'
    return 'failed' if current_status_value == 'running' else current_status_value if current_status_value in ('idle', 'failed', 'completed') else 'failed'


def start_detached_preparation(current_state_root, current_command_prefix, current_working_root):
    current_state_root.mkdir(parents=True, exist_ok=True)
    current_lock_file = (current_state_root/'worker.lock').open('a')
    try:
        try:
            fcntl.flock(current_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'preparation_status': 'running'}
        current_status_path = current_state_root/'status.json'
        write_record_atomically(current_status_path, {'status': 'running'})
        try:
            with (current_state_root/'worker.log').open('ab') as current_log_file:
                subprocess.Popen([*current_command_prefix, '--status-path', str(current_status_path), '--lock-fd', str(current_lock_file.fileno())],
                    cwd=current_working_root, stdout=current_log_file, stderr=subprocess.STDOUT,
                    start_new_session=True, pass_fds=(current_lock_file.fileno(),))
        except BaseException:
            write_record_atomically(current_status_path, {'status': 'failed'})
            raise
        return {'preparation_status': 'running'}
    finally:
        current_lock_file.close()
