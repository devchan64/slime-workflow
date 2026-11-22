"""작가 GPU 양도의 작업공간 고정, 접수 및 종료 관측 계약."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import yaml

from generators.writer_agent.documents import DEFAULT_WORKSPACE_CONFIG, UniqueDocumentLoader, load_workspace_config
from generators.writer_agent.jobs import JOB_IDENTIFIER_PATTERN
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record, check_delegation_record_exists, HermesDelegationStore
from workflow.domains.hermes_agent.gpu_handoff_kimodo import _gpu_idle_fresh, _derived_id
from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock


def _read_bounded_yaml(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1_048_576:
            raise ValueError('작가 설정 또는 상태 파일 오류')
        data = stream.read(1_048_577)
    if len(data) > 1_048_576:
        raise ValueError('작가 설정 또는 상태 크기 초과')
    return data, yaml.load(data, Loader=UniqueDocumentLoader)


def load_writer_workspace_for_binding(config_path=DEFAULT_WORKSPACE_CONFIG):
    """존재하는 설정과 상태 경로만 읽고 정규화된 설정과 지문을 반환한다."""
    config_path = Path(config_path)
    before, raw = _read_bounded_yaml(config_path)
    if not isinstance(raw, dict) or not isinstance(raw.get('state_root'), str):
        raise ValueError('작가 작업공간 설정 오류')
    state_root = Path(raw['state_root'])
    if state_root.is_symlink() or not state_root.is_dir():
        raise ValueError('작가 상태 경로를 확인할 수 없습니다.')
    config = load_workspace_config(config_path)
    after, _ = _read_bounded_yaml(config_path)
    if before != after:
        raise ValueError('작가 작업공간 설정이 조회 중 변경됐습니다.')
    encoded = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return config, hashlib.sha256(encoded).hexdigest()


def current_writer_config_path():
    """현재 작가 서비스가 사용 중인 설정 경로만 관측한다."""
    from workflow.domains.hermes_agent.writer_operations import call_hermes_writer_service
    state = call_hermes_writer_service('writer-state', {})
    if (not isinstance(state, dict) or state.get('configured') is not True
            or not isinstance(state.get('config_path'), str) or not Path(state['config_path']).is_absolute()):
        raise ValueError('작가 서비스의 작업공간 설정을 확인할 수 없습니다.')
    return Path(state['config_path'])


def inspect_writer_workspace(config_path=None):
    """존재하는 설정과 상태 경로만 읽고 정규화된 작업공간 지문을 반환한다."""
    if config_path is None:
        config_path = current_writer_config_path()
    config, fingerprint = load_writer_workspace_for_binding(config_path)
    return {'fingerprint':fingerprint, 'document_root':config['document_root'], 'state_root':config['state_root']}


def inspect_writer_target_release(job_id, expected_status, workspace_fingerprint, *, config_path=None):
    """같은 작업공간의 양쪽 종료 기록과 예약 부재·GPU 유휴를 확인한다."""
    if not isinstance(job_id, str) or not JOB_IDENTIFIER_PATTERN.fullmatch(job_id) or expected_status not in ('completed','failed','cancelled') or not isinstance(workspace_fingerprint, str) or not re.fullmatch(r'[a-f0-9]{64}',workspace_fingerprint):
        return None
    idle = _gpu_idle_fresh()
    if idle is not True:
        return idle
    try:
        check_live_config = config_path is None
        if check_live_config:
            config_path = current_writer_config_path()
        workspace = inspect_writer_workspace(config_path)
        if workspace['fingerprint'] != workspace_fingerprint:
            return None
        root = Path(workspace['state_root']) / 'jobs'
        directory = root / job_id
        if root.is_symlink() or directory.is_symlink() or not directory.is_dir() or directory.resolve().parent != root.resolve():
            return None
        with hold_writer_reservation_queue_lock() as active_root:
            queue_status = read_bounded_delegation_record(directory / 'status.json')
            _, writer_status = _read_bounded_yaml(directory / 'status.yaml')
            accepted_stages = {'completed':('review','completed','applied'), 'failed':('failed',), 'cancelled':('interrupted',)}
            if (not isinstance(queue_status, dict) or queue_status.get('status') != expected_status
                    or not isinstance(writer_status, dict) or writer_status.get('id') != job_id
                    or writer_status.get('stage') not in accepted_stages[expected_status]):
                return None
            for path in active_root.glob('*.json'):
                reservation = read_bounded_delegation_record(path)
                if not isinstance(reservation, dict) or not isinstance(reservation.get('path'), str) or not isinstance(reservation.get('service'), str):
                    return None
                if reservation['path'] == str(directory.resolve()):
                    return False
            if inspect_writer_workspace(config_path)['fingerprint'] != workspace_fingerprint:
                return None
        if check_live_config and current_writer_config_path() != config_path:
            return None
        return True
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError):
        return None


def validate_bound_writer_request(payload):
    """실제 작가 입력과 확인한 작업공간을 함께 검증한다."""
    from workflow.domains.hermes_agent.writer_operations import validate_hermes_writer_request
    if not isinstance(payload, dict) or set(payload) != {'request','workspace_fingerprint'}:
        raise ValueError('작가 GPU 양도 입력 오류')
    if payload['workspace_fingerprint'] != inspect_writer_workspace()['fingerprint']:
        raise ValueError('작가 작업공간이 변경됐습니다. 다시 검토하세요.')
    validate_hermes_writer_request(payload['request'])


def ensure_writer_target_unclaimed(request_id, store=None):
    """호출자는 양도 잠금을 보유한다. 이미 접수됐거나 불확실한 요청은 양도하지 않는다."""
    store=store or HermesDelegationStore()
    with store.hold_delegation_storage_lock():
        path=store.resolve_delegation_record_path(_derived_id('handoff_',request_id))
        if check_delegation_record_exists(path):
            raise ValueError('같은 작가 제안의 접수 기록이 있습니다. 기존 상태를 확인하세요.')


def submit_bound_writer_once(request_id,session_id,payload,*,handoff_store=None,delegation_store=None,submit=None,validate=None,preflight=None):
    """양도 승인과 동일한 잠금 순서로 직접 접수를 단 한 번 기록한다."""
    from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
    from workflow.domains.hermes_agent.writer_operations import call_hermes_writer_service
    handoff_store=handoff_store or GpuHandoffStore()
    delegation_store=delegation_store or HermesDelegationStore()
    submit=submit or (lambda value:call_hermes_writer_service('writer-submit-bound',value))
    validate=validate or validate_bound_writer_request
    def dispatch():
        if preflight:preflight()
        return delegation_store.execute_service_delegation_once(_derived_id('handoff_',request_id),'writer-agent',payload,submit,validate,record_validation_rejection=True)
    return handoff_store.run_without_open_session_handoff(session_id,dispatch)


class WriterHandoffAdapter(FluxHandoffAdapter):
    """고정된 작업공간의 작가 접수와 GPU 종료를 관측한다."""
    def target_request_id(self, record):
        return _derived_id('handoff_', record['id'])

    def validate_service(self, service):
        if service != 'writer-agent':
            raise ValueError('작가 양도 서비스 오류')

    def submit_target(self, record):
        from workflow.domains.hermes_agent.writer_operations import call_hermes_writer_service
        self.validate_service(record['service'])
        self.store.execute_service_delegation_once(_derived_id('handoff_',record['id']), 'writer-agent', record['target_request'],
            lambda payload:call_hermes_writer_service('writer-submit-bound',payload), validate_bound_writer_request, record_validation_rejection=True)
        return self.lookup_target(record)

    def inspect_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            return {'state':'unknown'}
        response = self.gateway('hermes-writer-status', {'request_id':_derived_id('handoff_',record['id'])})
        if not isinstance(response, dict) or not isinstance(response.get('receipt'), dict) or not isinstance(response.get('job'), dict):
            return {'state':'unknown'}
        observed, job = response['receipt'], response['job']
        if observed.get('state') != 'accepted' or observed.get('service') != 'writer-agent' or observed.get('job_id') != record['job_id']:
            return {'state':'unknown'}
        stage = job.get('stage')
        status = 'queued' if stage == 'queued' else 'running' if stage in ('preparing','indexing','searching','reasoning') else 'completed' if stage in ('review','completed','applied') else 'failed' if stage == 'failed' else 'cancelled' if stage == 'interrupted' else 'unknown'
        result = {'service':'writer-agent','job_id':record['job_id'],'status':status}
        if status in ('completed','failed','cancelled'):
            result['reservation_released'] = inspect_writer_target_release(record['job_id'],status,record['target_request']['workspace_fingerprint'])
        return result

    def cancel_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            raise ValueError('중지할 작가 작업의 접수 기록을 확인할 수 없습니다.')
        response = self.gateway('hermes-writer-cancel', {'request_id':_derived_id('handoff_',record['id']),'job_id':record['job_id']})
        if not isinstance(response, dict) or response.get('job_id') != record['job_id'] or response.get('cancel_requested') is not True:
            raise ValueError('작가 작업 중지 요청을 확인할 수 없습니다.')
        return response
