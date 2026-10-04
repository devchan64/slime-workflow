"""게임의 잠금 버전을 에셋 저장소에서 직접 검증한다."""
import re
from pathlib import Path
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader, load_registered_tiles, resolve_registered_asset, select_sprite_source_prefix
import yaml


def load_locked_sprite_sources(frontend_repository_path):
    lock_document_record = yaml.load((frontend_repository_path/'sprite-assets.lock.yaml').read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(lock_document_record, dict) or set(lock_document_record) != {'schema_version', 'repository', 'files'} or lock_document_record['schema_version'] != 1 or lock_document_record['repository'] != 'slime-assets' or not isinstance(lock_document_record['files'], list):
        raise ValueError('스프라이트 잠금 문서 형식 오류')
    asset_repository_path, registered_asset_records = load_registered_tiles()
    locked_source_records = {}
    for current_lock_record in lock_document_record['files']:
        if not isinstance(current_lock_record, dict) or set(current_lock_record) != {'path', 'source_path', 'sha256'}:
            raise ValueError('스프라이트 잠금 항목 필드 오류')
        target_relative_path = current_lock_record['path']
        if not isinstance(target_relative_path, str) or not re.fullmatch(r'assets/(characters|monsters|structures|effects)/[\w./-]+', target_relative_path) or '..' in Path(target_relative_path).parts or target_relative_path in locked_source_records:
            raise ValueError(f'스프라이트 전달 경로 오류 또는 중복: {target_relative_path!r}')
        sprite_directory_prefix = select_sprite_source_prefix(current_lock_record['source_path'])
        source_file_path, source_provenance_record = resolve_registered_asset(current_lock_record['source_path'], asset_repository_path, registered_asset_records, sprite_directory_prefix)
        if current_lock_record['sha256'] != source_provenance_record['sha256']:
            raise ValueError('스프라이트 원본과 잠금 해시 불일치')
        locked_source_records[target_relative_path] = (source_file_path, source_provenance_record)
    return asset_repository_path/'assets', locked_source_records


def load_review_sprite_sources(frontend_repository_path):
    """게임 잠금 원본과 모든 등록 캐릭터 애니메이션을 검수 대상으로 모은다."""
    registered_asset_root, locked_source_records = load_locked_sprite_sources(frontend_repository_path)
    review_source_records = dict(locked_source_records)
    asset_repository_path, registered_asset_records = load_registered_tiles()
    existing_source_paths = {current_source_path for current_source_path, _ in review_source_records.values()}
    for current_relative_path in sorted(registered_asset_records):
        current_path_parts = Path(current_relative_path).parts
        if len(current_path_parts) < 5 or current_path_parts[:2] != ('assets', 'characters') or current_path_parts[3] != 'animations':
            continue
        current_source_path = (asset_repository_path/current_relative_path).resolve()
        if current_source_path in existing_source_paths:
            continue
        if current_relative_path in review_source_records:
            raise ValueError(f'검수 스프라이트 논리 경로 충돌: {current_relative_path}')
        review_source_records[current_relative_path] = resolve_registered_asset(current_relative_path, asset_repository_path, registered_asset_records, 'assets/characters')
        existing_source_paths.add(current_source_path)
    return registered_asset_root, review_source_records
