"""사용자 승인된 GPU 양도의 영속 상태. 실제 작업 접수·종료는 수행하지 않는다."""
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.delegation_store import (
    HermesDelegationStore, check_delegation_record_exists, list_delegation_record_paths, read_bounded_delegation_record,
)

HANDOFF_ROOT = Path(__file__).resolve().parents[3] / '.local/hermes-agent/gpu-handoffs'
_ID = re.compile(r'[A-Za-z0-9_-]{8,80}\Z')
_SESSION = re.compile(r'[a-f0-9]{32}\Z')
_SERVICE = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
_DIGEST = re.compile(r'[a-f0-9]{64}\Z')
MAXIMUM_HANDOFF_INPUT_BYTES = 40 * 1024 * 1024
MAXIMUM_HANDOFF_RECORD_BYTES = MAXIMUM_HANDOFF_INPUT_BYTES + 65536
_TRANSITIONS = {
    'approved': {'waiting_release', 'cancelled', 'needs_attention'},
    # 해제 요청이 이미 전달됐을 수 있어 단순 취소하면 모델이 내려간 채 남는다.
    'waiting_release': {'submitting', 'cancel_waiting_release', 'needs_attention'},
    'cancel_waiting_release': {'cancel_reload_queued', 'needs_attention'},
    'cancel_reload_queued': {'cancel_reloading', 'needs_attention'},
    'cancel_reloading': {'cancelled', 'needs_attention'},
    'submitting': {'running', 'rejected_reload_queued', 'needs_attention'},
    'rejected_reload_queued': {'rejected_reloading', 'needs_attention'},
    'rejected_reloading': {'rejected', 'needs_attention'},
    'running': {'reload_queued', 'needs_attention'},
    'reload_queued': {'reloading', 'needs_attention'},
    'reloading': {'ready', 'needs_attention'},
    'ready': set(), 'cancelled': set(), 'rejected': set(), 'needs_attention': set(),
}


def _validate_binding(request_id, session_id, service, input_digest):
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
        raise ValueError('양도 요청 ID 오류')
    if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('대화 세션 ID 오류')
    if not isinstance(service, str) or len(service) > 80 or not _SERVICE.fullmatch(service):
        raise ValueError('대상 서비스 오류')
    if not isinstance(input_digest, str) or not _DIGEST.fullmatch(input_digest):
        raise ValueError('검토한 입력 지문 오류')


def _canonical_input(payload):
    if not isinstance(payload, dict):
        raise ValueError('확인한 대상 입력은 객체여야 합니다.')
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('확인한 대상 입력 형식 오류') from error
    if len(encoded) > MAXIMUM_HANDOFF_INPUT_BYTES:
        raise ValueError('확인한 대상 입력 크기 초과')
    return encoded


def summarize_handoff_request(record):
    request = record['target_request']
    if record['service'] == 'writer-agent' and isinstance(request.get('request'), dict):
        request = request['request']
    return {key:request.get(key) for key in ('prompt','mode','frames','width','height','steps','seed')}


def _read_handoff_record(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAXIMUM_HANDOFF_RECORD_BYTES:
            raise ValueError('GPU 양도 기록 형식 또는 크기 오류')
        data = stream.read(MAXIMUM_HANDOFF_RECORD_BYTES + 1)
    if len(data) > MAXIMUM_HANDOFF_RECORD_BYTES:
        raise ValueError('GPU 양도 기록 크기 초과')
    return json.loads(data)


def _validate_record(record, request_id):
    keys = {'version', 'id', 'session_id', 'service', 'input_digest', 'target_request', 'resident_id', 'model', 'state', 'revision', 'updated_at', 'job_id', 'target_status', 'reason'}
    if not isinstance(record, dict) or not keys.issubset(record) or set(record) - keys - {'uncertain_since','reload_retry'} or type(record.get('version')) is not int or record['version'] != 1 or record.get('id') != request_id:
        raise ValueError('GPU 양도 기록 형식 오류')
    record.setdefault('uncertain_since', None)
    record.setdefault('reload_retry', 0)
    if type(record['reload_retry']) is not int or record['reload_retry'] not in (0, 1):
        raise ValueError('재적재 재시도 기록 오류')
    _validate_binding(request_id, record['session_id'], record['service'], record['input_digest'])
    if (not isinstance(record['resident_id'], str) or not _ID.fullmatch(record['resident_id'])
            or hashlib.sha256(_canonical_input(record['target_request'])).hexdigest() != record['input_digest']):
        raise ValueError('승인한 상주 모델 또는 대상 입력이 일치하지 않습니다.')
    if record['model'] != 'qwen3.8-27b' or not isinstance(record['state'], str) or record['state'] not in _TRANSITIONS or type(record['revision']) is not int or record['revision'] < 1:
        raise ValueError('GPU 양도 상태 오류')
    if not isinstance(record['updated_at'], str) or any(value is not None and not isinstance(value, str) for value in (record['job_id'], record['target_status'], record['reason'], record['uncertain_since'])):
        raise ValueError('GPU 양도 세부 기록 오류')
    if record['state'] in ('running', 'reload_queued', 'reloading', 'ready') and (not isinstance(record['job_id'], str) or not _ID.fullmatch(record['job_id'])):
        raise ValueError('GPU 양도 대상 작업 기록 오류')
    if record['state'] in ('reload_queued', 'reloading', 'ready') and record['target_status'] not in ('completed', 'failed', 'cancelled'):
        raise ValueError('GPU 양도 대상 종료 기록 오류')
    if record['state'] == 'needs_attention' and (not record['reason'] or len(record['reason']) > 500):
        raise ValueError('GPU 양도 확인 필요 사유 오류')
    return record


class GpuHandoffStore(HermesDelegationStore):
    """확인된 요청을 원자적으로 저장하고 중복·낡은 상태 전이를 차단한다."""
    def __init__(self, root=HANDOFF_ROOT):
        super().__init__(root)

    @contextmanager
    def hold_delegation_storage_lock(self):
        root = self.delegation_storage_root
        if root.is_symlink():
            raise ValueError('GPU 양도 저장 경로 오류')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = root.stat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise ValueError('GPU 양도 입력을 저장할 개인 디렉터리가 필요합니다.')
        with super().hold_delegation_storage_lock():
            yield

    def approve(self, request_id, session_id, service, input_digest, *, target_request, resident_id, confirmed, precommit_check=None):
        _validate_binding(request_id, session_id, service, input_digest)
        encoded = _canonical_input(target_request)
        if hashlib.sha256(encoded).hexdigest() != input_digest or not isinstance(resident_id, str) or not _ID.fullmatch(resident_id):
            raise ValueError('승인한 상주 모델 또는 대상 입력이 일치하지 않습니다.')
        target_request = json.loads(encoded)
        if confirmed is not True:
            raise ValueError('대상과 재적재에 대한 명시적 확인이 필요합니다.')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            if check_delegation_record_exists(path):
                record = _validate_record(_read_handoff_record(path), request_id)
                if (record['session_id'], record['service'], record['input_digest'], record['resident_id']) != (session_id, service, input_digest, resident_id):
                    raise ValueError('같은 요청 ID를 다른 확인 대상에 사용할 수 없습니다.')
                return {**record, 'duplicate': True}
            withdrawn = self.delegation_storage_root / (request_id + '.withdrawn')
            if check_delegation_record_exists(withdrawn):
                raise ValueError('이 GPU 양도 요청은 철회되어 접수할 수 없습니다.')
            for existing_path in list_delegation_record_paths(self.delegation_storage_root):
                if existing_path.is_symlink() or not existing_path.is_file():
                    raise ValueError('기존 GPU 양도 기록을 확인할 수 없습니다.')
                existing = _validate_record(_read_handoff_record(existing_path), existing_path.stem)
                if (existing['session_id'], existing['service'], existing['input_digest']) == (session_id, service, input_digest) and existing['state'] not in ('ready', 'cancelled', 'rejected'):
                    raise ValueError('같은 확인 대상의 미완료 양도가 있습니다. 기존 요청 상태를 확인하세요.')
                if existing['state'] not in ('ready', 'cancelled', 'rejected') and (existing['session_id'] == session_id or existing['resident_id'] == resident_id):
                    raise ValueError('이 대화 또는 상주 모델의 미완료 양도가 있습니다. 기존 요청 상태를 확인하세요.')
            if precommit_check is not None:
                precommit_check()
            record = {'version':1, 'id':request_id, 'session_id':session_id, 'service':service,
                      'input_digest':input_digest, 'target_request':target_request, 'resident_id':resident_id, 'model':'qwen3.8-27b', 'state':'approved',
                      'revision':1, 'updated_at':datetime.now(timezone.utc).isoformat(),
                      'job_id':None, 'target_status':None, 'reason':None, 'uncertain_since':None}
            write_record_atomically(path, record)
            return {**record, 'duplicate': False}

    def withdraw_if_unaccepted(self, request_id, session_id, service):
        """승인 전 요청 ID를 봉인하거나 이미 접수된 원래 기록을 반환한다."""
        _validate_binding(request_id, session_id, service, '0'*64)
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            if check_delegation_record_exists(path):
                record = _validate_record(_read_handoff_record(path), request_id)
                if record['session_id'] != session_id or record['service'] != service:
                    raise ValueError('GPU 양도 요청의 세션 또는 서비스가 일치하지 않습니다.')
                return {key:value for key,value in record.items() if key != 'target_request'}
            withdrawn = self.delegation_storage_root / (request_id + '.withdrawn')
            expected = {'id':request_id, 'session_id':session_id, 'service':service, 'state':'withdrawn'}
            if check_delegation_record_exists(withdrawn):
                if read_bounded_delegation_record(withdrawn) != expected:
                    raise ValueError('철회 기록이 일치하지 않습니다.')
            else:
                write_record_atomically(withdrawn, expected)
            return expected

    def read(self, request_id):
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            if not check_delegation_record_exists(path):
                return None
            return dict(_validate_record(_read_handoff_record(path), request_id))

    def read_withdrawal(self, request_id, session_id):
        """철회 기록은 요청한 세션에 대해서만 확인한다."""
        if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
            raise ValueError('대화 세션 ID 오류')
        with self.hold_delegation_storage_lock():
            self.resolve_delegation_record_path(request_id)
            path = self.delegation_storage_root / (request_id + '.withdrawn')
            if not check_delegation_record_exists(path):
                return None
            row = read_bounded_delegation_record(path)
            if not isinstance(row, dict) or set(row) != {'id','session_id','service','state'} or row.get('id') != request_id or row.get('state') != 'withdrawn':
                raise ValueError('GPU 양도 철회 기록 오류')
            _validate_binding(row['id'],row['session_id'],row['service'],'0'*64)
            if row['session_id'] != session_id:
                raise ValueError('GPU 양도 요청의 세션이 일치하지 않습니다.')
            return row

    def list_active_ids(self):
        """손상된 기록을 숨기지 않고 재개 가능한 승인 작업 ID만 나열한다."""
        with self.hold_delegation_storage_lock():
            paths = list_delegation_record_paths(self.delegation_storage_root)
            if len(paths) > 10000:
                raise ValueError('GPU 양도 기록이 너무 많아 안전하게 조회할 수 없습니다.')
            active = []
            for path in paths:
                if path.is_symlink() or not path.is_file():
                    raise ValueError('GPU 양도 기록을 확인할 수 없습니다.')
                record = _validate_record(_read_handoff_record(path), path.stem)
                if record['state'] not in ('ready', 'cancelled', 'rejected', 'needs_attention'):
                    active.append(record['id'])
            return sorted(active)

    def list_session_records(self, session_id, limit=20):
        """현재 세션의 최근 양도만 입력 원본 없이 반환한다."""
        return self.list_session_records_page(session_id, 0, limit)['records']

    def list_session_records_page(self, session_id, offset=0, limit=20):
        if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id) or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError('GPU 양도 이력 조회 입력 오류')
        with self.hold_delegation_storage_lock():
            paths = list_delegation_record_paths(self.delegation_storage_root)
            if len(paths) > 10000:
                raise ValueError('GPU 양도 기록이 너무 많아 안전하게 조회할 수 없습니다.')
            rows = []
            for path in paths:
                if path.is_symlink() or not path.is_file():
                    raise ValueError('GPU 양도 기록을 확인할 수 없습니다.')
                record = _validate_record(_read_handoff_record(path), path.stem)
                if record['session_id'] != session_id:
                    continue
                summary = summarize_handoff_request(record)
                rows.append({**{key:value for key,value in record.items() if key != 'target_request'}, 'target_summary':summary})
            rows.sort(key=lambda row:(row['updated_at'],row['id']), reverse=True)
            return {'records':rows[offset:offset+limit], 'total':len(rows), 'offset':offset, 'limit':limit}

    def run_without_open_session_handoff(self, session_id, callback, *, all_sessions=False):
        """양도 승인과 상주 모델 최초 접수가 교차하지 않도록 같은 잠금을 유지한다."""
        if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
            raise ValueError('대화 세션 ID 오류')
        with self.hold_delegation_storage_lock():
            for path in list_delegation_record_paths(self.delegation_storage_root):
                record = _validate_record(_read_handoff_record(path), path.stem)
                if record['state'] not in ('ready','cancelled','rejected') and (all_sessions or record['session_id'] == session_id):
                    if record['session_id'] != session_id:
                        raise ValueError('다른 대화 세션의 GPU 양도가 완료되지 않아 시작할 수 없습니다. 해당 세션의 GPU 양도 상태를 확인하세요.')
                    raise ValueError('GPU 양도가 완료되지 않았습니다. 양도 상태를 먼저 확인하세요.')
            return callback()

    def recover_release_observation(self, request_id, expected_revision):
        """접수 전 해제 관측 오류만 확인 후 대기 상태로 되돌린다."""
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if (type(expected_revision) is not int or record['revision'] != expected_revision
                    or record['state'] != 'needs_attention' or record['job_id'] is not None
                    or record['target_status'] is not None
                    or record['reason'] not in ('헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.',
                                                '취소 후 헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.')):
                raise ValueError('복구할 수 있는 GPU 해제 관측 오류가 아닙니다.')
            recovery_state = 'cancel_waiting_release' if record['reason'].startswith('취소 후 ') else 'waiting_release'
            record.update(state=recovery_state, reason=None, uncertain_since=None, revision=record['revision']+1,
                          updated_at=datetime.now(timezone.utc).isoformat())
            write_record_atomically(path, record)
            return dict(record)

    def recover_accepted_submission(self, request_id, expected_revision, job_id):
        """검증된 기존 영수증의 작업만 불확실한 접수에서 다시 추적한다."""
        if not isinstance(job_id, str) or not _ID.fullmatch(job_id):
            raise ValueError('기존 작업 ID 오류')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if (type(expected_revision) is not int or record['revision'] != expected_revision
                    or record['state'] != 'needs_attention' or record['job_id'] is not None
                    or record['target_status'] is not None
                    or record['reason'] != '대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.'):
                raise ValueError('기존 접수를 복구할 수 있는 상태가 아닙니다.')
            record.update(state='running', job_id=job_id, reason=None, uncertain_since=None,
                          revision=record['revision']+1, updated_at=datetime.now(timezone.utc).isoformat())
            write_record_atomically(path, record)
            return dict(record)

    def recover_verified_reload(self, request_id, expected_revision, final_state):
        """이미 준비된 기존 재적재만 확인하고 완료 상태를 복원한다."""
        if final_state not in ('ready', 'cancelled', 'rejected'):
            raise ValueError('재적재 복구 결과 오류')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if (type(expected_revision) is not int or record['revision'] != expected_revision
                    or record['state'] != 'needs_attention'
                    or record['reason'] != '3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.'):
                raise ValueError('재적재 상태를 복구할 수 없습니다.')
            if final_state == 'ready':
                if not record['job_id'] or record['target_status'] not in ('completed','failed','cancelled'):
                    raise ValueError('대상 종료 기록을 확인할 수 없습니다.')
            elif record['job_id'] is not None or record['target_status'] is not None:
                raise ValueError('대상 접수 기록이 복구 결과와 일치하지 않습니다.')
            record.update(state=final_state, reason=None, uncertain_since=None, revision=record['revision']+1,
                          updated_at=datetime.now(timezone.utc).isoformat())
            write_record_atomically(path, record)
            return dict(record)

    def queue_reload_retry(self, request_id, expected_revision, state):
        if state not in ('reload_queued','cancel_reload_queued','rejected_reload_queued'):
            raise ValueError('재적재 재시도 상태 오류')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if (type(expected_revision) is not int or record['revision'] != expected_revision
                    or record['state'] != 'needs_attention' or record['reload_retry'] != 0
                    or record['reason'] != '3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.'):
                raise ValueError('재적재 재시도를 접수할 수 없습니다.')
            if (state == 'reload_queued') != (record['job_id'] is not None and record['target_status'] in ('completed','failed','cancelled')):
                raise ValueError('대상 작업 종료 기록이 일치하지 않습니다.')
            record.update(state=state, reload_retry=1, reason=None, uncertain_since=None,
                          revision=record['revision']+1, updated_at=datetime.now(timezone.utc).isoformat())
            write_record_atomically(path, record)
            return dict(record)

    def record_release_uncertainty(self, request_id, expected_revision, *, uncertain):
        if type(uncertain) is not bool:
            raise ValueError('GPU 해제 관측 상태 오류')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if record['state'] not in ('waiting_release','cancel_waiting_release','reloading','cancel_reloading','rejected_reloading') or record['revision'] != expected_revision:
                raise ValueError('GPU 양도 상태가 변경되었습니다.')
            if uncertain == (record['uncertain_since'] is not None):
                return dict(record)
            now = datetime.now(timezone.utc).isoformat()
            record.update(uncertain_since=now if uncertain else None, revision=record['revision']+1, updated_at=now)
            write_record_atomically(path, record)
            return dict(record)

    def transition(self, request_id, expected_revision, next_state, *, job_id=None, target_status=None, reason=None):
        if type(expected_revision) is not int or expected_revision < 1 or not isinstance(next_state, str) or next_state not in _TRANSITIONS:
            raise ValueError('GPU 양도 전이 형식 오류')
        with self.hold_delegation_storage_lock():
            path = self.resolve_delegation_record_path(request_id)
            record = _validate_record(_read_handoff_record(path), request_id)
            if record['revision'] != expected_revision or next_state not in _TRANSITIONS[record['state']]:
                raise ValueError('GPU 양도 상태가 변경됐거나 허용되지 않은 전이입니다.')
            if next_state == 'running' and (not isinstance(job_id, str) or not _ID.fullmatch(job_id)):
                raise ValueError('확인된 대상 작업 ID가 필요합니다.')
            if next_state == 'reload_queued' and target_status not in ('completed', 'failed', 'cancelled'):
                raise ValueError('대상 작업의 확인된 종료 상태가 필요합니다.')
            if next_state == 'needs_attention' and (not isinstance(reason, str) or not reason.strip() or len(reason) > 500):
                raise ValueError('확인 필요 사유가 필요합니다.')
            if (job_id is not None and next_state != 'running') or (target_status is not None and next_state != 'reload_queued') or (reason is not None and next_state != 'needs_attention'):
                raise ValueError('상태에 맞지 않는 GPU 양도 정보입니다.')
            record.update(state=next_state, revision=record['revision'] + 1, updated_at=datetime.now(timezone.utc).isoformat())
            if job_id is not None: record['job_id'] = job_id
            if target_status is not None: record['target_status'] = target_status
            if reason is not None: record['reason'] = reason
            write_record_atomically(path, record)
            return dict(record)
