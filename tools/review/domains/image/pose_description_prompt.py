"""포즈 설명 선택과 최종 프롬프트 결합."""
from pathlib import Path
import yaml
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader
from tools.review.domains.image.pose_transfer_generation import combine_pose_prompt

POSE_DESCRIPTION_CONFIG_PATH = Path(__file__).resolve().parents[4] / 'generators/image/config/pose-description-prompts.yaml'


def load_pose_descriptions():
    current_config_record = yaml.load(POSE_DESCRIPTION_CONFIG_PATH.read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(current_config_record, dict) or 'none' not in current_config_record:
        raise ValueError('포즈 설명 설정에 none 항목이 필요합니다.')
    for current_choice_identifier, current_choice_record in current_config_record.items():
        if not isinstance(current_choice_identifier, str) or not isinstance(current_choice_record, dict) or set(current_choice_record) != {'label', 'prompt'} or not all(isinstance(current_field_value, str) for current_field_value in current_choice_record.values()):
            raise ValueError('포즈 설명 설정의 ID·label·prompt 형식을 확인하세요.')
    if current_config_record['none']['prompt'] != '':
        raise ValueError('설명 없음의 프롬프트는 비어 있어야 합니다.')
    return current_config_record


def compose_description_prompt(current_base_prompt, current_auxiliary_prompt, selected_description_identifier):
    current_description_records = load_pose_descriptions()
    if selected_description_identifier not in current_description_records:
        raise ValueError('등록된 설명 프롬프트를 선택하세요.')
    current_description_text = current_description_records[selected_description_identifier]['prompt']
    return combine_pose_prompt(current_base_prompt, ' '.join((current_auxiliary_prompt, current_description_text)).strip())
