"""생성기 소유 작업 파일의 검증·잠금·용량 집계를 공유한다."""
from contextlib import ExitStack
import fcntl
import json
from pathlib import Path
import shutil

GENERATION_CLEANUP_TERMINAL_STATES = frozenset(('completed', 'failed', 'cancelled', 'paused'))
GENERATION_CLEANUP_SCOPE_TEXT = '작업 폴더의 입력 사본·중간 산출물·결과·모든 시도의 로그와 기록을 함께 삭제합니다. 복구할 수 없습니다. 외부 입력 원본·등록 에셋·모델은 제외합니다. 실행·대기 중에는 삭제할 수 없습니다.'


def validate_cleanup_path(current_target_path, current_storage_root):
    current_target_path = Path(current_target_path).absolute()
    current_storage_root = Path(current_storage_root).absolute()
    if current_storage_root.resolve() != current_storage_root or current_target_path.resolve() != current_target_path or not current_target_path.is_relative_to(current_storage_root) or current_target_path == current_storage_root:
        raise ValueError(f'삭제 경로가 관리 루트 밖이거나 심볼릭 링크입니다: {current_target_path}')
    return current_target_path


def delete_generation_job_files(current_storage_root, current_job_targets, current_index_paths=(), current_expected_jobs=None):
    """호출 서비스는 생성과 동일한 잠금을 유지해야 한다. 전체 사전 검증 후 삭제한다."""
    current_deleted_bytes = 0
    current_deleted_count = 0
    with ExitStack() as current_lock_stack:
        current_validated_targets = []
        current_observed_jobs = []
        for current_target_path in sorted(set(map(Path, current_job_targets))):
            current_target_path = validate_cleanup_path(current_target_path, current_storage_root)
            if not current_target_path.is_dir():
                raise ValueError(f'삭제할 작업 폴더가 없습니다: {current_target_path}')
            current_resume_path = current_target_path/'resume.lock'
            if current_resume_path.is_symlink():
                raise ValueError(f'작업 잠금 경로 오류: {current_resume_path}')
            current_resume_handle = current_lock_stack.enter_context(current_resume_path.open('a'))
            fcntl.flock(current_resume_handle, fcntl.LOCK_EX)
            current_status_path = current_target_path/'status.json'
            if current_status_path.is_symlink() or not current_status_path.is_file():
                raise ValueError(f'작업 상태 파일 오류: {current_status_path}')
            current_status_value = json.loads(current_status_path.read_text()).get('status')
            if current_status_value not in GENERATION_CLEANUP_TERMINAL_STATES:
                raise ValueError(f'실행·대기 또는 상태 미확인 작업은 삭제할 수 없습니다: {current_target_path.name} ({current_status_value})')
            current_observed_jobs.append({'path':str(current_target_path.relative_to(current_storage_root)),'status':current_status_value})
            current_target_bytes = 0
            for current_child_path in current_target_path.rglob('*'):
                if current_child_path.is_symlink():
                    raise ValueError(f'심볼릭 링크가 포함된 작업은 삭제할 수 없습니다: {current_child_path}')
                if current_child_path.is_file():
                    current_target_bytes += current_child_path.stat().st_size
            current_validated_targets.append((current_target_path,current_target_bytes))
        if current_expected_jobs is not None and current_observed_jobs != current_expected_jobs:
            raise ValueError('삭제 대상 또는 상태가 변경되었습니다. 삭제 대상을 다시 확인하세요.')
        current_index_targets = list(map(Path,current_index_paths))
        for current_index_path in current_index_targets:
            if current_index_path.is_symlink() or current_index_path.parent.resolve()!=current_index_path.parent.absolute():
                raise ValueError(f'이력 인덱스 경로 오류: {current_index_path}')
            if current_index_path.exists() and not current_index_path.is_file():
                raise ValueError(f'이력 인덱스가 파일이 아닙니다: {current_index_path}')
        try:
            for current_target_path,current_target_bytes in current_validated_targets:
                shutil.rmtree(current_target_path)
                current_deleted_bytes += current_target_bytes
                current_deleted_count += 1
            for current_index_path in current_index_targets:
                if current_index_path.exists():
                    current_index_bytes = current_index_path.stat().st_size
                    current_index_path.unlink()
                    current_deleted_bytes += current_index_bytes
        except OSError as current_delete_error:
            raise OSError(f'파일 삭제 일부 실패: 완료 {current_deleted_count}건, {current_deleted_bytes}바이트; {current_delete_error}') from current_delete_error
    return {'status':'cleared','deleted_jobs':current_deleted_count,'deleted_bytes':current_deleted_bytes,'files_preserved':False}


def describe_generation_cleanup(current_storage_root, current_job_targets):
    """삭제 예정 작업을 읽기 전용으로 확인한다. 실행 시 재검증을 대체하지 않는다."""
    current_target_records = []
    current_blocked_records = []
    for current_target_path in sorted(set(map(Path, current_job_targets))):
        current_target_path = validate_cleanup_path(current_target_path, current_storage_root)
        if not current_target_path.is_dir():
            raise ValueError(f'작업 폴더가 아닙니다: {current_target_path}')
        current_status_path = current_target_path / 'status.json'
        if current_status_path.is_symlink() or not current_status_path.is_file():
            raise ValueError(f'작업 상태 파일 오류: {current_status_path}')
        current_status_record = json.loads(current_status_path.read_text())
        if not isinstance(current_status_record, dict) or not isinstance(current_status_record.get('status'), str):
            raise ValueError(f'작업 상태 형식 오류: {current_status_path}')
        if any(current_child_path.is_symlink() for current_child_path in current_target_path.rglob('*')):
            raise ValueError(f'심볼릭 링크가 포함된 작업: {current_target_path}')
        current_target_record = {'path': str(current_target_path.relative_to(current_storage_root)), 'status': current_status_record['status']}
        current_target_records.append(current_target_record)
        if current_status_record['status'] not in GENERATION_CLEANUP_TERMINAL_STATES:
            current_blocked_records.append(current_target_record)
    return {'job_count': len(current_target_records), 'jobs': current_target_records,
            'blocked_jobs': current_blocked_records, 'can_reset': not current_blocked_records,
            'scope': GENERATION_CLEANUP_SCOPE_TEXT,
            'notice': '목록에서 숨긴 작업도 포함합니다. 삭제 시 상태를 다시 검증합니다.'}


def read_cleanup_confirmation(current_request_record, current_allow_empty=False):
    """기존 CLI 초기화와 GUI의 확인한 대상 목록을 엄격히 구분한다."""
    if current_allow_empty and current_request_record=={}:return None
    if not isinstance(current_request_record,dict) or current_request_record.get('action')!='reset' or set(current_request_record)-{'action','expected_jobs'}:
        raise ValueError('초기화 요청 필드 오류')
    if 'expected_jobs' not in current_request_record:return None
    current_expected_jobs=current_request_record['expected_jobs']
    if not isinstance(current_expected_jobs,list) or any(not isinstance(current_job_record,dict) or set(current_job_record)!={'path','status'} or not all(isinstance(current_job_record[current_field_name],str) for current_field_name in ('path','status')) for current_job_record in current_expected_jobs):
        raise ValueError('확인한 삭제 대상 목록 형식 오류')
    return current_expected_jobs
