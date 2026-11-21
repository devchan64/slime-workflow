"""FLUX 표정 작업과 이전 Qwen 이력을 분리한다."""
from workflow.common.reference_restore import HistoryInputError, restore_reference_inputs, validate_history_input_settings
import hashlib
import json
import re
from pathlib import Path
from workflow.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH
from workflow.domains.image.three_reference_generation import validate_three_reference_request, verify_reference_snapshots
from workflow.domains.image.expression_generation import load_expression_configuration
from workflow.domains.image.flux_translation_queue import FluxTranslationQueueMixin, validate_flux_translation_runtime, validate_flux_translation_record

FLUX_MODEL_ROOT_DIRECTORY = WORKFLOW_ROOT_PATH / '.model/flux-3-image-klein'
FLUX_MODEL_REVISION_VALUE = '09561231f44e41381c461caf53d5452005a60ac9'
FLUX_PROMPT_BASE_TEXT = ('Edit the facial expression to show {expression}. Keep the same character identity, facial proportions, eye color, hair shape and color, head size, front-facing angle, framing, background, linework and rendering style. Preserve the exact original hair and skin colors and their shading; do not recolor or retouch the hair, skin, eyes or background. Change only the eyebrows, eyelids and mouth as needed for expression.')


def build_flux_expression_prompt(expression_identifier_value):
    current_expression_record = next((item for item in load_expression_configuration()['expressions'] if item['id'] == expression_identifier_value), None)
    if current_expression_record is None:
        raise ValueError('등록된 표정을 선택하세요.')
    return FLUX_PROMPT_BASE_TEXT.format(expression=current_expression_record['movement_prompt'])


def restore_flux_expression_inputs(current_history_record, reference_storage_root=None):
    current_request_record = validate_history_input_settings(current_history_record)
    current_expression_identifier = current_request_record.get('expression_id')
    if not isinstance(current_expression_identifier, str):
        raise HistoryInputError('저장된 표정 프리셋이 없습니다. 표정을 직접 선택하세요.')
    try:
        current_expected_prompt = build_flux_expression_prompt(current_expression_identifier)
    except ValueError as current_preset_error:
        raise HistoryInputError('저장된 표정 프리셋을 현재 사용할 수 없습니다.') from current_preset_error
    current_translated_text=current_request_record.get('translated_design')
    if isinstance(current_translated_text,str):
        current_expected_prompt=' '.join((current_expected_prompt,current_translated_text.strip()))
    if current_request_record.get('prompt') != current_expected_prompt or current_request_record.get('prompt_sha256') != hashlib.sha256(current_expected_prompt.encode()).hexdigest():
        raise HistoryInputError('저장된 프롬프트가 현재 프리셋과 달라 동일한 입력으로 복원할 수 없습니다.')
    if current_request_record.get('steps') != 16:
        raise HistoryInputError('저장된 생성 단계가 현재 설정과 다릅니다.')
    if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= 1664 or current_request_record[name] % 16 for name in ('width', 'height')):
        raise HistoryInputError('저장된 출력 크기가 올바르지 않습니다.')
    if type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
        raise HistoryInputError('저장된 시드가 올바르지 않습니다.')
    current_reference_names = current_request_record.get('references')
    if not isinstance(current_reference_names, list) or len(current_reference_names) != 1:
        raise HistoryInputError('얼굴 참조 이미지 1장의 저장 정보가 필요합니다.')
    restored_reference_values = restore_reference_inputs(current_history_record, reference_storage_root or WORKFLOW_ROOT_PATH / '.tmp/test/flux-expression-generator', reference_slot_limit=1)
    return (restored_reference_values[6], current_expression_identifier, restored_reference_values[2], restored_reference_values[3], restored_reference_values[5], restored_reference_values[1],current_request_record.get('translation_source_ko',''))


class FluxExpressionGenerationManager(FluxTranslationQueueMixin, ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/flux-expression-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/flux-expression-generator'
        self.reference_request_limit = 12_100_000

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'flux-expression'

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/image/run_flux_expression.py'

    def select_generation_service(self, saved_request_record=None):
        return 'flux-expression'

    def validate_generation_runtime(self, saved_request_record=None):
        if not all((FLUX_MODEL_ROOT_DIRECTORY / name).exists() for name in ('manifest.json', 'transformer', 'vae', 'text_encoder')):
            raise ValueError('FLUX 3 Image Klein 모델 구성 요소가 없습니다.')
        validate_flux_translation_runtime(saved_request_record)

    def validate_generation_request(self, request_record_value):
        current_translation_source=None
        if isinstance(request_record_value,dict) and 'translation_source_ko' in request_record_value:
            current_translation_source=request_record_value['translation_source_ko']
            if not isinstance(current_translation_source,str) or not current_translation_source.strip() or len(current_translation_source)>6000 or not re.search('[가-힣]',current_translation_source):
                raise ValueError('추가 지시를 6000자 이하의 한국어로 입력하세요.')
            request_record_value={key:value for key,value in request_record_value.items() if key!='translation_source_ko'}
        current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=(16,), maximum_reference_count=1, minimum_output_size=256)
        if len(current_request_record['images']) != 1:
            raise ValueError('얼굴 참조 이미지 1장이 필요합니다.')
        current_prompt_text = build_flux_expression_prompt(current_request_record['prompt'])
        return {**current_request_record, 'expression_id':current_request_record['prompt'], 'prompt':current_prompt_text, 'flux_model_revision':FLUX_MODEL_REVISION_VALUE, 'prompt_sha256':hashlib.sha256(current_prompt_text.encode()).hexdigest(), **({'translation_source_ko':current_translation_source.strip(),'translation_base_prompt':current_prompt_text,'user_prompt':current_prompt_text} if current_translation_source else {})}

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        verify_reference_snapshots(selected_job_directory, current_request_record)
        if current_request_record.get('translation_source_ko'):
            validate_flux_translation_record(selected_job_directory,current_request_record,expression_mode_enabled=True)
        if len(current_request_record.get('references', [])) != 1 or current_request_record.get('steps') != 16 or type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('저장된 참조·스텝 또는 시드가 올바르지 않습니다.')
        if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= 1664 or current_request_record[name] % 16 for name in ('width', 'height')):
            raise ValueError('저장된 출력 크기가 올바르지 않습니다.')
        if current_request_record.get('flux_model_revision') != FLUX_MODEL_REVISION_VALUE or hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_request_record.get('prompt_sha256'):
            raise ValueError('저장된 모델 또는 프롬프트 정보가 일치하지 않습니다.')
        if current_request_record.get('translation_source_ko') and not (selected_job_directory/'gpu-command.json').exists():
            return
        current_command_record = json.loads((selected_job_directory/'gpu-command.json').read_text())
        if Path(current_command_record['command'][1]).resolve() != (WORKFLOW_ROOT_PATH/self.select_generation_runner()).resolve():
            raise ValueError('저장된 실행기가 일치하지 않습니다.')
