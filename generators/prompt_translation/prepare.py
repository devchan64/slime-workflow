"""동의된 Hugging Face 계정으로 고정 리비전 모델을 준비한다."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.translation.service import TRANSLATION_MODEL_ROOT

TRANSLATION_MODEL_REVISION = '10042cb0e6e7fdce748996a71dc3dc432a4e0c89'


def calculate_file_sha256(translation_file_path):
    translation_digest_value = hashlib.sha256()
    with translation_file_path.open('rb') as translation_file_handle:
        for translation_file_chunk in iter(lambda: translation_file_handle.read(1024 * 1024), b''):
            translation_digest_value.update(translation_file_chunk)
    return translation_digest_value.hexdigest()


def prepare_translation_model(translation_revision_value=TRANSLATION_MODEL_REVISION):
    if not re.fullmatch(r'[0-9a-f]{40}', translation_revision_value):
        raise ValueError('Hugging Face의 40자리 커밋 리비전을 지정하세요.')
    from tools.review.common.model_huggingface_download import tracked_snapshot_download
    translation_snapshot_path = TRANSLATION_MODEL_ROOT / translation_revision_value
    translation_snapshot_path.mkdir(parents=True, exist_ok=True)
    tracked_snapshot_download(repo_id='google/translategemma-4b-it', revision=translation_revision_value, local_dir=str(translation_snapshot_path), allow_patterns=['*.json', '*.jinja', '*.model', '*.safetensors'])
    translation_file_records = {}
    for translation_file_path in sorted(translation_snapshot_path.rglob('*')):
        if translation_file_path.is_file() and not any(current_part.startswith('.') for current_part in translation_file_path.relative_to(translation_snapshot_path).parts):
            translation_file_records[str(translation_file_path.relative_to(translation_snapshot_path))] = calculate_file_sha256(translation_file_path)
    if not any(current_name.endswith('.safetensors') for current_name in translation_file_records):
        raise ValueError('모델 가중치를 찾을 수 없습니다.')
    TRANSLATION_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    write_record_atomically(TRANSLATION_MODEL_ROOT / 'manifest.json', {'model_id': 'google/translategemma-4b-it', 'revision': translation_revision_value, 'snapshot': str(translation_snapshot_path), 'files': translation_file_records})


def inspect_translation_model_files():
    try:
        translation_manifest_record = json.loads((TRANSLATION_MODEL_ROOT / 'manifest.json').read_text(encoding='utf-8'))
        translation_snapshot_path = TRANSLATION_MODEL_ROOT / TRANSLATION_MODEL_REVISION
        translation_file_records = translation_manifest_record['files']
        if translation_manifest_record['model_id'] != 'google/translategemma-4b-it' or translation_manifest_record['revision'] != TRANSLATION_MODEL_REVISION or Path(translation_manifest_record['snapshot']) != translation_snapshot_path or not isinstance(translation_file_records, dict):
            return False
        if not {'config.json', 'tokenizer.json', 'chat_template.jinja', 'model.safetensors.index.json'}.issubset(translation_file_records):
            return False
        translation_index_record = json.loads((translation_snapshot_path / 'model.safetensors.index.json').read_text())
        translation_shard_names = set(translation_index_record['weight_map'].values())
        if not translation_shard_names or not translation_shard_names.issubset(translation_file_records):
            return False
        return all(not Path(current_name).is_absolute() and '..' not in Path(current_name).parts and (translation_snapshot_path / current_name).is_file() and isinstance(current_hash, str) and re.fullmatch(r'[a-f0-9]{64}', current_hash) for current_name, current_hash in translation_file_records.items())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


if __name__ == '__main__':
    translation_argument_parser = argparse.ArgumentParser(description=__doc__)
    translation_argument_parser.add_argument('--revision', required=True)
    prepare_translation_model(translation_argument_parser.parse_args().revision)
