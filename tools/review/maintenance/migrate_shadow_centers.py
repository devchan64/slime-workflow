"""그림자 이동을 점유 중심 v2로 변환한다. 재실행은 이미 변환한 값을 유지한다."""
from tools.review.maintenance.sync_billboard_catalog import load_billboard_catalog, list_billboard_catalog_paths, write_billboard_catalog, prepare_billboard_catalog_files
import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
import yaml
from tools.review.common.sprite_display_properties import validate_sprite_display_properties
from tools.review.maintenance.sync_billboard_catalog import build_catalog_reference, load_unique_yaml_document


def migrate_shadow_property_values(current_property_values):
    validate_sprite_display_properties({'migration-check':current_property_values})
    current_coordinate_version=current_property_values.get('shadowCoordinateVersion',1)
    if current_coordinate_version==2:return dict(current_property_values)
    if current_coordinate_version!=1:raise ValueError('지원하지 않는 그림자 좌표 버전')
    current_updated_values=dict(current_property_values)
    for current_count_field,current_offset_field in [('groundFootprintColumns','shadowOffsetColumn'),('groundFootprintRows','shadowOffsetRow')]:
        current_tile_count=current_property_values[current_count_field]
        current_center_offset=(current_tile_count-1)/2
        current_previous_origin=(.5 if current_tile_count==1 else current_tile_count-1) if current_property_values.get('billboardAnchorMode')=='tile-intersection' else current_center_offset
        current_updated_values[current_offset_field]=round(current_property_values.get(current_offset_field,0)+current_previous_origin-current_center_offset,2)
    current_updated_values['shadowCoordinateVersion']=2
    validate_sprite_display_properties({'migration-check':current_updated_values})
    return current_updated_values


def execute_shadow_center_migration(current_asset_root,current_backup_root,current_apply_changes=False,current_migration_function=migrate_shadow_property_values):
    current_properties_path=current_asset_root/'assets/maps/sprite-display-properties.yaml'
    current_registry_path=current_asset_root/'asset-registry.yaml'
    current_catalog_path=current_asset_root/'assets/billboards/catalog.yaml'
    current_backend_path=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
    current_source_bytes={current_path:current_path.read_bytes() for current_path in [current_properties_path,current_registry_path,current_catalog_path,current_backend_path]}
    current_source_bytes.update({current_path:current_path.read_bytes() for current_path in list_billboard_catalog_paths(current_asset_root)[1:]})
    current_property_document=load_unique_yaml_document(current_properties_path)
    current_catalog_document=load_billboard_catalog(current_asset_root)
    current_previous_values=copy.deepcopy(current_property_document['data'])
    current_changed_keys=[]
    for current_asset_record in current_catalog_document['billboards']:
        current_texture_key=current_asset_record['texture_key']
        if current_texture_key not in current_previous_values:raise ValueError('미설정 에셋: '+current_texture_key)
        current_next_values=current_migration_function(current_previous_values[current_texture_key])
        if current_next_values!=current_previous_values[current_texture_key]:current_changed_keys.append(current_texture_key)
        current_property_document['data'][current_texture_key]=current_next_values
    current_report_data={'count':len(current_changed_keys),'textures':current_changed_keys,'before':current_previous_values,'after':current_property_document['data']}
    if not current_apply_changes:return current_report_data
    if not current_changed_keys:return current_report_data
    current_backup_root.mkdir(parents=True,exist_ok=False)
    for current_file_index,(current_file_path,current_file_bytes) in enumerate(current_source_bytes.items()):
        (current_backup_root/str(current_file_index)).write_bytes(current_file_bytes)
    (current_backup_root/'paths.json').write_text(json.dumps([str(current_path) for current_path in current_source_bytes]))
    current_property_bytes=yaml.safe_dump(current_property_document,allow_unicode=True,sort_keys=False).encode()
    current_old_hash=hashlib.sha256(current_source_bytes[current_properties_path]).hexdigest()
    current_new_hash=hashlib.sha256(current_property_bytes).hexdigest()
    current_pending_files={current_properties_path:current_property_bytes}
    for current_file_path in [current_registry_path,current_backend_path]:
        current_file_text=current_source_bytes[current_file_path].decode()
        if current_file_text.count(current_old_hash)!=1:raise ValueError('원본 해시 잠금 불일치')
        current_pending_files[current_file_path]=current_file_text.replace(current_old_hash,current_new_hash).encode()
    for current_file_path,current_file_bytes in current_source_bytes.items():
        if current_file_path.read_bytes()!=current_file_bytes:raise ValueError('검토 중 원본 변경')
    try:
        for current_file_path,current_file_bytes in current_pending_files.items():current_file_path.write_bytes(current_file_bytes)
        write_billboard_catalog(current_asset_root,build_catalog_reference(current_asset_root))
    except Exception:
        for current_file_path,current_file_bytes in current_source_bytes.items():current_file_path.write_bytes(current_file_bytes)
        raise
    (current_backup_root/'report.json').write_text(json.dumps(current_report_data,ensure_ascii=False,indent=2))
    return current_report_data


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--asset-root',type=Path,required=True)
    current_argument_parser.add_argument('--backup-root',type=Path,required=True)
    current_argument_parser.add_argument('--apply',action='store_true')
    current_argument_values=current_argument_parser.parse_args()
    print(datetime.now().isoformat()+'/shadow-migration/start',flush=True)
    try:
        current_result_data=execute_shadow_center_migration(current_argument_values.asset_root,current_argument_values.backup_root,current_argument_values.apply)
        print(datetime.now().isoformat()+'/shadow-migration/complete',current_result_data['count'],flush=True)
    except Exception as current_migration_error:
        print(datetime.now().isoformat()+'/shadow-migration/failure',str(current_migration_error),flush=True)
        raise
