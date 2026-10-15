"""생성 결과와 함께 표시할 읽기 전용 입력 스냅샷."""
import hashlib
import html
from urllib.parse import quote
from pathlib import Path
from PIL import Image

GENERATION_INPUT_ROOT = Path(__file__).resolve().parents[3] / '.tmp/test'


def collect_saved_input_view(current_history_record, server_base_address='', record_folder_route=None):
    """현재 편집값을 변경하지 않고 저장된 요청과 검증된 참조를 반환한다."""
    if not current_history_record:
        return '', {}, [], ''
    current_request_record = current_history_record.get('request', {})
    current_prompt_text = current_request_record.get('final_prompt', current_request_record.get('prompt', current_request_record.get('user_prompt', '')))
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
            if record_folder_route and server_base_address:
                current_reference_address = (server_base_address.rstrip('/') + record_folder_route + '/jobs/'
                    + quote(current_job_directory.name, safe='') + '/'
                    + quote(selected_reference_path.relative_to(current_job_directory).as_posix(), safe='/'))
                current_reference_notices.append(
                    f'<a href="{html.escape(current_reference_address, quote=True)}" target="_blank" rel="noopener noreferrer">입력 참조 {current_reference_index} · 원본 열기 ↗</a>')
    return current_prompt_text, current_request_record, current_reference_images, '\n\n'.join(current_reference_notices)


def describe_saved_prompt_counts(current_history_record):
    """현재 기본값을 사용하지 않고 저장된 원문만 센다."""
    if not current_history_record:
        return ''
    current_request_record = current_history_record.get('request', {})
    current_original_text = current_request_record.get('prompt', current_request_record.get('user_prompt'))
    current_final_text = current_request_record.get('final_prompt')
    current_qwen_record = current_request_record.get('qwen21')
    current_added_text = None
    if isinstance(current_request_record.get('circular_vae'), dict) and isinstance(current_request_record.get('user_prompt'), str):
        current_original_text = current_request_record['user_prompt']
        current_final_text = current_request_record.get('prompt')
    elif isinstance(current_qwen_record, dict) and isinstance(current_qwen_record.get('user_prompt'), str):
        current_original_text = current_qwen_record['user_prompt']
        current_final_text = current_request_record.get('prompt')
        current_added_text = current_qwen_record.get('additional_prompt')
    current_count_parts = []
    if isinstance(current_original_text, str):
        current_count_parts.append(f'저장 원문 {len(current_original_text.split())}단어')
    if isinstance(current_added_text, str):
        current_count_parts.append(f'저장 추가 문구 {len(current_added_text.split())}단어')
    if isinstance(current_final_text, str):
        current_count_parts.append(f'저장 최종 입력 {len(current_final_text.split())}단어')
    else:
        current_count_parts.append('별도 최종 문구 기록 없음 · 현재 기본값으로 재구성하지 않습니다.')
    for current_model_name in ('vace', 'phantom'):
        current_model_record = current_request_record.get(current_model_name)
        if isinstance(current_model_record, dict) and isinstance(current_model_record.get('negative_prompt'), str):
            current_count_parts.append(f"저장 부정 입력 {len(current_model_record['negative_prompt'].split())}단어")
            break
    else:
        if isinstance(current_request_record.get('negative_prompt'), str):
            current_count_parts.append(f"저장 부정 입력 {len(current_request_record['negative_prompt'].split())}단어")
    return ' · '.join(current_count_parts)
