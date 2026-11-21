"""FLUX 원 서비스의 재개 예비 검토를 Hermes에서 확인한다."""
import re
from workflow.common.management_client import execute_remote_management_command
from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier


def preview_hermes_flux_resume(current_service_name,current_job_identifier):
    from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if not isinstance(current_service_name,str) or current_service_name not in FLUX_IMAGE_PROFILE_RECORDS or not validate_service_job_identifier(current_service_name,current_job_identifier):
        raise ValueError('FLUX 재개 검토 대상 오류')
    current_preview_value=execute_remote_management_command(current_service_name,'resume-preview',{'id':current_job_identifier})
    if (not isinstance(current_preview_value,dict) or current_preview_value.get('service')!=current_service_name or current_preview_value.get('id')!=current_job_identifier
            or current_preview_value.get('status') not in ('failed','cancelled','paused')
            or not isinstance(current_preview_value.get('expected_resume_fingerprint'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_preview_value['expected_resume_fingerprint'])):
        raise ValueError('FLUX 재개 검토 응답 오류')
    current_availability_value=current_preview_value.get('resume_availability','unknown')
    if current_availability_value not in ('available','download_running','unknown'):raise ValueError('FLUX 재개 가능 상태 오류')
    return {'service':current_service_name,'job_id':current_job_identifier,'status':current_preview_value['status'],'expected_resume_fingerprint':current_preview_value['expected_resume_fingerprint'],'resume_availability':current_availability_value,'note':'저장 요청과 참조·모델 준비 충돌의 검토 시점 결과입니다. GPU 가용성은 별도입니다.'}


from pathlib import Path
FLUX_RESUME_RECEIPT_ROOT=Path(__file__).resolve().parents[3]/'.local/hermes-agent/flux-resume-receipts'


def validate_flux_resume_target(current_service_name,current_job_identifier,current_fingerprint_value=None):
    from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if not isinstance(current_service_name,str) or current_service_name not in FLUX_IMAGE_PROFILE_RECORDS or not validate_service_job_identifier(current_service_name,current_job_identifier):
        raise ValueError('FLUX 재개 대상 오류')
    if current_fingerprint_value is not None and (not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value)):
        raise ValueError('FLUX 재개 확인값 오류')


def read_hermes_flux_resume_receipt(current_request_identifier):
    from workflow.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record
    return read_resume_receipt_record(FLUX_RESUME_RECEIPT_ROOT,current_request_identifier,validate_flux_resume_target)


def submit_hermes_flux_resume_once(current_request_identifier,current_service_name,current_job_identifier,current_fingerprint_value):
    from workflow.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
    def inspect_flux_resume_preflight(current_service_value,current_job_value,current_expected_value):
        try:current_preview_value=preview_hermes_flux_resume(current_service_value,current_job_value)
        except (OSError,ValueError,TypeError,KeyError,RuntimeError):return 'unavailable'
        if current_preview_value['expected_resume_fingerprint']!=current_expected_value:return 'fingerprint_changed'
        if current_preview_value['resume_availability']=='download_running':return 'download_running'
        if current_preview_value['resume_availability']!='available':return 'unavailable'
        return None
    def send_flux_reviewed_resume(current_service_value,current_job_value,current_expected_value):
        return execute_remote_management_command(current_service_value,'resume-reviewed',{'id':current_job_value,'expected_resume_fingerprint':current_expected_value})
    return submit_resume_receipt_once(FLUX_RESUME_RECEIPT_ROOT,current_request_identifier,current_service_name,current_job_identifier,current_fingerprint_value,validate_flux_resume_target,send_flux_reviewed_resume,current_preflight_callback=inspect_flux_resume_preflight)
