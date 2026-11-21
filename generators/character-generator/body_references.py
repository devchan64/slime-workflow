"""캐릭터 신체 비율 기준의 카탈로그와 출처 검증."""
import base64
import hashlib
import io
import re
from pathlib import Path

from PIL import Image
from tools.management.common.map_tile_assets import UniqueAssetYamlLoader
import yaml

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
BODY_REFERENCE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / 'baseline/mannequin'
BODY_CATALOG_PATH = BODY_REFERENCE_DIRECTORY / 'body-reference-catalog.yaml'
BODY_REFERENCE_ROLE_PROMPT = 'Use image 1 for body proportions only; follow the requested character appearance.'


def load_body_reference_catalog():
    current_catalog_record = yaml.load(BODY_CATALOG_PATH.read_text(encoding='utf-8'), Loader=UniqueAssetYamlLoader)
    if not isinstance(current_catalog_record, dict) or set(current_catalog_record) != {'schema_version', 'references'} or type(current_catalog_record['schema_version']) is not int or current_catalog_record['schema_version'] != 1 or not isinstance(current_catalog_record['references'], list):
        raise ValueError('신체 비율 참조 목록 형식 오류')
    current_seen_ids = set()
    for current_reference_record in current_catalog_record['references']:
        if not isinstance(current_reference_record, dict) or set(current_reference_record) != {'id', 'version', 'label', 'image', 'sha256', 'source', 'role'} or any(not isinstance(current_value, str) or not current_value.strip() for current_value in current_reference_record.values()):
            raise ValueError('신체 비율 참조 항목 형식 오류')
        current_reference_id = current_reference_record['id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', current_reference_id) or current_reference_id in current_seen_ids or not re.fullmatch(r'\d+\.\d+\.\d+', current_reference_record['version']) or not re.fullmatch(r'[a-f0-9]{64}', current_reference_record['sha256']):
            raise ValueError('신체 비율 참조 식별자·버전·해시 오류')
        current_seen_ids.add(current_reference_id)
        current_image_name = current_reference_record['image']
        if Path(current_image_name).name != current_image_name or not current_image_name.endswith('.png'):
            raise ValueError('신체 비율 참조 경로 오류')
        current_image_path = BODY_REFERENCE_DIRECTORY / current_image_name
        if current_image_path.is_symlink() or hashlib.sha256(current_image_path.read_bytes()).hexdigest() != current_reference_record['sha256']:
            raise ValueError('신체 비율 참조 이미지 해시 불일치')
    if not current_seen_ids:
        raise ValueError('신체 비율 참조 목록이 비었습니다.')
    return current_catalog_record['references']


def load_body_reference_image(current_reference_id):
    current_reference_record = next((current_record for current_record in load_body_reference_catalog() if current_record['id'] == current_reference_id), None)
    if current_reference_record is None:
        raise ValueError('등록되지 않은 신체 비율 참조입니다.')
    with Image.open(BODY_REFERENCE_DIRECTORY / current_reference_record['image']) as current_image_value:
        return current_image_value.convert('RGB').copy()


def calculate_reference_pixel_hash(current_image_bytes):
    with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
        current_rgb_image = current_image_value.convert('RGB')
        return hashlib.sha256(f'{current_rgb_image.width}x{current_rgb_image.height}:RGB:'.encode() + current_rgb_image.tobytes()).hexdigest()


def identify_body_reference_images(current_image_values):
    if not current_image_values:
        return []
    current_reference_records = load_body_reference_catalog()
    current_known_pixels = {calculate_reference_pixel_hash((BODY_REFERENCE_DIRECTORY / current_record['image']).read_bytes()): current_record for current_record in current_reference_records}
    current_matches = []
    for current_image_index, current_image_value in enumerate(current_image_values, 1):
        current_pixel_hash = calculate_reference_pixel_hash(base64.b64decode(current_image_value, validate=True))
        if current_pixel_hash in current_known_pixels:
            current_record = current_known_pixels[current_pixel_hash]
            current_matches.append({'order': current_image_index, 'id': current_record['id'], 'version': current_record['version'], 'source': 'baseline/mannequin/' + current_record['image'], 'source_sha256': current_record['sha256'], 'pixel_sha256': current_pixel_hash, 'role': '신체 비율 참고'})
    return current_matches


def verify_body_reference_history(current_job_root, current_request_record):
    current_reference_records = current_request_record.get('body_reference_sources', [])
    if not isinstance(current_reference_records, list):
        raise ValueError('신체 비율 참조 출처 형식 오류')
    for current_record in current_reference_records:
        if not isinstance(current_record, dict) or set(current_record) != {'order', 'id', 'version', 'source', 'source_sha256', 'pixel_sha256', 'role'} or type(current_record['order']) is not int or not 1 <= current_record['order'] <= len(current_request_record['references']):
            raise ValueError('저장된 신체 비율 참조 출처 오류')
        if not isinstance(current_record['id'], str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', current_record['id']) or not isinstance(current_record['version'], str) or not re.fullmatch(r'\d+\.\d+\.\d+', current_record['version']) or not isinstance(current_record['source'], str) or not re.fullmatch(r'(?:baseline/mannequin|prompts/references/mannequin/latest)/[a-z0-9-]+\.png', current_record['source']) or any(not isinstance(current_record[current_hash_field], str) or not re.fullmatch(r'[a-f0-9]{64}', current_record[current_hash_field]) for current_hash_field in ('source_sha256', 'pixel_sha256')) or current_record['role'] != '신체 비율 참고':
            raise ValueError('저장된 신체 비율 참조 출처 필드 오류')
        current_image_path = Path(current_job_root) / f"reference-{current_record['order']}.png"
        if calculate_reference_pixel_hash(current_image_path.read_bytes()) != current_record['pixel_sha256']:
            raise ValueError('저장된 신체 비율 참조 이미지 불일치')
