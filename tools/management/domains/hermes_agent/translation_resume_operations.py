"""번역 작업의 재개 검토와 중복 방지 접수."""
from pathlib import Path
import re
from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
from tools.management.domains.hermes_agent.translation_operations import call_hermes_translation_service
from tools.management.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record,submit_resume_receipt_once

TRANSLATION_RESUME_RECEIPT_ROOT=Path(__file__).resolve().parents[4]/'.local/hermes-agent/translation-resume-receipts'


def validate_translation_resume_target(current_service_name,current_job_identifier,current_fingerprint_value=None):
    if current_service_name!='prompt-translation' or not validate_service_job_identifier('prompt-translation',current_job_identifier):
        raise ValueError('번역 재개 대상 오류')
    if current_fingerprint_value is not None and (not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value)):
        raise ValueError('재개 확인값 형식 오류')


def preview_hermes_translation_resume(current_job_identifier):
    validate_translation_resume_target('prompt-translation',current_job_identifier)
    current_preview_value=call_hermes_translation_service('resume-preview',{'id':current_job_identifier})
    if not isinstance(current_preview_value,dict) or current_preview_value.get('id')!=current_job_identifier or current_preview_value.get('service')!='prompt-translation' or current_preview_value.get('status') not in ('failed','cancelled','paused'):
        raise ValueError('번역 재개 검토 대상 확인 불가')
    current_fingerprint_value=current_preview_value.get('expected_resume_fingerprint')
    if not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value):raise ValueError('번역 재개 확인값 오류')
    return {'service':'prompt-translation','job_id':current_job_identifier,'status':current_preview_value['status'],'expected_resume_fingerprint':current_fingerprint_value,'note':'검토 시점 기록이며 실제 실행·GPU 사용 가능 여부는 별도 확인합니다.'}


def read_hermes_translation_resume_receipt(current_request_identifier):
    return read_resume_receipt_record(TRANSLATION_RESUME_RECEIPT_ROOT,current_request_identifier,validate_translation_resume_target)


def submit_hermes_translation_resume_once(current_request_identifier,current_job_identifier,current_fingerprint_value):
    return submit_resume_receipt_once(TRANSLATION_RESUME_RECEIPT_ROOT,current_request_identifier,'prompt-translation',current_job_identifier,current_fingerprint_value,validate_translation_resume_target,lambda current_service_value,current_job_value,current_fingerprint_value:call_hermes_translation_service('resume',{'id':current_job_value,'expected_resume_fingerprint':current_fingerprint_value}))
