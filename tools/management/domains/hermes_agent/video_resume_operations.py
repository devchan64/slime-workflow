"""영상 재개 검토와 중복 방지 접수 기록."""
import re
from pathlib import Path
from tools.management.common.management_client import execute_remote_management_command
from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
from tools.management.domains.hermes_agent.resume_receipt_store import read_resume_receipt_record, submit_resume_receipt_once

VIDEO_RESUME_SERVICES = ('dwpose', 'wan22-animate2', 'wan22-vace', 'wan22-fun-control')
VIDEO_RESUME_RECEIPT_ROOT = Path(__file__).resolve().parents[4] / '.local/hermes-agent/video-resume-receipts'


def validate_video_resume_target(current_service_name, current_job_identifier, current_fingerprint_value=None):
    if not isinstance(current_service_name, str) or current_service_name not in VIDEO_RESUME_SERVICES or not validate_service_job_identifier(current_service_name, current_job_identifier):
        raise ValueError('영상 재개 대상 오류')
    if current_fingerprint_value is not None and (not isinstance(current_fingerprint_value, str) or not re.fullmatch(r'[a-f0-9]{64}', current_fingerprint_value)):
        raise ValueError('영상 재개 확인값 오류')


def preview_hermes_video_resume(current_service_name, current_job_identifier):
    validate_video_resume_target(current_service_name, current_job_identifier)
    current_preview_record = execute_remote_management_command(current_service_name, 'resume-preview', {'id': current_job_identifier})
    if (not isinstance(current_preview_record, dict) or current_preview_record.get('service') != current_service_name
            or current_preview_record.get('id') != current_job_identifier or current_preview_record.get('status') not in ('failed', 'cancelled', 'paused')
            or not isinstance(current_preview_record.get('expected_resume_fingerprint'), str)
            or not re.fullmatch(r'[a-f0-9]{64}', current_preview_record['expected_resume_fingerprint'])):
        raise ValueError('영상 재개 검토 응답 오류')
    current_availability_value = current_preview_record.get('resume_availability', 'unknown')
    if current_availability_value not in ('available', 'download_running', 'unknown'):
        raise ValueError('영상 재개 준비 상태 오류')
    return {'service': current_service_name, 'job_id': current_job_identifier, 'status': current_preview_record['status'],
            'resume_availability': current_availability_value,
            'expected_resume_fingerprint': current_preview_record['expected_resume_fingerprint'],
            'note': '저장 입력 검토 결과입니다. 중단된 실행 기록을 복구할 수 있습니다. GPU 가용성은 별도이며 접수 시 모델 준비 충돌을 다시 확인합니다.'}


def read_hermes_video_resume_receipt(current_request_identifier):
    return read_resume_receipt_record(VIDEO_RESUME_RECEIPT_ROOT, current_request_identifier, validate_video_resume_target)


def submit_hermes_video_resume_once(current_request_identifier, current_service_name, current_job_identifier, current_fingerprint_value):
    def inspect_video_resume_preflight(current_service_value, current_job_value, current_expected_value):
        try:
            current_preview_record = preview_hermes_video_resume(current_service_value, current_job_value)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError):
            return 'unavailable'
        if current_preview_record['expected_resume_fingerprint'] != current_expected_value:return 'fingerprint_changed'
        if current_preview_record['resume_availability'] == 'download_running':return 'download_running'
        if current_preview_record['resume_availability'] != 'available':return 'unavailable'
        return None
    def send_video_reviewed_resume(current_service_value, current_job_value, current_expected_value):
        return execute_remote_management_command(current_service_value, 'resume-reviewed', {'id': current_job_value, 'expected_resume_fingerprint': current_expected_value})
    return submit_resume_receipt_once(VIDEO_RESUME_RECEIPT_ROOT, current_request_identifier, current_service_name, current_job_identifier,
                                      current_fingerprint_value, validate_video_resume_target, send_video_reviewed_resume,
                                      current_preflight_callback=inspect_video_resume_preflight)
