"""FL2V의 첫·끝 프레임 보존 계약과 독립 저장소."""
from pathlib import Path
from generators.vace.timeline import validate_timeline_request, verify_timeline_request

VACE_FIRST_LAST_ROOT = Path(__file__).resolve().parents[2] / '.tmp/test/wan21-vace-fl2v'


def validate_first_last_layout(current_request_record):
    current_frame_count = current_request_record.get('frames')
    if isinstance(current_frame_count, bool) or not isinstance(current_frame_count, int) or current_frame_count < 5:
        raise ValueError('FL2V는 첫·끝 프레임이 분리되도록 5프레임 이상이어야 합니다.')
    current_expected_entries = [{'frame': 0, 'editable': False}, {'frame': current_frame_count - 1, 'editable': False}]
    if current_request_record.get('frame_entries') != current_expected_entries:
        raise ValueError('FL2V는 첫 프레임과 마지막 프레임 2장을 보존해야 합니다.')
    if current_request_record.get('identity_reference_count', 0) != 0:
        raise ValueError('FL2V는 별도 외형 참조를 받지 않습니다.')


def validate_first_last_request(current_request_record):
    if not isinstance(current_request_record, dict):
        raise ValueError('FL2V 요청은 객체여야 합니다.')
    validate_first_last_layout(current_request_record)
    return validate_timeline_request(current_request_record)


def verify_first_last_request(current_job_root):
    current_saved_record = verify_timeline_request(current_job_root)
    validate_first_last_layout(current_saved_record)
    return current_saved_record
