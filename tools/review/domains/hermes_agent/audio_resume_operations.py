"""음악·효과음 재개 검토와 중복 방지 접수. 실행 인터페이스는 별도 연결한다."""
from pathlib import Path
import re

from tools.review.domains.hermes_agent.audio_operations import call_hermes_audio_service, validate_hermes_audio_service
from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier

AUDIO_RESUME_RECEIPT_ROOT=Path(__file__).resolve().parents[4]/'.local/hermes-agent/audio-resume-receipts'


def validate_audio_resume_target(current_service_name,current_job_identifier,current_fingerprint_value=None):
    validate_hermes_audio_service(current_service_name)
    if not validate_service_job_identifier(current_service_name,current_job_identifier):
        raise ValueError('음악 재개 작업 ID 오류')
    if current_fingerprint_value is not None and (not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value)):
        raise ValueError('재개 확인값 형식 오류')


def preview_hermes_audio_resume(current_service_name,current_job_identifier):
    validate_audio_resume_target(current_service_name,current_job_identifier)
    current_preview_value=call_hermes_audio_service(current_service_name,'resume-preview',{'id':current_job_identifier})
    if not isinstance(current_preview_value,dict) or current_preview_value.get('id')!=current_job_identifier or current_preview_value.get('service')!=current_service_name or current_preview_value.get('status') not in ('failed','cancelled','paused'):
        raise ValueError('음악 재개 검토 대상 확인 불가')
    current_fingerprint_value=current_preview_value.get('expected_resume_fingerprint')
    if not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value):
        raise ValueError('음악 재개 확인값 오류')
    current_resume_availability=current_preview_value.get('resume_availability','unknown')
    if current_resume_availability not in ('available','download_running','other_preparation','unknown'):
        raise ValueError('음악 재개 가능 상태 오류')
    return {'service':current_service_name,'job_id':current_job_identifier,'status':current_preview_value['status'],'expected_resume_fingerprint':current_fingerprint_value,'resume_availability':current_resume_availability,'note':'검토 시점 기록입니다. 모델 다운로드를 확인하며, 대상이 모델 준비 작업이면 다른 준비 작업도 확인합니다. 접수 시 다시 확인하며 실제 GPU 사용 가능 여부는 보장하지 않습니다.'}


def inspect_audio_resume_receipt(current_record_value,current_request_identifier):
    from tools.review.domains.hermes_agent.resume_receipt_store import inspect_resume_receipt_record
    return inspect_resume_receipt_record(current_record_value,current_request_identifier,validate_audio_resume_target)


def read_hermes_audio_resume_receipt(current_request_identifier):
    from tools.review.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record
    return read_resume_receipt_record(AUDIO_RESUME_RECEIPT_ROOT,current_request_identifier,validate_audio_resume_target)


def validate_current_audio_resume_preflight(current_service_name,current_job_identifier,current_fingerprint_value):
    current_preview_value=preview_hermes_audio_resume(current_service_name,current_job_identifier)
    if current_preview_value['expected_resume_fingerprint']!=current_fingerprint_value:
        return 'fingerprint_changed'
    current_availability_value=current_preview_value['resume_availability']
    if current_availability_value in ('download_running','other_preparation'):return current_availability_value
    if current_availability_value!='available':return 'unavailable'
    return None


def submit_hermes_audio_resume_once(current_request_identifier,current_service_name,current_job_identifier,current_fingerprint_value):
    from tools.review.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
    return submit_resume_receipt_once(AUDIO_RESUME_RECEIPT_ROOT,current_request_identifier,current_service_name,current_job_identifier,current_fingerprint_value,validate_audio_resume_target,lambda current_service_value,current_job_value,current_fingerprint_value:call_hermes_audio_service(current_service_value,'resume',{'id':current_job_value,'expected_resume_fingerprint':current_fingerprint_value}),current_preflight_callback=validate_current_audio_resume_preflight)
