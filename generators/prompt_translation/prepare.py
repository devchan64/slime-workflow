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


def calculate_file_sha256(translation_file_path):
    translation_digest_value = hashlib.sha256()
    with translation_file_path.open('rb') as translation_file_handle:
        for translation_file_chunk in iter(lambda: translation_file_handle.read(1024 * 1024), b''):
            translation_digest_value.update(translation_file_chunk)
    return translation_digest_value.hexdigest()


def prepare_translation_model(translation_revision_value):
    if not re.fullmatch(r'[0-9a-f]{40}', translation_revision_value):
        raise ValueError('Hugging Face의 40자리 커밋 리비전을 지정하세요.')
    from huggingface_hub import snapshot_download
    translation_snapshot_path = Path(snapshot_download(repo_id='google/translategemma-4b-it', revision=translation_revision_value))
    translation_file_records = {}
    for translation_file_path in sorted(translation_snapshot_path.rglob('*')):
        if translation_file_path.is_file():
            translation_file_records[str(translation_file_path.relative_to(translation_snapshot_path))] = calculate_file_sha256(translation_file_path)
    if not any(current_name.endswith('.safetensors') for current_name in translation_file_records):
        raise ValueError('모델 가중치를 찾을 수 없습니다.')
    TRANSLATION_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    write_record_atomically(TRANSLATION_MODEL_ROOT / 'manifest.json', {'model_id': 'google/translategemma-4b-it', 'revision': translation_revision_value, 'snapshot': str(translation_snapshot_path), 'files': translation_file_records})


if __name__ == '__main__':
    translation_argument_parser = argparse.ArgumentParser(description=__doc__)
    translation_argument_parser.add_argument('--revision', required=True)
    prepare_translation_model(translation_argument_parser.parse_args().revision)
