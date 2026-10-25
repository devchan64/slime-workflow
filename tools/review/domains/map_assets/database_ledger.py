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
    current_catalog_record['review_categories']=current_payload_record['types']
    current_asset_lookup={current_asset_record['assetId']:current_asset_record for current_asset_record in current_payload_record['assets']}
    if set(current_asset_lookup)!={current_asset_record['texture_key'] for current_asset_record in current_catalog_record['billboards']}:
        raise ValueError('DB와 원장의 빌보드 ID가 다릅니다. 등록·폐기 원장을 먼저 정리하세요.')
    current_image_hash_changes={}
    # 이미지 내용은 저장 단계에서 게시되고 원장은 지연 동기화한다.
    for current_catalog_asset in current_catalog_record['billboards']:
        current_database_image=current_asset_lookup[current_catalog_asset['texture_key']]['image']
        current_source_record=current_catalog_asset['source_file']
        current_image_path=current_asset_root/current_database_image['path']
        if current_database_image['path']!=current_source_record['path']:
            raise ValueError('단일 원본 이미지 경로로 이관이 필요합니다: '+current_catalog_asset['texture_key'])
        if current_image_path.is_symlink() or not current_image_path.resolve().is_relative_to(current_asset_root) or hashlib.sha256(current_image_path.read_bytes()).hexdigest()!=current_database_image['sha256']:
            raise ValueError('DB 이미지와 실제 원본 해시가 다릅니다: '+current_catalog_asset['texture_key'])
        from PIL import Image
        with Image.open(current_image_path) as current_source_image:
            if list(current_source_image.size)!=[current_database_image['width'],current_database_image['height']]:
                raise ValueError('DB 이미지와 원본 크기가 다릅니다')
        current_asset_reference=current_catalog_asset['asset_ref']
        current_registry_matches=[current_entry_record for current_entry_record in current_registry_record['assets'] if current_entry_record['managementId']==current_asset_reference['management_id'] and current_entry_record['version']==current_asset_reference['version']]
        if len(current_registry_matches)!=1 or any(current_registry_matches[0][current_field_name]!=current_source_record[current_field_name] for current_field_name in ('path','sha256','width','height')):
            raise ValueError('이미지 등록부와 카탈로그가 다릅니다')
        current_image_hash_changes[current_source_record['sha256']]=current_database_image['sha256']
        current_registry_matches[0].update({current_field_name:current_database_image[current_field_name] for current_field_name in ('sha256','width','height')})
        current_catalog_asset['source_file']={current_field_name:current_database_image[current_field_name] for current_field_name in ('path','sha256','width','height')}
    current_property_document=load_unique_yaml_document(current_asset_root/current_property_path)
    current_property_document['data']={**current_payload_record['buildingProperties'],**{
        current_asset_identifier:current_asset_record['properties'] for current_asset_identifier,current_asset_record in current_asset_lookup.items()}}
    validate_sprite_display_properties(current_property_document['data'])
    current_source_documents={current_property_path:current_property_document}
    if 'effects' in current_payload_record:
        current_source_documents[Path('assets/sprites/effects/catalog.yaml')]={'schema_version':1,'category':'effects','name':'이펙트','effects':current_payload_record['effects']}
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
        current_metadata_lists=[current_registry_record['assets']]
        if current_relative_name.startswith('assets/maps/'):
            current_metadata_lists.append(current_lock_record['files'])
        for current_record_list in current_metadata_lists:
            current_matching_records=[current_file_record for current_file_record in current_record_list if current_file_record['path']==current_relative_name]
            if len(current_matching_records)!=1 or current_matching_records[0]['sha256']!=current_old_hash:
                raise ValueError('원장 등록부·잠금 해시 불일치: '+current_relative_name)
            current_matching_records[0]['sha256']=current_new_hash
    for current_metadata_path,current_metadata_record in ((current_registry_path,current_registry_record),(current_backend_lock,current_lock_record)):
        current_original_files[current_metadata_path]=current_metadata_path.read_bytes()
        if load_unique_yaml_document(current_metadata_path)!=current_metadata_record:
            current_pending_files[current_metadata_path]=yaml.safe_dump(current_metadata_record,allow_unicode=True,sort_keys=False).encode()
    for current_lock_name in ('map-assets.lock.yaml','sprite-assets.lock.yaml'):
        current_frontend_lock=current_asset_root.parent/'slime-frontend'/current_lock_name
        if not current_frontend_lock.exists():
            raise ValueError('프론트엔드 에셋 잠금 파일 누락: '+str(current_frontend_lock))
        current_original_files[current_frontend_lock]=current_frontend_lock.read_bytes()
        current_updated_text=current_original_files[current_frontend_lock].decode()
        for current_original_hash,current_updated_hash in current_image_hash_changes.items():
            current_updated_text=current_updated_text.replace(current_original_hash,current_updated_hash)
        if current_updated_text.encode()!=current_original_files[current_frontend_lock]:
            current_pending_files[current_frontend_lock]=current_updated_text.encode()
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
                current_staged_target=current_staging_root/current_target_path.relative_to(current_asset_root)
                current_staged_target.parent.mkdir(parents=True,exist_ok=True)
                current_staged_target.write_bytes(current_file_bytes)
        for current_catalog_asset in current_catalog_record['billboards']:
            current_database_asset=current_asset_lookup[current_catalog_asset['texture_key']]
            current_image_record=current_database_asset['image']
            if current_catalog_asset['source_file']['sha256']!=current_image_record['sha256']:
                raise ValueError('DB와 원장 이미지 버전이 다릅니다: '+current_database_asset['assetId'])
            current_catalog_asset['modeling']=current_database_asset['metadata']['modeling']
            current_catalog_asset['family']=current_database_asset['metadata']['family']
            current_catalog_record['families'][current_catalog_asset['family']]=current_database_asset['metadata']['familyDefinition']
        write_billboard_catalog(current_staging_root,current_catalog_record)
        write_billboard_catalog(current_staging_root,build_catalog_reference(current_staging_root))
        for current_staged_path in list_billboard_catalog_paths(current_staging_root):
            current_target_path=current_asset_root/current_staged_path.relative_to(current_staging_root)
            current_original_files[current_target_path]=current_target_path.read_bytes() if current_target_path.exists() else None
            if current_original_files[current_target_path]!=current_staged_path.read_bytes():
                current_pending_files[current_target_path]=current_staged_path.read_bytes()
    for current_target_path,current_original_bytes in current_original_files.items():
        if (current_target_path.read_bytes() if current_target_path.exists() else None)!=current_original_bytes:
            raise ValueError('원장 반영 준비 중 파일이 변경되었습니다: '+str(current_target_path))
    try:
        for current_target_path,current_file_bytes in current_pending_files.items():
            current_temporary_path=current_target_path.with_suffix('.ledger-tmp')
            current_temporary_path.write_bytes(current_file_bytes)
            os.replace(current_temporary_path,current_target_path)
    except Exception:
        for current_target_path in current_pending_files:
            if current_original_files[current_target_path] is None:
                current_target_path.unlink(missing_ok=True)
            else:
                current_target_path.write_bytes(current_original_files[current_target_path])
        raise
    return {'generation':current_payload_record['generation'],'updatedFiles':len(current_pending_files)}
