"""고정된 Hermes 소스 리비전과 실행 준비 기록을 확인한다."""
import json
import os
from pathlib import Path
import subprocess

HERMES_RUNTIME_REVISION = '3b421578588243f920886e6fe79a6faa87ea026e'
HERMES_RUNTIME_SOURCE = 'https://github.com/NousResearch/hermes-agent'
HERMES_RUNTIME_RELEASE = 'v0.23.1'


def verify_hermes_runtime_integrity(hermes_runtime_path):
    hermes_runtime_path = Path(hermes_runtime_path)
    hermes_marker_path = hermes_runtime_path / 'prepared-local.json'
    if hermes_runtime_path.is_symlink() or hermes_marker_path.is_symlink() or not (hermes_runtime_path / '.venv/bin/python').is_file():
        raise ValueError('Hermes 실행환경 또는 준비 기록이 없습니다.')
    try:
        hermes_marker_record = json.loads(hermes_marker_path.read_text())
    except (OSError, ValueError) as hermes_marker_error:
        raise ValueError('Hermes 실행 준비 기록을 읽을 수 없습니다.') from hermes_marker_error
    if hermes_marker_record != {'revision':HERMES_RUNTIME_REVISION, 'release':HERMES_RUNTIME_RELEASE, 'source':HERMES_RUNTIME_SOURCE}:
        raise ValueError('Hermes 실행환경의 고정 리비전 기록이 다릅니다.')
    hermes_git_environment = {hermes_key_value: hermes_item_value for hermes_key_value, hermes_item_value in os.environ.items() if not hermes_key_value.startswith('GIT_')}
    hermes_git_environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')
    hermes_git_prefix = ['git', '-C', str(hermes_runtime_path), '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null']
    try:
        hermes_revision_result = subprocess.run([*hermes_git_prefix, 'rev-parse', 'HEAD'], env=hermes_git_environment, capture_output=True, text=True, check=True, timeout=30)
        hermes_status_result = subprocess.run([*hermes_git_prefix, 'status', '--porcelain=v1', '--untracked-files=all'], env=hermes_git_environment, capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as hermes_git_error:
        raise ValueError('Hermes 소스 리비전을 확인할 수 없습니다.') from hermes_git_error
    if hermes_revision_result.stdout.strip() != HERMES_RUNTIME_REVISION:
        raise ValueError('Hermes 소스가 고정 리비전과 다릅니다.')
    hermes_status_lines = hermes_status_result.stdout.splitlines()
    if any(hermes_status_line != '?? prepared-local.json' for hermes_status_line in hermes_status_lines):
        raise ValueError('Hermes 소스에 수정되거나 새로 추가된 파일이 있습니다.')
