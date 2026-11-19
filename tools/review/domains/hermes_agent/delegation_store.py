"""관리 작업 접수 결과와 불확실한 응답을 재접수 없이 확인한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import threading

from tools.review.common.generation_records import write_record_atomically

HERMES_DELEGATION_ROOT = Path(__file__).resolve().parents[4] / '.local/hermes-agent/delegations'
HERMES_DELEGATION_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')
HERMES_DELEGATION_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_DELEGATION_SERVICE_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
HERMES_DELEGATION_THREAD_LOCK = threading.RLock()


def list_hermes_service_receipt_names():
    """서비스별 접수 직접 조회가 지원하는 원 서비스만 반환한다."""
    from tools.review.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
    from tools.review.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    return (*HERMES_AUDIO_SERVICES, *HERMES_VIDEO_SERVICES, *FLUX_IMAGE_PROFILE_RECORDS, 'flux-expression', 'prompt-translation', 'writer-agent')


def validate_service_job_identifier(current_service_name, current_job_identifier):
    """서비스별 기존 작업 ID 형식을 유지한다."""
    if not isinstance(current_job_identifier,str):
        return False
    if current_service_name == 'writer-agent':
        from generators.writer_agent.jobs import JOB_IDENTIFIER_PATTERN
        return bool(JOB_IDENTIFIER_PATTERN.fullmatch(current_job_identifier))
    return bool(HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_identifier))


class HermesDelegationStore:
    """접수 ID별 입력 해시와 서비스의 작업 ID만 보관한다."""

    def __init__(self, delegation_storage_root=HERMES_DELEGATION_ROOT):
        self.delegation_storage_root = Path(delegation_storage_root)

    @contextmanager
    def hold_delegation_storage_lock(self):
        if self.delegation_storage_root.is_symlink():
            raise ValueError('위임 저장 경로에 심볼릭 링크를 사용할 수 없습니다.')
        self.delegation_storage_root.mkdir(parents=True, exist_ok=True)
        current_lock_path = self.delegation_storage_root / '.delegations.lock'
        if current_lock_path.is_symlink():
            raise ValueError('위임 잠금 경로에 심볼릭 링크를 사용할 수 없습니다.')
        with HERMES_DELEGATION_THREAD_LOCK, current_lock_path.open('a') as current_lock_stream:
            fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
            yield

    def resolve_delegation_record_path(self, delegation_identifier_value):
        if not isinstance(delegation_identifier_value, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(delegation_identifier_value):
            raise ValueError('위임 접수 식별자 형식 오류')
        current_path_value = self.delegation_storage_root / (delegation_identifier_value + '.json')
        if current_path_value.is_symlink():
            raise ValueError('위임 기록은 심볼릭 링크일 수 없습니다.')
        return current_path_value

    def read_delegation_status(self, delegation_identifier_value):
        """접수 ID로 저장된 결과만 읽는다. 생성 명령은 실행하지 않는다."""
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if not current_record_path.exists():
                return {'state': 'not_found'}
            current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
            if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != delegation_identifier_value or current_saved_record.get('state') not in ('dispatching', 'accepted'):
                raise ValueError('위임 기록 형식 오류')
            if current_saved_record['state'] == 'dispatching':
                return {'state': 'unknown', 'message': '접수 결과 확인 필요. Kimodo 이력과 실제 작업을 확인하고 자동 재접수하지 마세요.'}
            if not isinstance(current_saved_record.get('job_id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_saved_record['job_id']):
                raise ValueError('위임 작업 ID 형식 오류')
            return {'state': 'accepted', 'job_id': current_saved_record['job_id']}

    def list_delegation_receipts(self):
        """최근 접수 식별자와 확인 상태만 반환하며 입력·해시는 공개하지 않는다."""
        with self.hold_delegation_storage_lock():
            current_receipt_values = []
            for current_record_path in self.delegation_storage_root.glob('*.json'):
                current_receipt_identifier = current_record_path.stem
                if current_record_path.is_symlink() or not current_record_path.is_file() or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_receipt_identifier):
                    continue
                try:
                    current_updated_time = current_record_path.stat().st_mtime
                    current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
                    # 기존 Kimodo 화면에는 다른 서비스의 접수 기록을 노출하지 않는다.
                    if isinstance(current_saved_record, dict) and current_saved_record.get('version') in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                        continue
                    if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != current_receipt_identifier:
                        raise ValueError('위임 기록 형식 오류')
                    current_state_value = current_saved_record.get('state')
                    current_job_identifier = current_saved_record.get('job_id')
                    if current_state_value == 'dispatching':
                        current_state_value = 'unknown'
                        current_job_identifier = None
                    elif current_state_value != 'accepted' or not isinstance(current_job_identifier, str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_identifier):
                        raise ValueError('위임 작업 상태 오류')
                except (OSError, ValueError, TypeError, KeyError):
                    current_updated_time = 0
                    current_state_value = 'unavailable'
                    current_job_identifier = None
                current_receipt_values.append({'request_id': current_receipt_identifier, 'state': current_state_value, 'job_id': current_job_identifier, 'updated_at': datetime.fromtimestamp(current_updated_time, timezone.utc).isoformat() if current_updated_time else None, '_sort_time': current_updated_time})
            current_receipt_values.sort(key=lambda current_receipt_value: (current_receipt_value['_sort_time'], current_receipt_value['request_id']), reverse=True)
            for current_receipt_value in current_receipt_values:
                current_receipt_value.pop('_sort_time')
            return {'records': current_receipt_values[:100], 'truncated': len(current_receipt_values) > 100}

    def execute_delegation_once(self, delegation_identifier_value, delegation_request_record, delegation_submit_callback, delegation_validate_callback=None):
        """접수 전 기록한다. 결과 유실 시 재실행하지 않고 확인 필요를 반환한다."""
        if not isinstance(delegation_request_record, dict):
            raise ValueError('위임 입력은 객체여야 합니다.')
        current_serialized_value = json.dumps(delegation_request_record, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        current_request_digest = hashlib.sha256(current_serialized_value).hexdigest()
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if current_record_path.exists():
                current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != delegation_identifier_value or current_saved_record.get('state') not in ('dispatching', 'accepted'):
                    raise ValueError('위임 기록 형식 오류')
                if current_saved_record.get('request_sha256') != current_request_digest:
                    raise ValueError('같은 위임 식별자를 다른 입력에 사용할 수 없습니다.')
                if current_saved_record['state'] == 'dispatching':
                    return {'state': 'unknown', 'duplicate': True, 'message': '접수 결과가 확인되지 않았습니다. 생성기 이력을 확인하고 자동 재접수하지 마세요.'}
                if not isinstance(current_saved_record.get('job_id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_saved_record['job_id']):
                    raise ValueError('위임 작업 ID 형식 오류')
                return {'state': 'accepted', 'duplicate': True, 'job_id': current_saved_record['job_id']}
            if delegation_validate_callback is not None:
                delegation_validate_callback(delegation_request_record)
            current_saved_record = {'version': 1, 'id': delegation_identifier_value, 'request_sha256': current_request_digest, 'state': 'dispatching'}
            write_record_atomically(current_record_path, current_saved_record)
            current_response_record = delegation_submit_callback(delegation_request_record)
            if not isinstance(current_response_record, dict) or not isinstance(current_response_record.get('id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_response_record['id']):
                raise ValueError('접수 응답의 작업 ID를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            if json.loads(current_record_path.read_text(encoding='utf-8')) != current_saved_record:
                raise ValueError('접수 중 기록이 변경됐습니다. 원 서비스와 접수 기록을 확인하고 자동 재접수하지 마세요.')
            current_saved_record.update(state='accepted', job_id=current_response_record['id'])
            write_record_atomically(current_record_path, current_saved_record)
            return {'state': 'accepted', 'duplicate': False, 'job_id': current_saved_record['job_id']}

    def read_service_delegation(self, delegation_identifier_value, expected_service_name):
        """서비스가 일치하는 새 버전의 접수 상태만 반환한다."""
        if not isinstance(expected_service_name, str) or not HERMES_DELEGATION_SERVICE_PATTERN.fullmatch(expected_service_name) or len(expected_service_name) > 80:
            raise ValueError('위임 서비스 식별자 형식 오류')
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if not current_record_path.exists():
                return {'state':'not_found','request_id':delegation_identifier_value,'service':expected_service_name}
            current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
            if not isinstance(current_record_value, dict) or current_record_value.get('version') != 2 or current_record_value.get('id') != delegation_identifier_value or current_record_value.get('service') != expected_service_name or current_record_value.get('state') not in ('dispatching', 'accepted'):
                raise ValueError('위임 서비스 또는 기록이 일치하지 않습니다.')
            if current_record_value['state'] == 'dispatching':
                return {'state':'unknown', 'request_id':delegation_identifier_value, 'service':expected_service_name, 'message':'접수 결과를 확인하고 자동 재접수하지 마세요.'}
            current_job_identifier = current_record_value.get('job_id')
            if not validate_service_job_identifier(expected_service_name, current_job_identifier):
                raise ValueError('위임 작업 ID 형식 오류')
            return {'state':'accepted', 'request_id':delegation_identifier_value, 'service':expected_service_name, 'job_id':current_job_identifier}

    def list_service_delegations(self, expected_service_name):
        """선택 서비스의 새 접수 기록을 최근 순으로 읽는다."""
        if not isinstance(expected_service_name, str) or not HERMES_DELEGATION_SERVICE_PATTERN.fullmatch(expected_service_name) or len(expected_service_name) > 80:
            raise ValueError('위임 서비스 식별자 형식 오류')
        with self.hold_delegation_storage_lock():
            current_records_list = []
            for current_record_path in self.delegation_storage_root.glob('*.json'):
                current_record_id = current_record_path.stem
                if current_record_path.is_symlink() or not current_record_path.is_file() or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_record_id):
                    continue
                try:
                    current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
                    if not isinstance(current_record_value, dict) or current_record_value.get('version') != 2 or current_record_value.get('service') != expected_service_name:
                        continue
                    if current_record_value.get('id') != current_record_id:
                        raise ValueError('접수 ID 불일치')
                    current_state_value = current_record_value.get('state')
                    current_job_identifier = current_record_value.get('job_id')
                    if current_state_value == 'dispatching':
                        current_state_value, current_job_identifier = 'unknown', None
                    elif current_state_value != 'accepted' or not validate_service_job_identifier(expected_service_name, current_job_identifier):
                        raise ValueError('접수 상태 오류')
                    current_updated_time = current_record_path.stat().st_mtime
                    current_records_list.append({'request_id':current_record_id, 'service':expected_service_name, 'state':current_state_value, 'job_id':current_job_identifier, 'updated_at':datetime.fromtimestamp(current_updated_time, timezone.utc).isoformat(), '_sort_time':current_updated_time})
                except (OSError, ValueError, TypeError, KeyError):
                    continue
            current_records_list.sort(key=lambda current_record_value:(current_record_value['_sort_time'], current_record_value['request_id']), reverse=True)
            for current_record_value in current_records_list:
                current_record_value.pop('_sort_time')
            return {'records':current_records_list[:100], 'truncated':len(current_records_list)>100, 'note':'손상되거나 서비스 확인이 불가능한 기록은 목록에서 제외됩니다.'}

    def execute_service_delegation_once(self, delegation_identifier_value, delegation_service_name, delegation_request_record, delegation_submit_callback, delegation_validate_callback):
        """서비스와 입력을 함께 고정하고 접수 결과가 불확실하면 재실행하지 않는다."""
        if not isinstance(delegation_service_name, str) or not HERMES_DELEGATION_SERVICE_PATTERN.fullmatch(delegation_service_name) or len(delegation_service_name) > 80:
            raise ValueError('위임 서비스 식별자 형식 오류')
        if not isinstance(delegation_request_record, dict) or not callable(delegation_validate_callback):
            raise ValueError('검증 가능한 위임 입력이 필요합니다.')
        current_request_bytes = json.dumps({'service':delegation_service_name, 'request':delegation_request_record}, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        current_request_digest = hashlib.sha256(current_request_bytes).hexdigest()
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if current_record_path.exists():
                current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_record_value, dict) or current_record_value.get('version') != 2 or current_record_value.get('id') != delegation_identifier_value or current_record_value.get('service') != delegation_service_name or current_record_value.get('request_sha256') != current_request_digest:
                    raise ValueError('같은 위임 식별자를 다른 서비스나 입력에 사용할 수 없습니다.')
                if current_record_value.get('state') == 'dispatching':
                    return {'state':'unknown', 'duplicate':True, 'service':delegation_service_name}
                current_job_identifier = current_record_value.get('job_id')
                if current_record_value.get('state') != 'accepted' or not validate_service_job_identifier(delegation_service_name, current_job_identifier):
                    raise ValueError('위임 기록 형식 오류')
                return {'state':'accepted', 'duplicate':True, 'service':delegation_service_name, 'job_id':current_job_identifier}
            delegation_validate_callback(delegation_request_record)
            current_record_value = {'version':2, 'id':delegation_identifier_value, 'service':delegation_service_name, 'request_sha256':current_request_digest, 'state':'dispatching'}
            write_record_atomically(current_record_path, current_record_value)
            current_response_record = delegation_submit_callback(delegation_request_record)
            current_job_identifier = current_response_record.get('id') if isinstance(current_response_record, dict) else None
            if not validate_service_job_identifier(delegation_service_name, current_job_identifier):
                raise ValueError('접수 응답의 작업 ID를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            if json.loads(current_record_path.read_text(encoding='utf-8')) != current_record_value:
                raise ValueError('접수 중 기록이 변경됐습니다. 원 서비스와 접수 기록을 확인하고 자동 재접수하지 마세요.')
            current_record_value.update(state='accepted', job_id=current_job_identifier)
            write_record_atomically(current_record_path, current_record_value)
            return {'state':'accepted', 'duplicate':False, 'service':delegation_service_name, 'job_id':current_job_identifier}
