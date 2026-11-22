"""FLUX 프로필의 기존 접수 영수증을 GPU 양도에 연결한다."""
import hashlib
import json
import re

from workflow.domains.hermes_agent.delegation_store import check_delegation_record_exists, read_bounded_delegation_record, validate_service_job_identifier
from workflow.domains.hermes_agent.flux_profile_operations import validate_hermes_flux_profile
from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter, _derived_id, inspect_target_release
from workflow.common.generation_records import write_record_atomically


def inspect_flux_release(service, job_id, expected_status):
    validate_hermes_flux_profile(service)
    if service == 'flux-expression':
        from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        root = FluxExpressionGenerationManager().job_storage_root
    else:
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        root = FluxImageGenerationManager(service).job_storage_root
    return inspect_target_release(root, job_id, expected_status)


class FluxHandoffAdapter(KimodoHandoffAdapter):
    def __init__(self, *, release_observer=inspect_flux_release, **kwargs):
        super().__init__(**kwargs)
        self.flux_release_observer = release_observer

    def validate_service(self, service):
        validate_hermes_flux_profile(service)

    def target_request_id(self, record):
        # Proposal IDs are shared with direct submission; older handoffs retain
        # their original derived ID so existing receipts stay readable.
        identifier = record['id']
        return identifier if re.fullmatch(r'flux_[a-f0-9]{64}', identifier) else _derived_id('handoff_', identifier)

    def lookup_target(self, record):
        service = record['service']
        self.validate_service(service)
        request_id = self.target_request_id(record)
        data = json.dumps({'service':service, 'request':record['target_request']}, ensure_ascii=False,
                          sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        with self.store.hold_delegation_storage_lock():
            path = self.store.resolve_delegation_record_path(request_id)
            if not check_delegation_record_exists(path):
                return {'state':'not_found'}
            receipt = read_bounded_delegation_record(path)
            if (isinstance(receipt, dict) and receipt.get('version') == 2 and receipt.get('id') == request_id
                    and receipt.get('service') == service and receipt.get('request_sha256') == digest
                    and receipt.get('state') == 'rejected'):
                return {'state':'rejected', 'service':service, 'input_digest':record['input_digest']}
            if (not isinstance(receipt, dict) or receipt.get('version') != 2 or receipt.get('id') != request_id
                    or receipt.get('service') != service or receipt.get('request_sha256') != digest
                    or receipt.get('state') != 'accepted' or not validate_service_job_identifier(service, receipt.get('job_id'))):
                return {'state':'unknown'}
            return {'state':'accepted','service':service,'input_digest':record['input_digest'],'job_id':receipt['job_id']}

    def seal_unsubmitted_target(self, record):
        service = record['service']
        self.validate_service(service)
        request_id = self.target_request_id(record)
        data = json.dumps({'service':service, 'request':record['target_request']}, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        with self.store.hold_delegation_storage_lock():
            path = self.store.resolve_delegation_record_path(request_id)
            if check_delegation_record_exists(path):
                return False
            write_record_atomically(path, {'version':2, 'id':request_id, 'service':service, 'request_sha256':digest, 'state':'rejected'})
            return True

    def submit_target(self, record):
        self.validate_service(record['service'])
        self.gateway('hermes-delegate-flux-profile', {'request_id':self.target_request_id(record),
                     'service':record['service'], 'request':record['target_request']})
        return self.lookup_target(record)

    def inspect_target(self, record):
        service = record['service']
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            return {'state':'unknown'}
        response = self.gateway('hermes-flux-profile-status', {'request_id':self.target_request_id(record), 'service':service})
        if not isinstance(response, dict) or not isinstance(response.get('receipt'), dict) or not isinstance(response.get('job'), dict):
            return {'state':'unknown'}
        observed, job = response['receipt'], response['job']
        if (observed.get('state') != 'accepted' or observed.get('service') != service or observed.get('job_id') != record['job_id']
                or job.get('id', record['job_id']) != record['job_id']):
            return {'state':'unknown'}
        status = job.get('status')
        result = {'service':service, 'job_id':record['job_id'], 'status':status}
        if status in ('completed','failed','cancelled'):
            result['reservation_released'] = self.flux_release_observer(service, record['job_id'], status)
        return result

    def cancel_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            raise ValueError('중지할 FLUX 작업의 접수 기록을 확인할 수 없습니다.')
        result = self.gateway('hermes-flux-profile-cancel', {'request_id':self.target_request_id(record),
                              'service':record['service'], 'job_id':record['job_id']})
        if not isinstance(result, dict) or result.get('job_id') != record['job_id'] or result.get('cancel_requested') is not True:
            raise ValueError('FLUX 작업 중지 요청을 확인할 수 없습니다.')
        return result
