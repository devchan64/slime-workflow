"""확인된 관측과 기존 서비스 어댑터를 사용해 GPU 양도를 한 단계 진행한다.

어댑터는 실제 소유권·예약·서비스 영수증을 검증해야 한다. 이 모듈만으로
GPU 작업이 접수되거나 모델이 상주하지 않는다.
"""
import fcntl
import os
import stat
from contextlib import contextmanager
from datetime import datetime, timezone

from .gpu_handoff_store import GpuHandoffStore


@contextmanager
def _hold_handoff_execution(store, request_id):
    # The receipt lock cannot be held across a call back into the receipt store.
    store.resolve_delegation_record_path(request_id)
    root = store.delegation_storage_root
    if root.is_symlink():
        raise ValueError('GPU 양도 잠금 경로 오류')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(root / (request_id + '.execution.lock'), os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ValueError('GPU 양도 잠금 형식 오류')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def _attention(store, record, reason):
    return store.transition(record['id'], record['revision'], 'needs_attention', reason=reason)


def _accepted_job(result, record):
    if (not isinstance(result, dict) or result.get('state') != 'accepted'
            or result.get('service') != record['service'] or result.get('input_digest') != record['input_digest']):
        raise ValueError('대상 접수 또는 입력 지문을 확인할 수 없습니다.')
    return result.get('job_id')


def advance_gpu_handoff(store: GpuHandoffStore, request_id, adapter):
    """한 요청만 처리한다. 부작용 직전 상태를 기록하고 불명확하면 재접수하지 않는다."""
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            return {'state':'in_progress'}
        record = store.read(request_id)
        if record is None:
            raise ValueError('승인된 GPU 양도 요청이 없습니다.')
        state = record['state']
        if state == 'approved':
            return store.transition(request_id, record['revision'], 'waiting_release')
        if state in ('waiting_release','cancel_waiting_release'):
            # 재시작 시에도 동일한 상주 작업에만 안전하게 반복할 수 있어야 한다.
            adapter.ensure_release_requested(record)
            release = adapter.inspect_release(record)
            if release == 'waiting':
                return store.record_release_uncertainty(request_id, record['revision'], uncertain=False)
            if release != 'released':
                record = store.record_release_uncertainty(request_id, record['revision'], uncertain=True)
                try:
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(record['uncertain_since'])).total_seconds()
                except (ValueError, TypeError):
                    elapsed = 31
                if 0 <= elapsed < 30:
                    return record
                reason = '취소 후 헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.' if state == 'cancel_waiting_release' else '헤르메스 종료와 GPU 예약 해제를 확인할 수 없습니다.'
                return _attention(store, record, reason)
            record = store.record_release_uncertainty(request_id, record['revision'], uncertain=False)
            if state == 'cancel_waiting_release':
                return store.transition(request_id, record['revision'], 'cancel_reload_queued')
            record = store.transition(request_id, record['revision'], 'submitting')
            # An interrupted or failed call leaves 'submitting' for receipt lookup.
            try:
                result = adapter.submit_target(record)
            except ValueError:
                if getattr(adapter, 'seal_unsubmitted_target', lambda _: False)(record):
                    return store.transition(request_id, record['revision'], 'rejected_reload_queued')
                return _attention(store, record, '대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            if isinstance(result, dict) and result.get('state') == 'rejected' and result.get('service') == record['service'] and result.get('input_digest') == record['input_digest']:
                return store.transition(request_id, record['revision'], 'rejected_reload_queued')
            job_id = _accepted_job(result, record)
            return store.transition(request_id, record['revision'], 'running', job_id=job_id)
        if state == 'submitting':
            result = adapter.lookup_target(record)
            if isinstance(result, dict) and result.get('state') == 'not_found':
                # 위임 저장소는 부작용 전에 동일 ID의 dispatching 영수증을 잠금 안에 기록한다.
                # 영수증이 없다면 중단된 호출을 같은 ID로 재개해도 중복 접수되지 않는다.
                try:
                    result = adapter.submit_target(record)
                except ValueError:
                    if getattr(adapter, 'seal_unsubmitted_target', lambda _: False)(record):
                        return store.transition(request_id, record['revision'], 'rejected_reload_queued')
                    return _attention(store, record, '대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            if isinstance(result, dict) and result.get('state') == 'rejected' and result.get('service') == record['service'] and result.get('input_digest') == record['input_digest']:
                return store.transition(request_id, record['revision'], 'rejected_reload_queued')
            try:
                job_id = _accepted_job(result, record)
            except ValueError:
                return _attention(store, record, '대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            return store.transition(request_id, record['revision'], 'running', job_id=job_id)
        if state == 'running':
            result = adapter.inspect_target(record)
            if not isinstance(result, dict) or result.get('job_id') != record['job_id'] or result.get('service') != record['service']:
                return _attention(store, record, '대상 작업의 신원을 확인할 수 없습니다.')
            status = result.get('status')
            if status in ('queued', 'running', 'paused'):
                return record
            if status in ('completed', 'failed', 'cancelled') and result.get('reservation_released') is False:
                return record
            if status not in ('completed', 'failed', 'cancelled') or result.get('reservation_released') is not True:
                return _attention(store, record, '대상 종료 또는 GPU 예약 해제를 확인할 수 없습니다.')
            return store.transition(request_id, record['revision'], 'reload_queued', target_status=status)
        if state in ('reload_queued', 'cancel_reload_queued', 'rejected_reload_queued'):
            next_state = {'cancel_reload_queued':'cancel_reloading', 'rejected_reload_queued':'rejected_reloading'}.get(state, 'reloading')
            record = store.transition(request_id, record['revision'], next_state)
            # The adapter must enqueue one idempotent reload using this request ID.
            adapter.submit_reload(record)
            return record
        if state in ('reloading','cancel_reloading','rejected_reloading'):
            result = adapter.inspect_reload(record)
            if isinstance(result, dict) and result.get('state') == 'not_found':
                # 상태 기록 직후 프로세스가 중단됐을 수 있다. 이 접수는 동일 ID로 멱등이어야 한다.
                adapter.submit_reload(record)
                return record
            if isinstance(result, dict) and result.get('state') in ('queued', 'running'):
                return store.record_release_uncertainty(request_id, record['revision'], uncertain=False)
            if (not isinstance(result, dict) or result.get('state') != 'ready' or result.get('model') != record['model']
                    or result.get('gpu_loaded') is not True or result.get('reservation_verified') is not True):
                if isinstance(result, dict) and result.get('state') == 'unknown':
                    record = store.record_release_uncertainty(request_id, record['revision'], uncertain=True)
                    try:
                        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(record['uncertain_since'])).total_seconds()
                    except (ValueError, TypeError):
                        elapsed = 31
                    if 0 <= elapsed < 30:
                        return record
                return _attention(store, record, '3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.')
            record = store.record_release_uncertainty(request_id, record['revision'], uncertain=False)
            return store.transition(request_id, record['revision'], {'cancel_reloading':'cancelled', 'rejected_reloading':'rejected'}.get(state, 'ready'))
        return record


def retry_failed_reload(store, request_id, session_id, expected_revision, adapter, *, confirmed):
    """실패한 원 재적재의 정리가 확인된 경우 같은 승인 아래 한 번 재시도한다."""
    if confirmed is not True:
        raise ValueError('재적재 재시도를 명시적으로 확인해야 합니다.')
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            raise ValueError('GPU 양도 처리가 진행 중입니다. 다시 확인하세요.')
        record = store.read(request_id)
        if record is None or record['session_id'] != session_id or record['revision'] != expected_revision:
            raise ValueError('GPU 양도 기록이나 세션이 변경되었습니다.')
        if record['state'] != 'needs_attention' or record['reason'] != '3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.' or record['reload_retry'] != 0:
            raise ValueError('재적재 재시도를 접수할 수 없습니다.')
        if adapter.inspect_failed_reload_cleanup(record) is not True:
            raise ValueError('실패한 재적재 작업의 종료와 GPU 정리를 확인할 수 없습니다.')
        if record['job_id'] is not None:
            state = 'reload_queued'
        else:
            receipt = adapter.lookup_target(record)
            if not isinstance(receipt, dict) or receipt.get('state') not in ('rejected','not_found'):
                raise ValueError('대상 미접수 여부를 확인할 수 없습니다.')
            if receipt['state'] == 'rejected' and (receipt.get('service') != record['service'] or receipt.get('input_digest') != record['input_digest']):
                raise ValueError('대상 거부 영수증이 확인한 요청과 일치하지 않습니다.')
            state = 'rejected_reload_queued' if receipt['state'] == 'rejected' else 'cancel_reload_queued'
        return store.queue_reload_retry(request_id, expected_revision, state)


def recover_verified_reload(store, request_id, session_id, expected_revision, adapter, *, confirmed):
    """기존 재적재가 준비된 경우에만 상태를 복구한다. 새 작업은 접수하지 않는다."""
    if confirmed is not True:
        raise ValueError('기존 재적재 상태를 다시 확인해야 합니다.')
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            raise ValueError('GPU 양도 처리가 진행 중입니다. 다시 확인하세요.')
        record = store.read(request_id)
        if record is None or record['session_id'] != session_id or record['revision'] != expected_revision:
            raise ValueError('GPU 양도 기록이나 세션이 변경되었습니다.')
        if record['state'] != 'needs_attention' or record['reason'] != '3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.':
            raise ValueError('재적재 상태를 복구할 수 없습니다.')
        result = adapter.inspect_reload(record)
        if (not isinstance(result, dict) or result.get('state') != 'ready' or result.get('model') != record['model']
                or result.get('gpu_loaded') is not True or result.get('reservation_verified') is not True):
            raise ValueError('기존 Qwen 3.8 재적재와 GPU 예약이 아직 확인되지 않습니다.')
        if record['job_id'] is not None:
            final = 'ready'
        else:
            receipt = adapter.lookup_target(record)
            if not isinstance(receipt, dict) or receipt.get('state') not in ('rejected','not_found'):
                raise ValueError('대상 미접수 여부를 확인할 수 없습니다.')
            if receipt['state'] == 'rejected' and (receipt.get('service') != record['service'] or receipt.get('input_digest') != record['input_digest']):
                raise ValueError('대상 거부 영수증이 확인한 요청과 일치하지 않습니다.')
            final = 'rejected' if receipt['state'] == 'rejected' else 'cancelled'
        return store.recover_verified_reload(request_id, expected_revision, final)


def recover_release_observation(store, request_id, session_id, expected_revision, adapter, *, confirmed):
    """대상 미접수와 상주 서버 해제를 모두 확인한 뒤 기존 승인만 이어간다."""
    if confirmed is not True:
        raise ValueError('기존 생성 요청을 계속할지 명시적으로 확인해야 합니다.')
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            raise ValueError('GPU 양도 처리가 진행 중입니다. 다시 확인하세요.')
        record = store.read(request_id)
        if record is None or record['session_id'] != session_id or record['revision'] != expected_revision:
            raise ValueError('GPU 양도 기록이나 세션이 변경되었습니다.')
        if adapter.inspect_release(record) != 'released':
            raise ValueError('상주 모델의 종료와 예약 해제를 확인할 수 없습니다.')
        receipt = adapter.lookup_target(record)
        if not isinstance(receipt, dict) or receipt.get('state') != 'not_found':
            raise ValueError('대상 생성 접수 여부가 불명확하여 자동으로 계속하지 않습니다.')
        return store.recover_release_observation(request_id, expected_revision)


def recover_accepted_submission(store, request_id, session_id, expected_revision, adapter, *, confirmed):
    """접수된 동일 입력의 영수증을 재확인하고 기존 작업만 추적한다."""
    if confirmed is not True:
        raise ValueError('기존 생성 작업 추적을 명시적으로 확인해야 합니다.')
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            raise ValueError('GPU 양도 처리가 진행 중입니다. 다시 확인하세요.')
        record = store.read(request_id)
        if record is None or record['session_id'] != session_id or record['revision'] != expected_revision:
            raise ValueError('GPU 양도 기록이나 세션이 변경되었습니다.')
        if record['state'] != 'needs_attention' or record['reason'] != '대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.':
            raise ValueError('기존 접수를 복구할 수 있는 상태가 아닙니다.')
        job_id = _accepted_job(adapter.lookup_target(record), record)
        return store.recover_accepted_submission(request_id, expected_revision, job_id)


def cancel_handoff(store, request_id, session_id, expected_revision, adapter, *, confirmed):
    """승인된 대상만 중지하고 모델 복구는 완료될 때까지 유지한다."""
    if confirmed is not True:
        raise ValueError('생성 요청 중지와 Qwen 3.8 재적재를 명시적으로 확인해야 합니다.')
    with _hold_handoff_execution(store, request_id) as acquired:
        if not acquired:
            raise ValueError('GPU 양도 처리가 진행 중입니다. 다시 확인하세요.')
        record = store.read(request_id)
        if record is None or record['session_id'] != session_id or record['revision'] != expected_revision:
            raise ValueError('GPU 양도 기록이나 세션이 변경되었습니다.')
        if record['state'] == 'approved':
            return store.transition(request_id, expected_revision, 'cancelled')
        if record['state'] == 'waiting_release':
            return store.transition(request_id, expected_revision, 'cancel_waiting_release')
        if record['state'] == 'running':
            response = adapter.cancel_target(record)
            return {'state':'running','id':request_id,'session_id':session_id,'service':record['service'],'job_id':record['job_id'],
                    'revision':expected_revision,'cancel_requested':response.get('cancel_requested') is True}
        raise ValueError('이 단계에서는 중지할 수 없습니다. 현재 상태를 다시 확인하세요.')
