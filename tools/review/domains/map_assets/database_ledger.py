"""개발 DB의 검증된 데이터를 에셋 저장소의 배포 원장으로 반영한다."""
from copy import deepcopy
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


PUBLIC_LEDGER_PAYLOAD_FIELDS = frozenset(('schemaVersion','generation','types','assets','mapDocuments','mapRevisions','buildingProperties','effects'))
PUBLIC_MAP_ROOT_DOCUMENTS = frozenset(('world-map.yaml', 'battlefield_encounters.yaml'))
PUBLIC_MAP_LEDGER_DIRECTORIES = frozenset(('map_names','field_tiles','map_spawns','city_layouts','field_waypoints','terrain'))


def validate_public_ledger_payload(current_payload_record):
    """공개 원장 전달의 최상위 필드와 맵 경로를 제한한다."""
    if not isinstance(current_payload_record,dict) or set(current_payload_record)!=PUBLIC_LEDGER_PAYLOAD_FIELDS:
        raise ValueError('공개 원장 전달 필드가 올바르지 않습니다.')
    if type(current_payload_record['schemaVersion']) is not int or current_payload_record['schemaVersion']!=1:
        raise ValueError('공개 원장 계약 버전 오류')
    if type(current_payload_record['generation']) is not int or current_payload_record['generation']<0:
        raise ValueError('공개 원장 세대 오류')
    for current_mapping_name in ('types','mapDocuments','mapRevisions','buildingProperties'):
        if not isinstance(current_payload_record[current_mapping_name],dict):
            raise ValueError('공개 원장 매핑 형식 오류: '+current_mapping_name)
    if not isinstance(current_payload_record['assets'],list) or not isinstance(current_payload_record['effects'],list):
        raise ValueError('공개 원장 에셋 목록 형식 오류')
    if set(current_payload_record['mapDocuments'])!=set(current_payload_record['mapRevisions']):
        raise ValueError('맵 원장과 revision 목록이 일치하지 않습니다.')
    for current_document_name,current_document_record in current_payload_record['mapDocuments'].items():
        if not isinstance(current_document_name,str):
            raise ValueError('맵 원장 경로는 문자열이어야 합니다.')
        current_document_path=Path(current_document_name)
        if (current_document_path.is_absolute() or '..' in current_document_path.parts
                or (current_document_name not in PUBLIC_MAP_ROOT_DOCUMENTS and
                    (len(current_document_path.parts)<2 or current_document_path.parts[0] not in PUBLIC_MAP_LEDGER_DIRECTORIES))
                or current_document_path.suffix!='.yaml' or current_document_path.as_posix()!=current_document_name):
            raise ValueError('공개 맵 원장 허용 경로가 아닙니다: '+current_document_name)
        if not isinstance(current_document_record,dict) or set(current_document_record)!={'managementId','data'} or not isinstance(current_document_record['data'],dict):
            raise ValueError('맵 원장 문서 형식 오류')
        current_revision_value=current_payload_record['mapRevisions'][current_document_name]
        if type(current_revision_value) is not int or current_revision_value<1:
            raise ValueError('맵 원장 revision 오류')


def publish_content_asset_ledger(current_asset_root, current_payload_record):
    current_asset_root=Path(current_asset_root).resolve(strict=True)
    validate_public_ledger_payload(current_payload_record)
    current_property_path=Path('assets/maps/sprite-display-properties.yaml')
    current_registry_path=current_asset_root/'asset-registry.yaml'
    if current_registry_path.is_symlink() or not current_registry_path.resolve().is_relative_to(current_asset_root):
        raise ValueError('에셋 등록부 경로 이탈')
    current_registry_record=load_unique_yaml_document(current_registry_path)
    current_catalog_record=load_billboard_catalog(current_asset_root)
    current_catalog_record['review_categories']=current_payload_record['types']
    current_asset_lookup=resolve_active_ledger_assets(current_payload_record['assets'],current_catalog_record['billboards'])
    # 이미지 내용은 저장 단계에서 게시되고 원장은 지연 동기화한다.
    for current_catalog_asset in current_catalog_record['billboards']:
        current_database_image=current_asset_lookup[current_catalog_asset['texture_key']]['image']
        current_source_record=current_catalog_asset['source_file']
        current_image_path=current_asset_root/current_database_image['path']
        if current_database_image['path']!=current_source_record['path'] and current_database_image['path']!='assets/billboards/versions/'+current_database_image['sha256']+'.png':
            raise ValueError('불변 이미지 버전 경로가 아닙니다: '+current_catalog_asset['texture_key'])
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
        if current_database_image['imageId']!=current_asset_reference['management_id']:
            raise ValueError('이미지 관리 ID 변경은 별도 등록이 필요합니다.')
        current_new_registry_record=deepcopy(current_registry_matches[0])
        current_new_registry_record.update({current_field_name:current_database_image[current_field_name] for current_field_name in ('path','sha256','width','height','version')})
        current_existing_versions=[current_entry_record for current_entry_record in current_registry_record['assets']
            if current_entry_record['managementId']==current_database_image['imageId'] and current_entry_record['version']==current_database_image['version']]
        if current_existing_versions:
            if len(current_existing_versions)!=1 or any(current_existing_versions[0][current_field_name]!=current_new_registry_record[current_field_name]
                    for current_field_name in ('path','sha256','width','height')):
                raise ValueError('등록된 불변 이미지 버전의 내용 불일치')
        else:
            current_registry_record['assets'].append(current_new_registry_record)
        current_asset_reference['version']=current_database_image['version']
        current_catalog_asset['source_file']={current_field_name:current_database_image[current_field_name] for current_field_name in ('path','sha256','width','height')}
    # 폐기된 에셋은 원본 파일·등록 이력을 보존하고 활성 카탈로그에서 제외한다.
    current_retired_identifiers={current_asset_identifier for current_asset_identifier,current_asset_record in current_asset_lookup.items()
        if current_asset_record['retired']}
    for current_catalog_asset in current_catalog_record['billboards']:
        if current_catalog_asset['texture_key'] not in current_retired_identifiers:
            continue
        current_asset_reference=current_catalog_asset['asset_ref']
        current_registry_entry=next(current_entry_record for current_entry_record in current_registry_record['assets']
            if current_entry_record['managementId']==current_asset_reference['management_id']
            and current_entry_record['version']==current_asset_reference['version'])
        current_registry_entry.setdefault('source',{})['lifecycle_status']='retired'
    current_catalog_record['billboards']=[current_catalog_asset for current_catalog_asset in current_catalog_record['billboards']
        if current_catalog_asset['texture_key'] not in current_retired_identifiers]
    current_asset_lookup={current_asset_identifier:current_asset_record for current_asset_identifier,current_asset_record in current_asset_lookup.items()
        if current_asset_identifier not in current_retired_identifiers}
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
        for current_record_list in current_metadata_lists:
            current_matching_records=[current_file_record for current_file_record in current_record_list if current_file_record['path']==current_relative_name]
            if len(current_matching_records)!=1 or current_matching_records[0]['sha256']!=current_old_hash:
                raise ValueError('원장 등록부·잠금 해시 불일치: '+current_relative_name)
            current_matching_records[0]['sha256']=current_new_hash
    for current_metadata_path,current_metadata_record in ((current_registry_path,current_registry_record),):
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
        if current_target_path.is_symlink() or not current_target_path.resolve().is_relative_to(current_asset_root):
            raise ValueError('원장 반영 대상 경로 이탈')
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
    return {'generation':current_payload_record['generation'],'updatedFiles':len(current_pending_files),
        'changedFiles':[{'path':current_target_path.relative_to(current_asset_root).as_posix(),
            'beforeSha256':hashlib.sha256(current_original_files[current_target_path]).hexdigest() if current_original_files[current_target_path] is not None else None,
            'afterSha256':hashlib.sha256(current_file_bytes).hexdigest()}
            for current_target_path,current_file_bytes in sorted(current_pending_files.items())],
        'consumerLocksUpdated':False}


def resolve_active_ledger_assets(current_database_assets,current_catalog_assets):
    """DB의 폐기 이력은 보존하되 활성 원장으로 다시 게시하지 않는다."""
    current_catalog_identifiers={current_asset_record['texture_key'] for current_asset_record in current_catalog_assets}
    current_asset_lookup={current_asset_record['assetId']:current_asset_record for current_asset_record in current_database_assets if not current_asset_record['retired'] or current_asset_record['assetId'] in current_catalog_identifiers}
    if set(current_asset_lookup)!=current_catalog_identifiers:
        raise ValueError('DB와 원장의 활성 빌보드 ID가 다릅니다. 등록·폐기 원장을 먼저 정리하세요.')
    return current_asset_lookup
