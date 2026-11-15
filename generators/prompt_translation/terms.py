"""승인 용어와 번역 결과의 불일치를 검토한다."""
from pathlib import Path
import re
import yaml

TRANSLATION_GLOSSARY_PATH = Path(__file__).with_name('glossary.yaml')


def validate_translation_glossary(translation_glossary_values):
    if not isinstance(translation_glossary_values, list) or len(translation_glossary_values) > 50:
        raise ValueError('용어는 최대 50개까지 지정할 수 있습니다.')
    translation_seen_sources = set()
    for translation_term_record in translation_glossary_values:
        if not isinstance(translation_term_record, dict) or set(translation_term_record) != {'source', 'target'}:
            raise ValueError('용어 항목은 원문과 번역어가 필요합니다.')
        for current_term_value in translation_term_record.values():
            if not isinstance(current_term_value, str) or not current_term_value.strip() or current_term_value != current_term_value.strip() or len(current_term_value) > 100 or '\n' in current_term_value or '\r' in current_term_value:
                raise ValueError('용어 원문과 번역어는 한 줄의 1~100자여야 합니다.')
        if translation_term_record['source'] in translation_seen_sources:
            raise ValueError('같은 원문 용어를 중복 지정할 수 없습니다.')
        translation_seen_sources.add(translation_term_record['source'])
    return translation_glossary_values


def load_approved_translation_terms(translation_target_language):
    from generators.writer_agent.documents import read_yaml_document
    translation_registry_value = read_yaml_document(TRANSLATION_GLOSSARY_PATH)
    if not isinstance(translation_registry_value, dict) or set(translation_registry_value) != {'version', 'terms'} or translation_registry_value['version'] != 1 or not isinstance(translation_registry_value['terms'], list):
        raise ValueError('승인 용어집 형식 오류')
    translation_approved_records = []
    for translation_term_record in translation_registry_value['terms']:
        if not isinstance(translation_term_record, dict) or set(translation_term_record) != {'source', 'targets', 'source_ref', 'status'} or translation_term_record['status'] != 'approved' or not isinstance(translation_term_record['targets'], dict) or set(translation_term_record['targets']) - {'en','zh-CN'} or not isinstance(translation_term_record['source_ref'],str) or not translation_term_record['source_ref'] or translation_term_record['source_ref'].startswith('/') or '..' in Path(translation_term_record['source_ref']).parts:
            raise ValueError('승인 용어 항목 오류')
        for current_language, current_target in translation_term_record['targets'].items():
            validate_translation_glossary([{'source': translation_term_record['source'], 'target': current_target}])
        translation_reference_path = Path(__file__).resolve().parents[3] / translation_term_record['source_ref']
        translation_is_map_reference = translation_term_record['source_ref'].startswith('slime-assets/assets/maps/map_names/')
        translation_is_prompt_reference = translation_term_record['source_ref'] in {'slime-workflow/prompts/common/art-style-v1.5.0.yaml', 'slime-workflow/prompts/common/character-appearance-v1.2.0.yaml'}
        if not (translation_is_map_reference or translation_is_prompt_reference) or translation_reference_path.is_symlink():
            raise ValueError('승인 용어 출처 경로 오류')
        translation_reference_record = read_yaml_document(translation_reference_path)
        if translation_is_map_reference:
            translation_reference_matches = isinstance(translation_reference_record, dict) and isinstance(translation_reference_record.get('data'), dict) and translation_reference_record['data'].get('ko') == translation_term_record['source'] and all(translation_reference_record['data'].get(current_language) == current_target for current_language, current_target in translation_term_record['targets'].items())
        else:
            translation_reference_matches = isinstance(translation_reference_record, dict) and isinstance(translation_reference_record.get('prompt_ko'), str) and isinstance(translation_reference_record.get('prompt'), str) and translation_term_record['source'] in translation_reference_record['prompt_ko'] and set(translation_term_record['targets']) == {'en'} and translation_term_record['targets']['en'] in translation_reference_record['prompt']
        if not translation_reference_matches:
            raise ValueError('승인 용어가 출처와 다릅니다. 용어집을 갱신하세요.')
        if translation_target_language in translation_term_record['targets']:
            translation_approved_records.append({'source':translation_term_record['source'], 'target':translation_term_record['targets'][translation_target_language], 'source_ref':translation_term_record['source_ref']})
    validate_translation_glossary([{'source': current_term['source'], 'target': current_term['target']} for current_term in translation_approved_records])
    return translation_approved_records


def compare_translation_terms(translation_source_text, translation_result_text, translation_term_records):
    translation_comparison_records = []
    for translation_term_record in translation_term_records:
        translation_source_count = translation_source_text.count(translation_term_record['source'])
        if not translation_source_count:
            continue
        translation_target_pattern = re.escape(translation_term_record['target'])
        if re.match(r'[A-Za-z0-9]', translation_term_record['target']):
            translation_target_pattern = r'(?<![A-Za-z0-9])' + translation_target_pattern
        if re.search(r'[A-Za-z0-9]$', translation_term_record['target']):
            translation_target_pattern += r'(?![A-Za-z0-9])'
        translation_target_count = len(re.findall(translation_target_pattern, translation_result_text, re.IGNORECASE))
        translation_comparison_records.append({**translation_term_record, 'source_count':translation_source_count, 'target_count':translation_target_count, 'status':'matched' if translation_target_count >= translation_source_count else 'mismatch'})
    return translation_comparison_records
