"""사용자의 현재 파일을 별도 저장소에 복사해 검토 가능한 변경 기준을 만든다."""
import os
from pathlib import Path
import shutil
import stat
import subprocess

MAXIMUM_SNAPSHOT_BYTES = 2 * 1024 * 1024 * 1024
COMPATIBILITY_LINKS = {
    'gui': 'tools/management/gui',
    'generators': 'tools/management/generators',
    'baseline': 'tools/management/baseline',
    'tools/management/ui': 'gui/ui',
}


def run_snapshot_git_command(snapshot_repository_path, snapshot_argument_values):
    snapshot_environment_values = {snapshot_key_value: snapshot_item_value for snapshot_key_value, snapshot_item_value in os.environ.items() if not snapshot_key_value.startswith('GIT_')}
    snapshot_environment_values.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_SYSTEM='/dev/null')
    return subprocess.run(['git', '-C', str(snapshot_repository_path), *snapshot_argument_values], env=snapshot_environment_values, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def list_snapshot_source_files(source_repository_path):
    snapshot_file_bytes = run_snapshot_git_command(source_repository_path, ['ls-files', '--cached', '--others', '--exclude-standard', '-z'])
    return sorted(set(os.fsdecode(snapshot_file_value) for snapshot_file_value in snapshot_file_bytes.split(b'\0') if snapshot_file_value))


def read_snapshot_source_state(source_repository_path, snapshot_relative_name):
    snapshot_relative_path = Path(snapshot_relative_name)
    if snapshot_relative_path.is_absolute() or any(snapshot_part_value in ('', '..', '.git') for snapshot_part_value in snapshot_relative_path.parts):
        raise ValueError('허용되지 않는 작업 공간 경로입니다.')
    source_current_path = source_repository_path
    for snapshot_part_value in snapshot_relative_path.parts:
        source_current_path = source_current_path / snapshot_part_value
        if source_current_path.is_symlink():
            current_link_name = source_current_path.relative_to(source_repository_path).as_posix()
            if current_link_name not in COMPATIBILITY_LINKS or os.readlink(source_current_path) != COMPATIBILITY_LINKS[current_link_name]:
                raise ValueError(f'심볼릭 링크는 격리 작업에 포함할 수 없습니다: {snapshot_relative_name}')
            if current_link_name != snapshot_relative_name:
                # 이전 추적 파일은 이동된 원본이 새 경로에서 별도로 복사된다.
                return source_current_path, None
            current_link_stat = source_current_path.lstat()
            return source_current_path, (current_link_stat.st_dev, current_link_stat.st_ino, current_link_stat.st_size, current_link_stat.st_mtime_ns, current_link_stat.st_ctime_ns, current_link_stat.st_mode)
    try:
        source_current_stat = source_current_path.stat()
    except FileNotFoundError:
        return source_current_path, None
    # Git can still list the former root symlink while its replacement files are untracked.
    if snapshot_relative_name in COMPATIBILITY_LINKS and stat.S_ISDIR(source_current_stat.st_mode):
        return source_current_path, None
    if not stat.S_ISREG(source_current_stat.st_mode):
        raise ValueError(f'일반 파일이 아닙니다: {snapshot_relative_name}')
    return source_current_path, (source_current_stat.st_dev, source_current_stat.st_ino, source_current_stat.st_size, source_current_stat.st_mtime_ns, source_current_stat.st_ctime_ns, source_current_stat.st_mode)


def copy_snapshot_source_files(source_repository_path, snapshot_workspace_path):
    """추적 파일과 무시되지 않은 신규 파일의 현재 내용을 복사한다.

    고정된 호환 링크만 링크 자체로 복사하고 그 외 심볼릭 링크와 특수 파일은 거부한다.
    복사 중 바뀐 파일과 목록 변경은 조용히 부분 상태를 만들지 않고 실패한다.
    """
    source_repository_path = Path(source_repository_path).resolve(strict=True)
    snapshot_workspace_path = Path(snapshot_workspace_path)
    if snapshot_workspace_path.exists():
        raise ValueError('격리 작업 공간이 이미 존재합니다.')
    snapshot_source_head = run_snapshot_git_command(source_repository_path, ['rev-parse', 'HEAD']).strip()
    snapshot_source_names = list_snapshot_source_files(source_repository_path)
    snapshot_workspace_path.mkdir(parents=True)
    snapshot_total_bytes = 0
    snapshot_source_states = {}
    for snapshot_relative_name in snapshot_source_names:
        snapshot_relative_path = Path(snapshot_relative_name)
        source_current_path, source_original_state = read_snapshot_source_state(source_repository_path, snapshot_relative_name)
        snapshot_source_states[snapshot_relative_name] = source_original_state
        if source_original_state is None:
            continue
        snapshot_total_bytes += source_original_state[2]
        if snapshot_total_bytes > MAXIMUM_SNAPSHOT_BYTES:
            raise ValueError('격리 작업 파일이 최대 크기를 초과했습니다.')
        snapshot_current_path = snapshot_workspace_path / snapshot_relative_path
        snapshot_current_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_current_path, snapshot_current_path, follow_symlinks=False)
        _, source_finished_state = read_snapshot_source_state(source_repository_path, snapshot_relative_name)
        if source_original_state != source_finished_state:
            raise ValueError(f'격리 작업 복사 중 원본이 변경됐습니다: {snapshot_relative_name}')
    if snapshot_source_names != list_snapshot_source_files(source_repository_path) or snapshot_source_head != run_snapshot_git_command(source_repository_path, ['rev-parse', 'HEAD']).strip():
        raise ValueError('격리 작업 복사 중 원본 목록 또는 HEAD가 변경됐습니다.')
    for snapshot_relative_name, source_original_state in snapshot_source_states.items():
        _, source_finished_state = read_snapshot_source_state(source_repository_path, snapshot_relative_name)
        if source_original_state != source_finished_state:
            raise ValueError(f'격리 작업 복사 중 원본이 변경됐습니다: {snapshot_relative_name}')
    run_snapshot_git_command(snapshot_workspace_path, ['init', '-q'])
    run_snapshot_git_command(snapshot_workspace_path, ['config', 'user.name', 'Hermes Sandbox'])
    run_snapshot_git_command(snapshot_workspace_path, ['config', 'user.email', 'hermes-sandbox@localhost'])
    run_snapshot_git_command(snapshot_workspace_path, ['add', '-f', '--all'])
    run_snapshot_git_command(snapshot_workspace_path, ['commit', '-q', '--allow-empty', '-m', 'chore: 격리 작업 기준 생성'])
    snapshot_copied_count = sum(snapshot_state_value is not None for snapshot_state_value in snapshot_source_states.values())
    return {'source_head': snapshot_source_head.decode('ascii'), 'baseline_commit': run_snapshot_git_command(snapshot_workspace_path, ['rev-parse', 'HEAD']).decode('ascii').strip(), 'file_count': snapshot_copied_count, 'deleted_file_count': len(snapshot_source_names) - snapshot_copied_count, 'size_bytes': snapshot_total_bytes}


def collect_snapshot_change_diff(snapshot_workspace_path, snapshot_baseline_commit):
    """추가·삭제·변경 파일을 기준 커밋과 비교해 바이너리 diff로 반환한다."""
    snapshot_workspace_path = Path(snapshot_workspace_path)
    if len(snapshot_baseline_commit) != 40 or any(snapshot_hex_digit not in '0123456789abcdef' for snapshot_hex_digit in snapshot_baseline_commit):
        raise ValueError('격리 작업 기준 커밋 형식 오류')
    run_snapshot_git_command(snapshot_workspace_path, ['add', '--all'])
    return run_snapshot_git_command(snapshot_workspace_path, ['diff', '--cached', '--binary', '--no-ext-diff', snapshot_baseline_commit, '--'])
