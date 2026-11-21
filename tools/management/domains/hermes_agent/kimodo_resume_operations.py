"""Kimodo 재개 검토와 중복 방지 접수."""
import re
import hashlib
import json
from pathlib import Path
from tools.management.common.management_client import execute_remote_management_command
from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier


KIMODO_RESUME_RECEIPT_ROOT=Path(__file__).resolve().parents[4]/'.local/hermes-agent/kimodo-resume-receipts'


def validate_kimodo_resume_target(current_service_name,current_job_identifier,current_fingerprint_value=None):
    if current_service_name!='kimodo' or not validate_service_job_identifier('kimodo',current_job_identifier):raise ValueError('Kimodo 재개 대상 오류')
    if current_fingerprint_value is not None and (not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value)):raise ValueError('Kimodo 재개 확인값 오류')


def preview_hermes_kimodo_resume(current_job_identifier):
    if not validate_service_job_identifier('kimodo',current_job_identifier):
        raise ValueError('Kimodo 재개 작업 ID 오류')
    current_result_value=execute_remote_management_command('kimodo','resume-preview',{'id':current_job_identifier})
    if (not isinstance(current_result_value,dict) or current_result_value.get('id')!=current_job_identifier
            or current_result_value.get('service')!='kimodo' or current_result_value.get('status') not in ('failed','cancelled','paused')
            or not isinstance(current_result_value.get('expected_resume_fingerprint'),str)
            or not re.fullmatch(r'[a-f0-9]{64}',current_result_value['expected_resume_fingerprint'])):
        raise ValueError('Kimodo 재개 검토 응답 오류')
    if 'keyframe_fingerprint' not in current_result_value or (current_result_value['keyframe_fingerprint'] is not None and (not isinstance(current_result_value['keyframe_fingerprint'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_result_value['keyframe_fingerprint']))):
        raise ValueError('Kimodo 키프레임 확인값 오류')
    current_resume_availability=current_result_value.get('resume_availability','unknown')
    if current_resume_availability not in ('available','download_running','unknown'):raise ValueError('Kimodo 재개 가능 상태 오류')
    current_fingerprint_values={'records':current_result_value['expected_resume_fingerprint'],'keyframes':current_result_value['keyframe_fingerprint']}
    current_review_fingerprint=hashlib.sha256(json.dumps(current_fingerprint_values,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    return {'service':'kimodo','job_id':current_job_identifier,'status':current_result_value['status'],
            'expected_resume_fingerprint':current_review_fingerprint,'record_fingerprint':current_fingerprint_values['records'],'keyframe_fingerprint':current_fingerprint_values['keyframes'],'resume_availability':current_resume_availability,
            'note':'작업 기록과 키프레임을 결합한 검토값입니다. 실제 재개 접수 시 같은 값을 다시 검증하며 GPU 가용성은 별도입니다.'}


def read_hermes_kimodo_resume_receipt(current_request_identifier):
    from tools.management.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record
    return read_resume_receipt_record(KIMODO_RESUME_RECEIPT_ROOT,current_request_identifier,validate_kimodo_resume_target)


def submit_hermes_kimodo_resume_once(current_request_identifier,current_job_identifier,current_fingerprint_value):
    from tools.management.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
    current_review_records=[]
    def inspect_kimodo_resume_preflight(current_service_name,current_job_value,current_expected_value):
        try:
            current_review_value=preview_hermes_kimodo_resume(current_job_value)
        except (OSError,ValueError,TypeError,KeyError,RuntimeError):
            return 'unavailable'
        if current_review_value['expected_resume_fingerprint']!=current_expected_value:return 'fingerprint_changed'
        if current_review_value.get('resume_availability')=='download_running':return 'download_running'
        if current_review_value.get('resume_availability')!='available':return 'unavailable'
        current_review_records.append(current_review_value)
        return None
    def send_kimodo_reviewed_resume(current_service_name,current_job_value,current_expected_value):
        if len(current_review_records)!=1:raise ValueError('Kimodo 재개 검토를 확인할 수 없습니다.')
        current_review_value=current_review_records[0]
        return execute_remote_management_command('kimodo','resume-reviewed',{'id':current_job_value,'expected_resume_fingerprint':current_review_value['record_fingerprint'],'keyframe_fingerprint':current_review_value['keyframe_fingerprint']})
    return submit_resume_receipt_once(KIMODO_RESUME_RECEIPT_ROOT,current_request_identifier,'kimodo',current_job_identifier,current_fingerprint_value,validate_kimodo_resume_target,send_kimodo_reviewed_resume,current_preflight_callback=inspect_kimodo_resume_preflight)
