"""검증된 DB 스냅샷을 추적 원장으로 반영한다. 세대 보관 파일과 구분한다."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import yaml
from tools.review.maintenance.sync_billboard_catalog import (
    load_unique_yaml_document, load_billboard_catalog, build_catalog_reference,
    write_billboard_catalog, list_billboard_catalog_paths,
)
from tools.review.common.sprite_display_properties import validate_sprite_display_properties


def publish_content_asset_ledger(current_asset_root, current_payload_record):
    current_asset_root=Path(current_asset_root).resolve(strict=True)
    current_property_path=Path('assets/maps/sprite-display-properties.yaml')
    current_registry_path=current_asset_root/'asset-registry.yaml'
    current_backend_lock=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
    current_registry_record=load_unique_yaml_document(current_registry_path)
    current_lock_record=load_unique_yaml_document(current_backend_lock)
    current_catalog_record=load_billboard_catalog(current_asset_root)
    current_asset_lookup={current_asset_record['assetId']:current_asset_record for current_asset_record in current_payload_record['assets']}
    if set(current_asset_lookup)!={current_asset_record['texture_key'] for current_asset_record in current_catalog_record['billboards']}:
        raise ValueError('DB와 원장의 빌보드 ID가 다릅니다. 등록·폐기 원장을 먼저 정리하세요.')
    current_property_document=load_unique_yaml_document(current_asset_root/current_property_path)
    current_property_document['data']={**current_payload_record['buildingProperties'],**{
        current_asset_identifier:current_asset_record['properties'] for current_asset_identifier,current_asset_record in current_asset_lookup.items()}}
    validate_sprite_display_properties(current_property_document['data'])
    current_source_documents={current_property_path:current_property_document}
    for current_document_name,current_document_value in current_payload_record['mapDocuments'].items():
        current_relative_path=Path(current_document_name)
        if current_relative_path.is_absolute() or '..' in current_relative_path.parts or current_relative_path.suffix!='.yaml':
            raise ValueError('원장 맵 상대 경로 오류')
        current_source_documents[Path('assets/maps')/current_relative_path]=current_document_value
    current_pending_files={}
    current_original_files={}
    for current_relative_path,current_document_value in current_source_documents.items():
        current_target_path=current_asset_root/current_relative_path
        if current_target_path.is_symlink() or not current_target_path.resolve().is_relative_to(current_asset_root):
            raise ValueError('원장 경로 이탈')
        current_original_files[current_target_path]=current_target_path.read_bytes()
        if load_unique_yaml_document(current_target_path)!=current_document_value:
            current_pending_files[current_target_path]=yaml.safe_dump(current_document_value,allow_unicode=True,sort_keys=False).encode()
    # 원본 내용과 등록 해시가 일치해야 갱신한다. 수동 편집을 조용히 덮지 않는다.
    for current_target_path,current_file_bytes in current_pending_files.items():
        current_relative_name=current_target_path.relative_to(current_asset_root).as_posix()
        current_old_hash=hashlib.sha256(current_original_files[current_target_path]).hexdigest()
        current_new_hash=hashlib.sha256(current_file_bytes).hexdigest()
        for current_record_list in (current_registry_record['assets'],current_lock_record['files']):
            current_matching_records=[current_file_record for current_file_record in current_record_list if current_file_record['path']==current_relative_name]
            if len(current_matching_records)!=1 or current_matching_records[0]['sha256']!=current_old_hash:
                raise ValueError('원장 등록부·잠금 해시 불일치: '+current_relative_name)
            current_matching_records[0]['sha256']=current_new_hash
    for current_metadata_path,current_metadata_record in ((current_registry_path,current_registry_record),(current_backend_lock,current_lock_record)):
        current_original_files[current_metadata_path]=current_metadata_path.read_bytes()
        if load_unique_yaml_document(current_metadata_path)!=current_metadata_record:
            current_pending_files[current_metadata_path]=yaml.safe_dump(current_metadata_record,allow_unicode=True,sort_keys=False).encode()
    with tempfile.TemporaryDirectory(prefix='content-ledger-') as current_temporary_name:
        current_staging_root=Path(current_temporary_name)
        shutil.copytree(current_asset_root/'assets/maps',current_staging_root/'assets/maps')
        shutil.copytree(current_asset_root/'assets/billboards',current_staging_root/'assets/billboards',ignore=shutil.ignore_patterns('*.png'))
        for current_image_path in (current_asset_root/'assets/billboards').rglob('*.png'):
            current_staged_image=current_staging_root/current_image_path.relative_to(current_asset_root)
            current_staged_image.parent.mkdir(parents=True,exist_ok=True)
            current_staged_image.symlink_to(current_image_path)
        (current_staging_root/'asset-registry.yaml').write_text(yaml.safe_dump(current_registry_record,allow_unicode=True,sort_keys=False))
        for current_target_path,current_file_bytes in current_pending_files.items():
            if current_target_path.is_relative_to(current_asset_root):
                (current_staging_root/current_target_path.relative_to(current_asset_root)).write_bytes(current_file_bytes)
        for current_catalog_asset in current_catalog_record['billboards']:
            current_database_asset=current_asset_lookup[current_catalog_asset['texture_key']]
            current_image_record=current_database_asset['image']
            if current_catalog_asset['source_file']['sha256']!=current_image_record['sha256']:
                raise ValueError('DB와 원장 이미지 버전이 다릅니다: '+current_database_asset['assetId'])
            current_catalog_asset['modeling']=current_database_asset['metadata']['modeling']
        write_billboard_catalog(current_staging_root,current_catalog_record)
        write_billboard_catalog(current_staging_root,build_catalog_reference(current_staging_root))
        for current_staged_path in list_billboard_catalog_paths(current_staging_root):
            current_target_path=current_asset_root/current_staged_path.relative_to(current_staging_root)
            current_original_files[current_target_path]=current_target_path.read_bytes()
            if current_target_path.read_bytes()!=current_staged_path.read_bytes():
                current_pending_files[current_target_path]=current_staged_path.read_bytes()
    for current_target_path,current_original_bytes in current_original_files.items():
        if current_target_path.read_bytes()!=current_original_bytes:
            raise ValueError('원장 반영 준비 중 파일이 변경되었습니다: '+str(current_target_path))
    try:
        for current_target_path,current_file_bytes in current_pending_files.items():
            current_temporary_path=current_target_path.with_suffix('.ledger-tmp')
            current_temporary_path.write_bytes(current_file_bytes)
            os.replace(current_temporary_path,current_target_path)
    except Exception:
        for current_target_path in current_pending_files:
            current_target_path.write_bytes(current_original_files[current_target_path])
        raise
    return {'generation':current_payload_record['generation'],'updatedFiles':len(current_pending_files)}
