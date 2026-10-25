"""등록 원본을 백엔드 최초 적재용 전달 계약으로 변환한다."""
import hashlib
from pathlib import Path
from tools.review.maintenance.sync_billboard_catalog import load_billboard_catalog, load_unique_yaml_document
from tools.review.common.sprite_display_properties import validate_sprite_display_properties


def build_billboard_database_seed(current_asset_root, current_public_asset_prefix):
    """이미지 파일은 전송하지 않고 검증된 등록 참조만 전달한다."""
    current_asset_root = Path(current_asset_root).resolve()
    if not isinstance(current_public_asset_prefix,str) or not current_public_asset_prefix.startswith('/') or current_public_asset_prefix.startswith('//'):
        raise ValueError('정적 에셋 게시 경로는 /로 시작하는 동일 출처 경로여야 합니다.')
    current_catalog_record = load_billboard_catalog(current_asset_root)
    current_property_records = load_unique_yaml_document(current_asset_root/'assets/maps/sprite-display-properties.yaml')['data']
    validate_sprite_display_properties(current_property_records)
    current_asset_records = []
    for current_catalog_asset in current_catalog_record['billboards']:
        current_texture_identifier = current_catalog_asset['texture_key']
        current_family_record = current_catalog_record['families'][current_catalog_asset['family']]
        current_source_record = current_catalog_asset['source_file']
        current_source_path = (current_asset_root/current_source_record['path']).resolve()
        if not current_source_path.is_relative_to(current_asset_root):
            raise ValueError('에셋 원본 경로 이탈: '+current_texture_identifier)
        if hashlib.sha256(current_source_path.read_bytes()).hexdigest() != current_source_record['sha256']:
            raise ValueError('에셋 원본 해시 불일치: '+current_texture_identifier)
        current_asset_records.append({'assetId':current_texture_identifier,
            'assetType':current_family_record['review_category'],'name':current_family_record['name'],
            'image':{'imageId':current_catalog_asset['asset_ref']['management_id'],
                'version':current_catalog_asset['asset_ref']['version'],
                'path':current_source_record['path'],'sha256':current_source_record['sha256'],
                'width':current_source_record['width'],'height':current_source_record['height'],
                'publishedPath':current_public_asset_prefix.rstrip('/')+'/'+current_source_record['path']},
            'properties':current_property_records[current_texture_identifier],
            'metadata':{'family':current_catalog_asset['family'],'familyDefinition':current_family_record,
                'modeling':current_catalog_asset['modeling'],'mapReferences':current_catalog_asset['map_references'],
                'metadataReferences':current_catalog_asset.get('metadata_references',[])}})
    return {'types':current_catalog_record['review_categories'],'assets':current_asset_records}


def build_map_database_seed(current_asset_root):
    current_asset_root=Path(current_asset_root).resolve()
    current_map_root=current_asset_root/'assets/maps'
    current_catalog_record=load_billboard_catalog(current_asset_root)
    current_billboard_identifiers={current_asset_record['texture_key'] for current_asset_record in current_catalog_record['billboards']}
    current_property_records=load_unique_yaml_document(current_map_root/'sprite-display-properties.yaml')['data']
    validate_sprite_display_properties(current_property_records)
    current_document_records={}
    for current_document_path in sorted(current_map_root.rglob('*.yaml')):
        if current_document_path.name=='sprite-display-properties.yaml':continue
        if current_document_path.is_symlink():raise ValueError('맵 시드에 심볼릭 링크를 허용하지 않습니다.')
        current_document_records[current_document_path.relative_to(current_map_root).as_posix()]=load_unique_yaml_document(current_document_path)
    return {'documents':current_document_records,'buildingProperties':{
        current_asset_identifier:current_property_values for current_asset_identifier,current_property_values in current_property_records.items()
        if current_asset_identifier not in current_billboard_identifiers}}
