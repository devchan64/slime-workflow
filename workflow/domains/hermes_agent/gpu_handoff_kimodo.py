"""승인된 Kimodo 작업과 상주 모델 양도를 기존 접수·예약에 연결한다."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from workflow.domains.hermes_agent.delegation_store import (
    HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record,
)
from workflow.domains.hermes_agent.resident_queue import (
    enqueue_resident_once, inspect_resident, request_resident_release,
)
from workflow.domains.hermes_agent.workflow_dispatch import call_workflow_management_command
from workflow.common.generation_records import write_record_atomically


def _derived_id(prefix, request_id):
    return prefix + hashlib.sha256(request_id.encode('utf-8')).hexdigest()


def _target_receipt(store, record):
    """원 접수 기록의 서비스·입력 해시까지 대조한다."""
    request_id = _derived_id('handoff_', record['id'])
    expected = {'service':'kimodo', 'request':record['target_request']}
    payload = json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    digest = hashlib.sha256(payload).hexdigest()
    with store.hold_delegation_storage_lock():
        path = store.resolve_delegation_record_path(request_id)
        if not check_delegation_record_exists(path):
            return {'state':'not_found'}
        receipt = read_bounded_delegation_record(path)
        if (not isinstance(receipt, dict) or receipt.get('version') != 1 or receipt.get('id') != request_id
                or receipt.get('request_sha256') != digest or receipt.get('state') not in ('dispatching', 'accepted', 'rejected')):
            return {'state':'unknown'}
        if receipt['state'] == 'rejected':
            return {'state':'rejected','service':'kimodo','input_digest':record['input_digest']}
        if receipt['state'] != 'accepted':
            return {'state':'unknown'}
        job_id = receipt.get('job_id')
        if not isinstance(job_id, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', job_id):
            return {'state':'unknown'}
        return {'state':'accepted','service':'kimodo','input_digest':record['input_digest'],'job_id':job_id}


def _gpu_idle_fresh():
    """캐시 없이 장치별 GPU 프로세스 관측이 완전히 비었을 때만 True."""
    try:
        result = subprocess.run(['amd-smi', 'process', '--json'], capture_output=True, text=True, timeout=10, check=True)
        devices = json.loads(result.stdout)
        if not isinstance(devices, list) or not devices:
            return None
        for device in devices:
            if not isinstance(device, dict) or not isinstance(device.get('process_list'), list):
                return None
            for item in device['process_list']:
                if not isinstance(item, dict) or 'process_info' not in item:
                    return None
                if item['process_info'] != 'No running processes detected':
                    return False
        return True
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return None


def inspect_target_release(job_root, job_id, expected_status):
    """대상 종료, 실제 GPU 유휴 및 대상 예약 부재를 확인한다."""
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    if not isinstance(job_id, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', job_id):
        return None
    idle = _gpu_idle_fresh()
    if idle is not True:
        return idle
    try:
        root = Path(job_root)
        directory = root / job_id
        if root.is_symlink() or directory.is_symlink() or not directory.is_dir():
            return None
        with hold_writer_reservation_queue_lock() as active_root:
            status = read_bounded_delegation_record(directory / 'status.json')
            if not isinstance(status, dict) or status.get('status') != expected_status:
                return None
            for path in active_root.glob('*.json'):
                reservation = read_bounded_delegation_record(path)
                if not isinstance(reservation, dict) or not isinstance(reservation.get('path'), str) or not isinstance(reservation.get('service'), str):
                    return None
                if reservation['path'] == str(directory.resolve()):
                    return False
            return True
    except (OSError, ValueError, TypeError):
        return None


def inspect_kimodo_release(job_id, expected_status):
    from generators.kimodo.contracts import KIMODO_JOB_STORAGE
    return inspect_target_release(KIMODO_JOB_STORAGE, job_id, expected_status)


class KimodoHandoffAdapter:
    """기존 Kimodo 명령과 상주 모델 관리 함수를 사용하는 어댑터."""
    def __init__(self, *, gateway=call_workflow_management_command, delegation_store=None,
                 resident_root=None, release_observer=inspect_kimodo_release):
        self.gateway = gateway
        self.store = delegation_store or HermesDelegationStore()
        self.resident_options = {} if resident_root is None else {'root':resident_root}
        self.release_observer = release_observer

    def _resident(self, record, identifier):
        return inspect_resident(identifier, record['session_id'], **self.resident_options)

    def ensure_release_requested(self, record):
        state = self._resident(record, record['resident_id']).get('state')
        if state == 'ready':
            request_resident_release(record['resident_id'], record['session_id'], **self.resident_options)
        elif state not in ('running', 'queued', 'released', 'unknown', 'not_found'):
            raise ValueError('해제할 상주 모델 상태를 확인할 수 없습니다.')

    def inspect_release(self, record):
        state = self._resident(record, record['resident_id']).get('state')
        return 'released' if state == 'released' else 'waiting' if state in ('ready', 'running', 'queued') else 'unknown'

    def submit_target(self, record):
        if record['service'] != 'kimodo':
            raise ValueError('지원하지 않는 GPU 양도 대상입니다.')
        self.gateway('hermes-delegate-kimodo', {'request_id':_derived_id('handoff_', record['id']), 'request':record['target_request']})
        return _target_receipt(self.store, record)

    def lookup_target(self, record):
        return _target_receipt(self.store, record)

    def seal_unsubmitted_target(self, record):
        """접수 영수증이 없을 때 같은 잠금에서 영구 거부 기록을 만든다."""
        request_id = _derived_id('handoff_', record['id'])
        payload = {'service':'kimodo', 'request':record['target_request']}
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        with self.store.hold_delegation_storage_lock():
            path = self.store.resolve_delegation_record_path(request_id)
            if check_delegation_record_exists(path):
                return False
            write_record_atomically(path, {'version':1, 'id':request_id, 'request_sha256':digest, 'state':'rejected'})
            return True

    def inspect_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            return {'state':'unknown'}
        response = self.gateway('hermes-delegation-job-status', {'request_id':_derived_id('handoff_', record['id'])})
        if not isinstance(response, dict) or not isinstance(response.get('receipt'), dict) or not isinstance(response.get('job'), dict):
            return {'state':'unknown'}
        observed_receipt, job = response['receipt'], response['job']
        if (observed_receipt.get('state') != 'accepted' or observed_receipt.get('service') != 'kimodo'
                or observed_receipt.get('job_id') != record['job_id'] or job.get('id', record['job_id']) != record['job_id']):
            return {'state':'unknown'}
        status = job.get('status')
        result = {'service':'kimodo', 'job_id':record['job_id'], 'status':status}
        if status in ('completed', 'failed', 'cancelled'):
            result['reservation_released'] = self.release_observer(record['job_id'], status)
        return result

    def cancel_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            raise ValueError('중지할 생성 작업의 접수 기록을 확인할 수 없습니다.')
        result = self.gateway('hermes-delegation-cancel', {'request_id':_derived_id('handoff_', record['id']), 'job_id':record['job_id']})
        if not isinstance(result, dict) or result.get('job_id') != record['job_id'] or result.get('cancel_requested') is not True:
            raise ValueError('생성 작업 중지 요청을 확인할 수 없습니다.')
        return result

    def submit_reload(self, record):
        original = _derived_id('reload_', record['id'])
        if record.get('reload_retry', 0) == 1:
            return enqueue_resident_once(_derived_id('retry_', record['id']), record['session_id'], recovered_failure_id=original, **self.resident_options)
        return enqueue_resident_once(original, record['session_id'], **self.resident_options)

    def inspect_reload(self, record):
        result = self._resident(record, _derived_id('retry_' if record.get('reload_retry', 0) == 1 else 'reload_', record['id']))
        if record.get('reload_retry', 0) == 1 and result.get('state') == 'ready':
            # 접수 완료 후 연결 기록을 쓰기 전에 중단됐으면 동일 접수만 재확인해 복원한다.
            self.submit_reload(record)
        return result

    def inspect_failed_reload_cleanup(self, record):
        from workflow.domains.hermes_agent.resident_queue import inspect_failed_resident_cleanup
        return inspect_failed_resident_cleanup(_derived_id('reload_', record['id']), record['session_id'], **self.resident_options)
