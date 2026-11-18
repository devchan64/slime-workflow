"""FLUX 프로필별 이미지 작업을 기존 검증·GPU 대기열에 위임한다."""
import os
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason
from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS


def validate_hermes_flux_profile(current_profile_name):
    if not isinstance(current_profile_name,str) or current_profile_name not in (*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression'):
        raise ValueError('등록된 FLUX 이미지 프로필이 아닙니다.')


def call_hermes_flux_profile(current_profile_name,current_command_name,current_payload_record):
    validate_hermes_flux_profile(current_profile_name)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command(current_profile_name,current_command_name,current_payload_record,current_gateway_address)


def submit_hermes_flux_profile(current_request_identifier,current_profile_name,current_request_record):
    from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
    from tools.review.domains.image.flux_expression_generation import FluxExpressionGenerationManager
    validate_hermes_flux_profile(current_profile_name)
    current_manager_value=FluxExpressionGenerationManager() if current_profile_name=='flux-expression' else FluxImageGenerationManager(current_profile_name)
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,current_profile_name,current_request_record,
        lambda current_request_value:call_hermes_flux_profile(current_profile_name,'generate',current_request_value),
        current_manager_value.validate_generation_request)


def inspect_hermes_flux_result(current_profile_name,current_job_identifier,current_job_value):
    """기존 상태 응답을 바꾸지 않고 동일 서비스·작업의 완료 이미지 경로만 확인한다."""
    validate_hermes_flux_profile(current_profile_name)
    if not isinstance(current_job_value,dict) or ('id' in current_job_value and current_job_value['id']!=current_job_identifier):
        raise ValueError('FLUX 작업 상태 응답 또는 작업 ID 오류')
    current_expected_path='/'+current_profile_name+'-generator/jobs/'+current_job_identifier+'/result.png'
    current_completed_value=current_job_value.get('status')=='completed'
    current_result_path=current_expected_path if current_completed_value and current_job_value.get('image')==current_expected_path else None
    return {'image':current_result_path,'status':'available' if current_result_path else 'unavailable' if current_completed_value else 'not_ready'}


def read_hermes_flux_profile_status(current_request_identifier,current_profile_name):
    validate_hermes_flux_profile(current_profile_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_profile_name)
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    current_job_value=call_hermes_flux_profile(current_profile_name,'status',{'id':current_receipt_value['job_id']})
    if not isinstance(current_job_value,dict):
        raise ValueError('FLUX 작업 상태 응답 형식 오류')
    current_status_value=current_job_value.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):
        current_status_value='unknown'
    current_result_record=inspect_hermes_flux_result(current_profile_name,current_receipt_value['job_id'],current_job_value)
    current_result_path=current_result_record['image']
    current_result_status=current_result_record['status']
    return {'receipt':current_receipt_value,'job':{'status':current_status_value,'image':current_result_path,'result_status':current_result_status,'note':'상세 로그와 다른 결과는 해당 생성기 화면에서 확인하세요. 생성 이미지는 자동으로 에셋에 등록되지 않습니다.', **observe_hermes_failure_reason(current_status_value,current_job_value.get('error'))}}


def list_hermes_flux_profile_receipts(current_profile_name):
    validate_hermes_flux_profile(current_profile_name)
    return HermesDelegationStore().list_service_delegations(current_profile_name)


def cancel_hermes_flux_profile(current_request_identifier,current_profile_name,current_job_identifier):
    validate_hermes_flux_profile(current_profile_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_profile_name)
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('접수 기록과 확인한 생성기 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_flux_profile(current_profile_name,'cancel',{'id':current_job_identifier})
    if not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True:
        raise ValueError('중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}
