"""AU 참고 프리셋을 사용하는 Qwen 2511 표정 작업 서비스."""
import hashlib
import json
import yaml
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, validate_qwen_plain_request, verify_qwen_saved_request
from tools.review.domains.image.three_reference_generation import validate_three_reference_request

EXPRESSION_CONFIGURATION_PATH = WORKFLOW_ROOT_PATH / 'generators/image/config/expression_presets.yaml'
EXPRESSION_ADAPTER_PATH = WORKFLOW_ROOT_PATH / '.model/qwen-21-anime-consistency/Qwen2.1_Anime_consistency.safetensors'
EXPRESSION_ADAPTER_SHA256 = '0c171eb802ea8051b511f2d93c1743eeadd030316255aa98fa65d40809366752'
EXPRESSION_ADAPTER_SCALE = 0.7
EXPRESSION_ADAPTER_REPOSITORY = 'A20labs/Qwen-Image-2.1-LoRAs'
EXPRESSION_ADAPTER_REVISION = '3b37b28'


def validate_expression_adapter():
    if not EXPRESSION_ADAPTER_PATH.is_file():
        raise FileNotFoundError(f'표정 LoRA 가중치가 없습니다: {EXPRESSION_ADAPTER_PATH} ({EXPRESSION_ADAPTER_REPOSITORY}@{EXPRESSION_ADAPTER_REVISION})')
    if hashlib.sha256(EXPRESSION_ADAPTER_PATH.read_bytes()).hexdigest() != EXPRESSION_ADAPTER_SHA256:
        raise ValueError(f'표정 LoRA 가중치 해시가 일치하지 않습니다: {EXPRESSION_ADAPTER_PATH}')
    return EXPRESSION_ADAPTER_PATH


def expression_adapter_metadata():
    return {'repository': EXPRESSION_ADAPTER_REPOSITORY, 'revision': EXPRESSION_ADAPTER_REVISION, 'filename': EXPRESSION_ADAPTER_PATH.name, 'sha256': EXPRESSION_ADAPTER_SHA256, 'scale': EXPRESSION_ADAPTER_SCALE}


def verify_expression_saved_request(current_job_root, current_request_record):
    if current_request_record.get('expression_adapter') != expression_adapter_metadata():
        raise ValueError('이전 표정 이력 또는 LoRA 설정이 일치하지 않아 재개할 수 없습니다.')
    current_expression_record = current_request_record.get('expression')
    if not isinstance(current_expression_record, dict) or hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_expression_record.get('prompt_sha256'):
        raise ValueError('저장된 표정 프롬프트 해시가 일치하지 않습니다.')
    verify_qwen_saved_request(current_job_root, current_request_record)


class ExpressionConfigurationLoader(yaml.SafeLoader):
    """중복 설정 키를 거절한다."""


def construct_unique_mapping(current_yaml_loader, current_yaml_node, deep=False):
    current_mapping_value = {}
    for current_key_node, current_value_node in current_yaml_node.value:
        current_key_value = current_yaml_loader.construct_object(current_key_node, deep=deep)
        if current_key_value in current_mapping_value:
            raise ValueError(f'표정 설정 중복 키: {current_key_value}')
        current_mapping_value[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=deep)
    return current_mapping_value


ExpressionConfigurationLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def load_expression_configuration():
    current_config_record = yaml.load(EXPRESSION_CONFIGURATION_PATH.read_text(), Loader=ExpressionConfigurationLoader)
    if not isinstance(current_config_record, dict) or set(current_config_record) != {'version','source','base_prompt','expressions'} or type(current_config_record['version']) is not int or current_config_record['version'] != 1:
        raise ValueError('표정 설정 스키마 오류')
    current_source_record = current_config_record['source']
    if not isinstance(current_source_record, dict) or set(current_source_record) != {'section','version','sha256'} or not all(isinstance(current_source_value,str) and current_source_value for current_source_value in current_source_record.values()):
        raise ValueError('표정 출처 설정 오류')
    if not isinstance(current_config_record['base_prompt'],str) or not current_config_record['base_prompt'].strip() or not isinstance(current_config_record['expressions'],list) or not current_config_record['expressions']:
        raise ValueError('표정 프롬프트 설정 오류')
    seen_expression_identifiers = set()
    for current_expression_record in current_config_record['expressions']:
        if not isinstance(current_expression_record,dict) or set(current_expression_record) != {'id','label_ko','au_hints','movement_prompt'}:
            raise ValueError('표정 항목 필드 오류')
        if not all(isinstance(current_expression_record[current_field_name],str) and current_expression_record[current_field_name].strip() for current_field_name in ('id','label_ko','movement_prompt')):
            raise ValueError('표정 항목 문자열 오류')
        if current_expression_record['id'] in seen_expression_identifiers:
            raise ValueError('표정 ID 중복')
        seen_expression_identifiers.add(current_expression_record['id'])
        if not isinstance(current_expression_record['au_hints'],list) or any(type(current_au_number) is not int or not 1 <= current_au_number <= 64 for current_au_number in current_expression_record['au_hints']):
            raise ValueError('AU 참고 목록 오류')
        if len((current_expression_record['movement_prompt']+' '+current_config_record['base_prompt']).split()) >= 100:
            raise ValueError('표정 최종 프롬프트는 100단어 미만이어야 합니다.')
    return current_config_record


def build_expression_prompt(expression_identifier_value):
    current_config_record = load_expression_configuration()
    for current_expression_record in current_config_record['expressions']:
        if current_expression_record['id'] == expression_identifier_value:
            final_prompt_value = current_expression_record['movement_prompt']+'. '+current_config_record['base_prompt']
            return final_prompt_value, {**current_expression_record, 'source':current_config_record['source'], 'config_sha256':hashlib.sha256(EXPRESSION_CONFIGURATION_PATH.read_bytes()).hexdigest(), 'prompt_word_count':len(final_prompt_value.split()), 'prompt_sha256':hashlib.sha256(final_prompt_value.encode()).hexdigest()}
    raise ValueError('알 수 없는 표정 ID입니다. 표정 프리셋을 선택하세요.')


class ExpressionGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/expression-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/expression-generator'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'expression'

    def validate_generation_request(self, request_record_value):
        current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=(20, 30, 40, 50))
        if not 1 <= len(current_request_record['images']) <= 3:
            raise ValueError('표정 생성에는 참조 이미지 1~3장이 필요합니다.')
        final_prompt_value, expression_source_record = build_expression_prompt(current_request_record['prompt'])
        current_request_record = validate_qwen_plain_request({**current_request_record, 'prompt': final_prompt_value})
        return {**current_request_record, 'expression':expression_source_record, 'expression_adapter':expression_adapter_metadata()}

    def validate_generation_runtime(self, saved_request_record=None):
        super().validate_generation_runtime(saved_request_record)
        validate_expression_adapter()

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        current_command_path = selected_job_directory / 'gpu-command.json'
        if current_command_path.exists():
            current_command_values = json.loads(current_command_path.read_text()).get('command')
            if not isinstance(current_command_values, list) or len(current_command_values) < 2 or not isinstance(current_command_values[1], str) or not current_command_values[1].endswith('/run_qwen_21_reference.py'):
                raise ValueError('이전 표정 실행기는 폐기되어 재개할 수 없습니다.')
        verify_expression_saved_request(selected_job_directory, current_request_record)

    def enrich_generation_status(self, current_job_root, current_status_record):
        current_status_record = super().enrich_generation_status(current_job_root, current_status_record)
        current_request_path = current_job_root / 'request.json'
        if current_request_path.exists():
            current_request_record = json.loads(current_request_path.read_text())
            if current_request_record.get('expression_adapter') != expression_adapter_metadata():
                current_status_record['resume_allowed'] = False
                current_status_record['resume_block_reason'] = '이전 표정 생성 이력은 재개할 수 없습니다. Qwen 2.1로 새 작업을 생성하세요.'
        return current_status_record
