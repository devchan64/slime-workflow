"""Run a confirmed revision of the MiniMax image form after resident release."""
from .gpu_handoff_flux import FluxHandoffAdapter
from .gpu_handoff_kimodo import inspect_target_release
from .flux_reports import proposal_request_id
from .minimax_form_store import MiniMaxFormStore
from .session_store import HermesSessionStore
from generators.minimax_h3_image.contracts import STORAGE, validate_request


def verify_form(session, target):
    if set(target) != {'form_id', 'revision', 'request'}:
        raise ValueError('MiniMax 이미지 폼 버전을 확인하세요.')
    forms = MiniMaxFormStore(HermesSessionStore().session_storage_root/'minimax-forms.sqlite3')
    form = forms.read(session, target['form_id'])
    if form['service']!='minimax-h3-image' or form['revision']!=target['revision'] or form['request']!=target['request']:
        raise ValueError('승인 대상 이미지 폼이 변경되었습니다.')
    validate_request(form['request'])
    return proposal_request_id(session, form['source_job_id'], form['service'])


class MiniMaxImageHandoff(FluxHandoffAdapter):
    def validate_service(self, service):
        if service != 'minimax-h3-image':
            raise ValueError('MiniMax 이미지 서비스 오류')

    def generation_input(self, record):
        return record['target_request']['request']

    def submit_target(self, record):
        target = record['target_request']
        session = record['session_id']
        if verify_form(session, target) != record['id']:
            raise ValueError('이미지 제안 접수 ID 불일치')
        self.gateway('hermes-minimax-form-submit', dict(session_id=session, form_id=target['form_id'], revision=target['revision']))
        return self.lookup_target(record)

    def inspect_target(self, record):
        import json
        job = record['job_id']
        if self.lookup_target(record).get('job_id') != job:
            return {'state':'unknown'}
        HermesSessionStore().append_result_notice(record['session_id'], 'queued_'+record['id'],
                                                 f'{record["service"]} 이미지 생성 대기열에 등록했습니다. 작업 ID: {job}')
        status = json.loads((STORAGE/job/'status.json').read_text())['status']
        result = dict(service=record['service'],job_id=job,status=status)
        if status in ('completed','failed','cancelled'):
            result['reservation_released'] = inspect_target_release(STORAGE,job,status)
        return result

    def cancel_target(self, record):
        from workflow.common.management_gateway import execute_management_command
        from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
        import os
        if self.lookup_target(record).get('job_id') != record['job_id']:
            raise ValueError('MiniMax 작업 ID 불일치')
        address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        return execute_management_command(record['service'],'cancel',{'id':record['job_id']},address)
