"""명시적으로 전달한 게임 UI 검수 빌드를 검증하고 독립 사본으로 가져온다."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

BUNDLE_ALLOWED_SUFFIXES = {'.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.svg', '.woff', '.woff2'}


def reject_manifest_duplicates(current_field_pairs):
    parsed_manifest_object = {}
    for current_field_name, current_field_value in current_field_pairs:
        if current_field_name in parsed_manifest_object:
            raise ValueError(f'검수 manifest 중복 필드: {current_field_name}')
        parsed_manifest_object[current_field_name] = current_field_value
    return parsed_manifest_object


def validate_bundle_path(current_relative_path):
    if not isinstance(current_relative_path, str) or not current_relative_path or '\\' in current_relative_path:
        raise ValueError('검수 파일 경로 형식 오류')
    parsed_relative_path = PurePosixPath(current_relative_path)
    if parsed_relative_path.is_absolute() or any(current_path_part.startswith('.') for current_path_part in parsed_relative_path.parts) or str(parsed_relative_path) != current_relative_path or parsed_relative_path.suffix not in BUNDLE_ALLOWED_SUFFIXES:
        raise ValueError(f'허용되지 않는 검수 경로: {current_relative_path}')
    return parsed_relative_path


def load_ui_bundle(source_bundle_directory):
    source_bundle_directory = Path(source_bundle_directory).resolve()
    manifest_source_bytes = (source_bundle_directory/'manifest.json').read_bytes()
    bundle_manifest_data = json.loads(manifest_source_bytes, object_pairs_hook=reject_manifest_duplicates)
    expected_manifest_fields = {'schemaVersion', 'kind', 'sourceCommit', 'sourceDirty', 'createdAt', 'pages', 'files'}
    if not isinstance(bundle_manifest_data, dict) or set(bundle_manifest_data) != expected_manifest_fields or type(bundle_manifest_data['schemaVersion']) is not int or bundle_manifest_data['schemaVersion'] != 1 or bundle_manifest_data['kind'] != 'slime-ui-review':
        raise ValueError('지원하지 않는 UI 검수 manifest')
    if not isinstance(bundle_manifest_data['sourceCommit'], str) or not re.fullmatch('[a-f0-9]{40}', bundle_manifest_data['sourceCommit']) or type(bundle_manifest_data['sourceDirty']) is not bool or not isinstance(bundle_manifest_data['createdAt'], str):
        raise ValueError('검수 출처 형식 오류')
    if not isinstance(bundle_manifest_data['files'], list) or not bundle_manifest_data['files'] or not isinstance(bundle_manifest_data['pages'], list) or not bundle_manifest_data['pages']:
        raise ValueError('검수 파일 또는 페이지 목록 누락')
    validated_bundle_files = {}
    for current_file_record in bundle_manifest_data['files']:
        if not isinstance(current_file_record, dict) or set(current_file_record) != {'path', 'sha256'}:
            raise ValueError('검수 파일 항목 형식 오류')
        current_relative_path = current_file_record['path']
        validate_bundle_path(current_relative_path)
        current_source_path = source_bundle_directory/current_relative_path
        if current_relative_path in validated_bundle_files or not current_source_path.resolve().is_relative_to(source_bundle_directory) or any(current_parent_path.is_symlink() for current_parent_path in (current_source_path, *current_source_path.parents)):
            raise ValueError(f'중복 파일 또는 심볼릭 링크: {current_relative_path}')
        current_source_bytes = current_source_path.read_bytes()
        if hashlib.sha256(current_source_bytes).hexdigest() != current_file_record['sha256']:
            raise ValueError(f'검수 파일 해시 불일치: {current_relative_path}')
        validated_bundle_files[current_relative_path] = current_source_bytes
    registered_page_identifiers = set()
    for current_page_record in bundle_manifest_data['pages']:
        if not isinstance(current_page_record, dict) or set(current_page_record) != {'id', 'label', 'path'} or any(not isinstance(current_page_record[current_field_name], str) or not current_page_record[current_field_name].strip() for current_field_name in ('id', 'label', 'path')):
            raise ValueError('검수 페이지 형식 오류')
        if not re.fullmatch('[a-z][a-z0-9-]+', current_page_record['id']) or current_page_record['id'] in registered_page_identifiers:
            raise ValueError('검수 페이지 ID 중복 또는 형식 오류')
        parsed_page_location = urlsplit(current_page_record['path'])
        if parsed_page_location.scheme or parsed_page_location.netloc or parsed_page_location.fragment or parsed_page_location.path not in validated_bundle_files or not parsed_page_location.path.endswith('.html'):
            raise ValueError('검수 진입 HTML 누락 또는 외부 주소')
        registered_page_identifiers.add(current_page_record['id'])
    return bundle_manifest_data, validated_bundle_files, manifest_source_bytes


def import_ui_bundle(source_bundle_directory, output_review_directory, emit_review_trace):
    bundle_manifest_data, validated_bundle_files, manifest_source_bytes = load_ui_bundle(source_bundle_directory)
    bundle_content_digest = hashlib.sha256(manifest_source_bytes).hexdigest()
    destination_bundle_name = 'ui-'+bundle_content_digest[:16]
    destination_bundle_root = output_review_directory/destination_bundle_name
    destination_bundle_root.mkdir(exist_ok=False)
    for current_relative_path, current_source_bytes in validated_bundle_files.items():
        destination_file_path = destination_bundle_root/current_relative_path
        destination_file_path.parent.mkdir(parents=True, exist_ok=True)
        destination_file_path.write_bytes(current_source_bytes)
    (destination_bundle_root/'manifest.json').write_bytes(manifest_source_bytes)
    emit_review_trace('ui-bundle', f'{destination_bundle_name} files={len(validated_bundle_files)} commit={bundle_manifest_data["sourceCommit"]}')
    return [{'id': destination_bundle_name+'-'+current_page_record['id'], 'label': current_page_record['label'], 'path': destination_bundle_name+'/'+current_page_record['path'], 'category': 'game-ui', 'anchorEditor': False, 'description': f'{bundle_manifest_data["sourceCommit"]} · {"로컬 수정 포함" if bundle_manifest_data["sourceDirty"] else "커밋 원본"} · {bundle_manifest_data["createdAt"]} · {bundle_content_digest}'} for current_page_record in bundle_manifest_data['pages']]
