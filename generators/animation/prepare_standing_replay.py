"""보관된 스탠딩 레시피로 내장 이미지젠의 단계별 입력을 준비한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import re
import shutil
import traceback
import yaml

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
RECIPE_SOURCE_PATH = WORKFLOW_ROOT_PATH / 'assets/recipes/character-default-standing-v2/v1/recipe.yaml'
RECIPE_FIELD_NAMES = {
    'version', 'recipe_id', 'generator', 'status', 'input', 'steps',
    'output', 'reproduction', 'policy', 'source_record',
}
SECTION_FIELD_NAMES = {
    'generator': {'tool', 'mode', 'model', 'seed'},
    'input': {'file', 'sha256', 'repository', 'commit', 'path', 'provenance'},
    'output': {'repository', 'path', 'sha256', 'width', 'height', 'metadata_path', 'metadata_sha256', 'snapshot_commit'},
    'reproduction': {'mode', 'original_intermediate_available', 'original_execution_trace_available', 'step_order', 'metadata'},
    'policy': {'use', 'prompt_storage'},
    'source_record': {'repository', 'commit', 'path'},
}

class UniqueRecipeLoader(yaml.SafeLoader):
    """중복 YAML 키를 허용하지 않는다."""

def construct_unique_mapping(current_yaml_loader, current_mapping_node, deep_mapping_flag=False):
    constructed_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_field_name = current_yaml_loader.construct_object(current_key_node, deep=deep_mapping_flag)
        if current_field_name in constructed_mapping_values:
            raise ValueError(f'중복 YAML 키: {current_field_name}')
        constructed_mapping_values[current_field_name] = current_yaml_loader.construct_object(current_value_node, deep=deep_mapping_flag)
    return constructed_mapping_values

UniqueRecipeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)

def require_mapping_fields(current_mapping_value, expected_field_names, current_section_name):
    if not isinstance(current_mapping_value, dict) or set(current_mapping_value) != expected_field_names:
        raise ValueError(f'{current_section_name}: 필수 또는 알 수 없는 필드 오류')

def load_standing_recipe():
    current_recipe_data = yaml.load(RECIPE_SOURCE_PATH.read_text(), Loader=UniqueRecipeLoader)
    require_mapping_fields(current_recipe_data, RECIPE_FIELD_NAMES, 'recipe')
    for current_section_name, expected_field_names in SECTION_FIELD_NAMES.items():
        require_mapping_fields(current_recipe_data[current_section_name], expected_field_names, current_section_name)
        for current_field_name, current_field_value in current_recipe_data[current_section_name].items():
            if current_section_name == 'generator' and current_field_name == 'seed':
                if current_field_value is not None:
                    raise ValueError('내장 도구의 시드는 기록되지 않았습니다')
            elif current_field_name in ('width', 'height'):
                if type(current_field_value) is not int or current_field_value <= 0:
                    raise ValueError('출력 크기는 양의 정수여야 합니다')
            elif current_field_name in ('original_intermediate_available', 'original_execution_trace_available'):
                if type(current_field_value) is not bool:
                    raise ValueError('재현 이력 상태는 bool이어야 합니다')
            elif not isinstance(current_field_value, str) or not current_field_value.strip():
                raise ValueError(f'{current_section_name}.{current_field_name}: 비어 있지 않은 문자열이 필요합니다')
            if current_field_name.endswith('sha256') and not re.fullmatch('[0-9a-f]{64}', current_field_value):
                raise ValueError(f'{current_field_name}: SHA-256 형식 오류')
    if current_recipe_data['status'] != 'historical-runtime-asset':
        raise ValueError('지원하지 않는 기록 상태')
    if type(current_recipe_data['version']) is not int or current_recipe_data['version'] != 1:
        raise ValueError('지원하지 않는 레시피 버전')
    if current_recipe_data['recipe_id'] != 'character-default-standing-v2':
        raise ValueError('지원하지 않는 레시피 ID')
    if current_recipe_data['generator'] != {'tool': 'image_gen', 'mode': 'built-in', 'model': 'tool-managed', 'seed': None}:
        raise ValueError('생성기는 내장 image_gen으로 고정되어야 합니다')
    if not isinstance(current_recipe_data['steps'], list) or len(current_recipe_data['steps']) != 2:
        raise ValueError('initial/refinement 두 단계가 필요합니다')
    for current_step_data, expected_step_name, expected_input_name in zip(current_recipe_data['steps'], ('initial', 'refinement'), ('input-standing-v1.png', 'initial-step-output')):
        require_mapping_fields(current_step_data, {'id', 'prompt', 'input'}, 'step')
        if current_step_data['id'] != expected_step_name or current_step_data['input'] != expected_input_name:
            raise ValueError('단계 순서 또는 입력 계약 오류')
        if not isinstance(current_step_data['prompt'], str) or not current_step_data['prompt'].strip():
            raise ValueError('비어 있는 단계 프롬프트')
    if current_recipe_data['input']['file'] != 'input-standing-v1.png':
        raise ValueError('등록된 v1 참조 파일만 허용합니다')
    return current_recipe_data

def prepare_standing_replay():
    replay_argument_parser = argparse.ArgumentParser(description=__doc__)
    replay_argument_parser.add_argument('--stage', choices=('initial', 'refinement'), required=True)
    replay_argument_parser.add_argument('--input', type=Path, help='refinement에 전달할 이번 initial 단계 PNG')
    replay_parsed_arguments = replay_argument_parser.parse_args()
    replay_started_time = datetime.now(ZoneInfo('Asia/Seoul'))
    replay_output_directory = WORKFLOW_ROOT_PATH / '.tmp' / replay_started_time.strftime('%Y-%m-%d_%H-%M-%S')
    replay_output_directory.mkdir(parents=True, exist_ok=False)
    replay_log_file = replay_output_directory / 'execution.log'

    def record_replay_event(current_stage_name, current_message_text):
        current_log_line = f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/standing-replay/{current_stage_name} {current_message_text}'
        print(current_log_line, flush=True)
        with replay_log_file.open('a') as current_log_stream:
            current_log_stream.write(current_log_line + '\n')

    try:
        record_replay_event('start', '레시피·참조 검증 시작')
        replay_recipe_data = load_standing_recipe()
        if replay_parsed_arguments.stage == 'initial':
            if replay_parsed_arguments.input is not None:
                raise ValueError('initial은 등록된 v1 입력을 사용합니다. --input은 허용하지 않습니다')
            replay_reference_path = RECIPE_SOURCE_PATH.parent / replay_recipe_data['input']['file']
        else:
            if replay_parsed_arguments.input is None:
                raise ValueError('refinement에는 이번 initial 단계 출력 --input이 필요합니다')
            replay_reference_path = replay_parsed_arguments.input.resolve()
        replay_reference_bytes = replay_reference_path.read_bytes()
        if replay_reference_bytes[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('참조 입력은 PNG여야 합니다')
        replay_reference_hash = hashlib.sha256(replay_reference_bytes).hexdigest()
        if replay_parsed_arguments.stage == 'initial' and replay_reference_hash != replay_recipe_data['input']['sha256']:
            raise ValueError('등록된 v1 입력의 SHA-256 불일치')
        replay_selected_step = replay_recipe_data['steps'][0 if replay_parsed_arguments.stage == 'initial' else 1]
        shutil.copy2(replay_reference_path, replay_output_directory / 'reference.png')
        (replay_output_directory / 'prompt.txt').write_text(replay_selected_step['prompt'] + '\n')
        replay_manifest_data = {
            'recipe': replay_recipe_data['recipe_id'], 'version': replay_recipe_data['version'],
            'recipe_sha256': hashlib.sha256(RECIPE_SOURCE_PATH.read_bytes()).hexdigest(),
            'stage': replay_parsed_arguments.stage, 'generator': replay_recipe_data['generator'],
            'reference': 'reference.png', 'reference_source': str(replay_reference_path),
            'reference_sha256': replay_reference_hash, 'prompt': 'prompt.txt',
            'prompt_sha256': hashlib.sha256((replay_output_directory / 'prompt.txt').read_bytes()).hexdigest(),
            'status': 'prepared-not-generated', 'pixel_identical_replay': False,
        }
        (replay_output_directory / 'replay.yaml').write_text(yaml.safe_dump(replay_manifest_data, allow_unicode=True, sort_keys=False))
        record_replay_event('WARN', '원본 실행 중간 이미지·모델·시드 미확인; 동일 픽셀 재현 보장 없음')
        record_replay_event('complete', f'내장 image_gen 입력 준비 완료: {replay_output_directory}')
    except Exception:
        record_replay_event('failed', traceback.format_exc())
        print(replay_log_file.read_text()[-6000:], flush=True)
        raise

if __name__ == '__main__':
    prepare_standing_replay()
