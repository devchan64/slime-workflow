"""생성 결과와 함께 표시할 읽기 전용 입력 스냅샷."""
import hashlib
import html
import json
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
        current_job_directory = Path(current_directory_value)
        if current_job_directory.is_symlink():
            return current_prompt_text, current_request_record, [], '참조 이미지 작업 폴더가 심볼릭 링크이므로 표시하지 않습니다.'
        current_job_directory = current_job_directory.resolve()
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


def collect_saved_negative_prompt(current_history_record):
    """실행 당시 모델 설정의 부정 문구를 우선하며 빈 문구도 보존한다."""
    current_request_record = (current_history_record or {}).get('request', {})
    for current_model_name in ('vace', 'phantom'):
        current_model_record = current_request_record.get(current_model_name)
        if isinstance(current_model_record, dict) and isinstance(current_model_record.get('negative_prompt'), str):
            return current_model_record['negative_prompt']
    current_negative_text = current_request_record.get('negative_prompt')
    return current_negative_text if isinstance(current_negative_text, str) else None


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
    current_negative_text = collect_saved_negative_prompt(current_history_record)
    if current_negative_text is not None:
        current_count_parts.append(f"저장 부정 입력 {len(current_negative_text.split())}단어")
    return ' · '.join(current_count_parts)


def collect_saved_stage_prompts(current_history_record):
    """접수 문구와 단계별 실행 요청을 구분하여 현재 설정 없이 표시한다."""
    current_request_record = (current_history_record or {}).get('request', {})
    if current_request_record.get('schema_version') == 2 and 'outfit_prompt' in current_request_record:
        current_part_sections = []
        for current_prompt_key, current_part_label in (('prompt', '신체 베이스'), ('outfit_prompt', '복장')):
            current_part_prompt = current_request_record.get(current_prompt_key)
            if not isinstance(current_part_prompt, str):
                current_part_sections.append(f'{current_part_label} · 저장 요청 문구 없음')
            else:
                current_part_sections.append(f'{current_part_label} · 저장 요청 {len(current_part_prompt.split())}단어\n{current_part_prompt}')
        return '\n\n'.join(current_part_sections)
    current_pattern_record = current_request_record.get('seamless_tile', {})
    if not isinstance(current_pattern_record, dict) or current_pattern_record.get('schema_version') not in (6, 7):
        return ''
    current_directory_value = current_history_record.get('job_path') or current_history_record.get('path')
    if not current_directory_value:
        return '단계별 실행 입력: 저장 경로가 기록되어 있지 않습니다.'
    current_job_directory = Path(current_directory_value)
    if current_job_directory.is_symlink() or not current_job_directory.resolve().is_relative_to(GENERATION_INPUT_ROOT.resolve()):
        return '단계별 실행 입력: 허용된 작업 폴더가 아니므로 표시하지 않습니다.'
    current_job_directory = current_job_directory.resolve()
    current_stage_sections = []
    for current_stage_number, current_stage_folder in ((1, 'stage-1-pattern'), (3, 'stage-3-horizontal'), (5, 'stage-5-vertical')):
        current_stage_path = current_job_directory / current_stage_folder / 'request.json'
        if current_stage_path.parent.is_symlink() or current_stage_path.is_symlink():
            current_stage_sections.append(f'{current_stage_number}단계 · 실행 요청이 심볼릭 링크이므로 표시하지 않습니다.')
            continue
        if not current_stage_path.exists():
            current_stage_sections.append(f'{current_stage_number}단계 · 실행 요청 기록 없음 · 접수 문구로 재구성하지 않습니다.')
            continue
        try:
            current_stage_record = json.loads(current_stage_path.read_text())
            if not isinstance(current_stage_record, dict) or not isinstance(current_stage_record.get('prompt'), str):
                raise ValueError('prompt 문자열 누락')
        except (OSError, ValueError) as current_stage_error:
            current_stage_sections.append(f'{current_stage_number}단계 · 실행 요청 읽기 실패: {current_stage_error}')
            continue
        current_stage_prompt = current_stage_record['prompt']
        current_stage_sections.append(f'{current_stage_number}단계 · 저장 실행 입력 {len(current_stage_prompt.split())}단어\n{current_stage_prompt}')
    return '\n\n'.join(current_stage_sections)
