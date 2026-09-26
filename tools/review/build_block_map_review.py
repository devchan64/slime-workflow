"""명시적으로 내보낸 게임 블록 기하 사본을 관리도구에 게시한다."""
from pathlib import Path
import hashlib
import json
import shutil
import yaml

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]


def build_block_map_review(output_directory_path):
    output_directory_path=Path(output_directory_path).resolve()
    if not output_directory_path.is_relative_to(WORKFLOW_ROOT_DIRECTORY/'.tmp'):
        raise ValueError('검수 출력은 .tmp 하위여야 합니다.')
    source_asset_directory=WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/blocks'
    current_material_record=yaml.safe_load((source_asset_directory/'materials.yaml').read_text())
    output_directory_path.mkdir(parents=True,exist_ok=True)
    prefab_source_records=yaml.safe_load((source_asset_directory.parent/'building-prefabs.yaml').read_text())['prefabs']
    building_tile_records={current_prefab_record['id']:{'roof':current_prefab_record['roof_tile'],'wall':current_prefab_record['ground_floor_plain_wall_tile'],'window':current_prefab_record['ground_floor_small_window_wall_tile'],'large_window':current_prefab_record['upper_floor_large_window_wall_tile'],'door':current_prefab_record['door_tile']} for current_prefab_record in prefab_source_records}
    (output_directory_path/'block-building-tiles.json').write_text(json.dumps(building_tile_records))
    exported_map_records=[]
    # 명시적으로 내보낸 맵 사본만 목록에 게시한다.
    for source_map_path in sorted(source_asset_directory.glob('*.json')):
        current_map_record=json.loads(source_map_path.read_text())
        if current_map_record['id']!=source_map_path.stem or any(current_building_record['blockSchemaVersion']!=1 for current_building_record in current_map_record['buildings']):
            raise ValueError(f'블록 스키마 오류: {source_map_path.name}')
        required_material_names=set(current_map_record['terrainCodes'].values())|{'wall','roof'}
        if required_material_names-set(current_material_record['materials']):
            raise ValueError(f'임시 재질이 정의되지 않았습니다: {source_map_path.name}')
        target_map_filename=f"block-map-{current_map_record['id']}.json"
        shutil.copy2(source_map_path,output_directory_path/target_map_filename)
        exported_map_records.append({'id':current_map_record['id'],'name':current_map_record['name'],'path':target_map_filename})
    if not exported_map_records:
        raise ValueError('검수할 마을 맵이 없습니다.')
    (output_directory_path/'block-map-index.json').write_text(json.dumps(exported_map_records,ensure_ascii=False))
    shutil.copy2(source_asset_directory/'iseulon.json',output_directory_path/'block-map.json')
    (output_directory_path/'block-materials.json').write_text(json.dumps(current_material_record['materials']))
    # 게시 시 정식 에셋을 사본으로 전달하고 원본 해시를 보존한다.
    tile_catalog_record=yaml.safe_load((source_asset_directory.parent/'tile-catalog.yaml').read_text())
    texture_source_root=WORKFLOW_ROOT_DIRECTORY.parent/'slime-frontend/src/assets'
    texture_output_directory=output_directory_path/'textures'
    texture_output_directory.mkdir(exist_ok=True)
    exported_texture_records={}
    for current_tile_record in tile_catalog_record['tiles']:
        texture_source_path=texture_source_root/current_tile_record['asset']
        texture_target_name=current_tile_record['id']+'.png'
        shutil.copy2(texture_source_path,texture_output_directory/texture_target_name)
        exported_texture_records[current_tile_record['id']]={'path':'textures/'+texture_target_name+'?v='+hashlib.sha256(texture_source_path.read_bytes()).hexdigest(),'source':current_tile_record['asset'],'sha256':hashlib.sha256(texture_source_path.read_bytes()).hexdigest()}
    (output_directory_path/'block-textures.json').write_text(json.dumps(exported_texture_records))
    from tools.review.common.game_render_metrics import load_game_render_metrics
    game_render_metrics=load_game_render_metrics(texture_source_root.parents[1])
    (output_directory_path/'game-render-metrics.json').write_text(json.dumps(game_render_metrics))
    character_source_directory=texture_source_root/'characters/default/standing-v5'
    character_metadata_record=json.loads((character_source_directory/'idle-v5.animation.json').read_text())
    character_source_record=json.loads((character_source_directory/'source.json').read_text())
    character_frame_record=next(current_frame_record for current_frame_record in character_metadata_record['frames'] if current_frame_record['frameId']=='down_left.0')
    character_image_path=character_source_directory/'standing-down-left.png'
    shutil.copy2(character_image_path,texture_output_directory/'review-character.png')
    (output_directory_path/'review-character.json').write_text(json.dumps({'image':'textures/review-character.png?v='+hashlib.sha256(character_image_path.read_bytes()).hexdigest(),'frame':character_frame_record,'bodyHeight':character_source_record['referenceBodyHeight'],'displayHeight':game_render_metrics['characterHeight'],'source':'characters/default/standing-v5'}))
    source_ui_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map'
    shutil.copy2(source_ui_directory/'block-map-review.html',output_directory_path/'map-review.html')
    shutil.copy2(source_ui_directory/'block-map-review.js',output_directory_path/'block-map-review.js')
    return output_directory_path
