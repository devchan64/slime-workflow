"""F2V 독립 저장소와 첫 프레임 보존 입력 계약."""
from pathlib import Path
from generators.vace.timeline import validate_timeline_request, verify_timeline_request

VACE_FIRST_FRAME_ROOT = Path(__file__).resolve().parents[2] / '.tmp/test/wan21-vace-f2v'


def validate_first_frame_layout(current_request_record):
    if current_request_record.get('frame_entries') != [{'frame': 0, 'editable': False}]:
        raise ValueError('F2V는 첫 프레임 1장을 보존해야 합니다.')
    if current_request_record.get('identity_reference_count', 0) != 0:
        raise ValueError('F2V는 별도 외형 참조를 받지 않습니다.')


def validate_first_frame_request(current_request_record):
    if not isinstance(current_request_record, dict):
        raise ValueError('F2V 요청은 객체여야 합니다.')
    validate_first_frame_layout(current_request_record)
    return validate_timeline_request(current_request_record)


def verify_first_frame_request(current_job_root):
    current_saved_record = verify_timeline_request(current_job_root)
    validate_first_frame_layout(current_saved_record)
    return current_saved_record
