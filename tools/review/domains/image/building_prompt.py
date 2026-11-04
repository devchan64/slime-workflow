"""건물 Qwen 페이지의 추적 기본 문구와 입력 준비 상태."""
from pathlib import Path
from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt

BUILDING_PROMPT_SOURCE_PATH = Path(__file__).resolve().parents[4] / 'generators/image/config/building-qwen-prompt.txt'


def load_building_base_prompt():
    current_prompt_text = BUILDING_PROMPT_SOURCE_PATH.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('건물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def check_building_input_readiness(current_prompt_text, current_style_enabled, current_transparency_enabled, current_layout_image, building_prompt_enabled=False):
    if building_prompt_enabled:
        current_prompt_text = (current_prompt_text.strip() + ' ' + load_building_base_prompt()).strip()
    current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_prompt_text, current_style_enabled, current_transparency_enabled)
    return current_layout_image is not None and 0 < len(current_final_prompt.split()) < 100


def load_prop_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('prop-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('소품 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def load_vegetation_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('vegetation-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('자연물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


from tools.review.domains.image.building_structure_guides import BUILDING_STRUCTURE_CATALOG, BUILDING_STRUCTURE_ROOT
import yaml


def read_building_structure_catalog():
    class BuildingCatalogStrictLoader(yaml.SafeLoader):
        pass
    def construct_unique_mapping(current_yaml_loader, current_mapping_node):
        current_mapping_record = {}
        for current_key_node, current_value_node in current_mapping_node.value:
            current_key_name = current_yaml_loader.construct_object(current_key_node)
            if current_key_name in current_mapping_record:
                raise ValueError('건물 카탈로그 중복 키: '+str(current_key_name))
            current_mapping_record[current_key_name] = current_yaml_loader.construct_object(current_value_node)
        return current_mapping_record
    BuildingCatalogStrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)
    current_catalog_value = yaml.load(BUILDING_STRUCTURE_CATALOG.read_text(), Loader=BuildingCatalogStrictLoader)
    if set(current_catalog_value) != {'version', 'guides'} or current_catalog_value['version'] != 1:
        raise ValueError('건물 구조 카탈로그 버전 오류')
    current_catalog_records = current_catalog_value['guides']
    if len(current_catalog_records) != 50 or len({record['id'] for record in current_catalog_records}) != 50:
        raise ValueError('건물 구조 가이드는 고유한 50종이어야 합니다.')
    for current_structure_record in current_catalog_records:
        if set(current_structure_record) != {'id','width','depth','floors','roof','roofRise','entrance','doorWidth','doorHeight'}:
            raise ValueError('건물 구조 필드 오류')
        if any(type(current_structure_record[key]) is not int for key in ('width','depth','floors','roofRise','doorWidth','doorHeight')):
            raise ValueError('건물 구조 수치 자료형 오류')
        if not (2 <= current_structure_record['width'] <= current_structure_record['depth'] <= 5) or current_structure_record['floors'] not in (1,2) or current_structure_record['roof'] not in ('gable','hip','shed') or current_structure_record['entrance'] not in ('south','east') or current_structure_record['doorHeight'] != 64 or current_structure_record['roofRise'] <= 0:
            raise ValueError('건물 구조 규격 오류')
        current_entry_span = current_structure_record['width' if current_structure_record['entrance']=='south' else 'depth']
        if current_structure_record['doorWidth'] != (1 if current_entry_span<=3 else 2):
            raise ValueError('문 폭 규격 오류')
    return {record['id']:record for record in current_catalog_records}


BUILDING_STRUCTURE_RECORDS = read_building_structure_catalog()
BUILDING_LAYOUT_PRESET_NAMES = tuple(BUILDING_STRUCTURE_RECORDS)


def describe_building_structure_label(current_preset_name):
    current_structure_record = BUILDING_STRUCTURE_RECORDS[current_preset_name]
    current_roof_label = {'gable':'박공','hip':'우진각','shed':'외쪽'}[current_structure_record['roof']]
    current_entrance_label = '왼쪽(남쪽)' if current_structure_record['entrance']=='south' else '오른쪽(동쪽)'
    return f"{current_structure_record['width']}x{current_structure_record['depth']} · {current_roof_label} · {current_structure_record['floors']}층 · {current_structure_record['floors']*80}px · {current_entrance_label} 입구"


def load_building_layout_preset(current_preset_name, current_height_pixels=None):
    from PIL import Image
    if current_preset_name not in BUILDING_STRUCTURE_RECORDS:
        raise ValueError('폐기되었거나 등록되지 않은 건물 구조 가이드입니다.')
    if current_height_pixels is not None and current_height_pixels != BUILDING_STRUCTURE_RECORDS[current_preset_name]['floors']*80:
        raise ValueError('가이드에 고정된 층 높이와 다릅니다.')
    with Image.open(BUILDING_STRUCTURE_ROOT / (current_preset_name+'.png')) as current_image_value:
        return current_image_value.copy()
