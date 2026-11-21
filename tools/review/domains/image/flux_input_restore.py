"""저장된 FLUX 프롬프트와 참조 이미지를 검증한다."""
import hashlib

from generators.image.common_art_style import compose_common_style_prompt
from tools.review.common.reference_restore import HistoryInputError, restore_reference_inputs, validate_history_input_settings


def restore_flux_image_inputs(current_history_record, current_profile_name, storage_root):
    current_request_record = validate_history_input_settings(current_history_record)
    current_user_prompt = current_request_record.get('user_prompt')
    if not isinstance(current_user_prompt,str) or (not current_user_prompt.strip() and not current_request_record.get('translation_source_ko')) or current_request_record.get('profile') != current_profile_name:
        raise HistoryInputError('저장된 사용자 프롬프트 또는 생성기 정보가 없습니다.')
    current_final_prompt,_ = compose_common_style_prompt(current_user_prompt)
    if current_request_record.get('prompt') != current_final_prompt or current_request_record.get('prompt_sha256') != hashlib.sha256(current_final_prompt.encode()).hexdigest():
        raise HistoryInputError('저장된 프롬프트가 현재 화풍과 다르거나 변조되어 복원할 수 없습니다.')
    current_allowed_steps = range(1, 51) if current_profile_name == 'flux-character' else (16,)
    if type(current_request_record.get('steps')) is not int or current_request_record['steps'] not in current_allowed_steps or type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
        raise HistoryInputError('저장된 스텝 또는 시드가 올바르지 않습니다.')
    current_maximum_size = 2048 if current_profile_name == 'flux-character' else 1664
    if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= current_maximum_size or current_request_record[name] % 16 for name in ('width','height')):
        raise HistoryInputError('저장된 출력 크기가 올바르지 않습니다.')
    current_restored_values = restore_reference_inputs(current_history_record, storage_root,reference_slot_limit=2)
    current_input_prompt=current_request_record.get('building_design_ko',current_user_prompt) if current_profile_name=='flux-building' else current_request_record.get('translation_base_prompt',current_user_prompt)
    current_output_values=(current_input_prompt,current_restored_values[6],current_restored_values[7],current_restored_values[2],current_restored_values[3],current_request_record['steps'],current_restored_values[5],current_restored_values[1])
    if current_profile_name == 'flux-seamless':
        current_saved_method=current_request_record.get('seamless_method','edge-blend')
        if current_saved_method not in ('global-periodic-v1','circular-vae-v2','circular-vae','edge-blend'): raise HistoryInputError('저장된 심리스 처리 방식이 올바르지 않습니다.')
    if current_profile_name != 'flux-building':
        current_output_values += (current_request_record.get('translation_source_ko',''),)
    return current_output_values
