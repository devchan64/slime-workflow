"""기존 타일 길이를 점유 영역 배율로 변환한다."""
import argparse
from datetime import datetime
from pathlib import Path
from tools.review.common.sprite_display_properties import validate_sprite_display_properties
from tools.review.maintenance.migrate_shadow_centers import execute_shadow_center_migration


def migrate_shadow_size_values(current_property_values):
    validate_sprite_display_properties({'migration-check':current_property_values})
    if current_property_values.get('shadowSizeVersion',1)==2:
        return dict(current_property_values)
    current_updated_values=dict(current_property_values)
    for current_size_field,current_count_field in [('shadowScaleX','groundFootprintColumns'),('shadowScaleY','groundFootprintRows')]:
        current_tile_count=current_property_values[current_count_field]
        current_updated_values[current_size_field]=round(current_property_values.get(current_size_field,current_tile_count)/current_tile_count,6)
    current_updated_values['shadowSizeVersion']=2
    validate_sprite_display_properties({'migration-check':current_updated_values})
    return current_updated_values


def reset_shadow_size_defaults(current_property_values):
    """점유 배율로 전환한 뒤 크기만 공통 기본값으로 통일한다."""
    current_updated_values=migrate_shadow_size_values(current_property_values)
    current_updated_values.update(shadowScaleX=1,shadowScaleY=1)
    return current_updated_values


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--asset-root',type=Path,required=True)
    current_argument_parser.add_argument('--backup-root',type=Path,required=True)
    current_argument_parser.add_argument('--apply',action='store_true')
    current_argument_parser.add_argument('--reset-sizes',action='store_true',help='기존 크기 보존 대신 점유 배율 1·1로 통일')
    current_argument_values=current_argument_parser.parse_args()
    print(datetime.now().isoformat()+'/shadow-size-migration/start',flush=True)
    try:
        current_result_data=execute_shadow_center_migration(current_argument_values.asset_root,current_argument_values.backup_root,current_argument_values.apply,reset_shadow_size_defaults if current_argument_values.reset_sizes else migrate_shadow_size_values)
        print(datetime.now().isoformat()+'/shadow-size-migration/complete',current_result_data['count'],flush=True)
    except Exception as current_migration_error:
        print(datetime.now().isoformat()+'/shadow-size-migration/failure',str(current_migration_error),flush=True)
        raise
