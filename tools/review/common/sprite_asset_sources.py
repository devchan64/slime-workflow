"""게임의 잠금 버전을 에셋 저장소에서 직접 검증한다."""
import re
from pathlib import Path
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader, load_registered_tiles, resolve_registered_asset
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
        if not isinstance(target_relative_path, str) or not re.fullmatch(r'src/assets/(characters|monsters|structures)/[\w./-]+', target_relative_path) or '..' in Path(target_relative_path).parts or target_relative_path in locked_source_records:
            raise ValueError('스프라이트 전달 경로 오류 또는 중복')
        source_file_path, source_provenance_record = resolve_registered_asset(current_lock_record['source_path'], asset_repository_path, registered_asset_records, 'assets/sprites')
        if current_lock_record['sha256'] != source_provenance_record['sha256']:
            raise ValueError('스프라이트 원본과 잠금 해시 불일치')
        locked_source_records[target_relative_path] = (source_file_path, source_provenance_record)
    return asset_repository_path/'assets/sprites', locked_source_records
