"""생성 결과와 함께 표시할 읽기 전용 입력 스냅샷."""
import hashlib
from pathlib import Path
from PIL import Image

GENERATION_INPUT_ROOT = Path(__file__).resolve().parents[3] / '.tmp/test'


def collect_saved_input_view(current_history_record):
    """현재 편집값을 변경하지 않고 저장된 요청과 검증된 참조를 반환한다."""
    if not current_history_record:
        return '', {}, [], ''
    current_request_record = current_history_record.get('request', {})
    current_prompt_text = current_request_record.get('prompt', current_request_record.get('user_prompt', ''))
    current_reference_images = []
    current_reference_notices = []
    current_snapshot_records = current_request_record.get('reference_snapshots', [])
    if current_snapshot_records:
        current_directory_value = current_history_record.get('job_path') or current_history_record.get('path')
        if not current_directory_value:
            return current_prompt_text, current_request_record, [], '참조 저장 경로가 기록되어 있지 않습니다.'
        current_job_directory = Path(current_directory_value).resolve()
        if not current_job_directory.is_relative_to(GENERATION_INPUT_ROOT.resolve()):
            return current_prompt_text, current_request_record, [], '허용된 생성 기록 경로가 아니므로 참조를 표시하지 않습니다.'
        for current_reference_index, current_snapshot_record in enumerate(current_snapshot_records, 1):
            selected_reference_path = (current_job_directory / current_snapshot_record['path']).resolve()
            if not selected_reference_path.is_relative_to(current_job_directory):
                raise ValueError('참조 이미지가 생성 기록 폴더 밖을 가리킵니다.')
            if not selected_reference_path.is_file():
                current_reference_notices.append(f'참조 {current_reference_index}: 원본 파일 없음')
                continue
            if hashlib.sha256(selected_reference_path.read_bytes()).hexdigest() != current_snapshot_record['sha256']:
                current_reference_notices.append(f'참조 {current_reference_index}: 해시 불일치로 표시 제외')
                continue
            with Image.open(selected_reference_path) as current_reference_image:
                current_reference_images.append((current_reference_image.copy(), f'입력 참조 {current_reference_index}'))
    return current_prompt_text, current_request_record, current_reference_images, '\n'.join(current_reference_notices)
