"""명시적으로 내보낸 게임 블록 기하 사본을 관리도구에 게시한다."""
from pathlib import Path
import hashlib
import json
import shutil
import yaml
from PIL import Image

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
GAME_TILE_SOURCE_SIZE=256
TOWN_BLOCK_HEIGHT=80


def load_town_block_height():
    render_profile_values=yaml.safe_load((WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/render-profiles.yaml').read_text())
    if not isinstance(render_profile_values,dict) or render_profile_values.get('block_height')!=TOWN_BLOCK_HEIGHT:
        raise ValueError(f'마을 블록 높이는 {TOWN_BLOCK_HEIGHT}px여야 합니다.')
    return TOWN_BLOCK_HEIGHT


def validate_town_block_heights(map_record_values, block_height_value):
    for building_record_values in map_record_values['buildings']:
        for block_record_values in building_record_values['blocks']:
            current_block_height=block_record_values['height']
            if not isinstance(current_block_height,int) or current_block_height<=0 or block_height_value%current_block_height:
                raise ValueError(f'블록 높이 오류: {map_record_values["id"]}/{block_record_values["id"]}')
        for face_record_values in building_record_values.get('faces',[]):
            for vertex_record_values in face_record_values['vertices']:
                if vertex_record_values['height']%block_height_value:
                    raise ValueError(f'블록 면 높이 오류: {map_record_values["id"]}')


def normalize_game_block_heights(map_record_values, source_block_height, target_block_height):
    """게임 블록 높이를 검수 화면의 블록 높이로 정규화한다."""
    if not isinstance(source_block_height,int) or source_block_height<=0:
        raise ValueError('게임 블록 높이 메타데이터가 올바르지 않습니다.')
    for current_building_record in map_record_values['buildings']:
        for current_block_record in current_building_record['blocks']:
            current_block_height=current_block_record['height']
            current_offset_height=current_block_record['offsetHeight']
            current_normalized_block_height=current_block_height*target_block_height
            current_normalized_offset_height=current_offset_height*target_block_height
            if current_normalized_block_height%source_block_height or current_normalized_offset_height%source_block_height:
                raise ValueError(f'게임 블록 높이 단위 오류: {map_record_values["id"]}/{current_block_record["id"]}')
            current_block_record['height']=current_normalized_block_height//source_block_height
            current_block_record['offsetHeight']=current_normalized_offset_height//source_block_height


def build_current_block_faces(block_record_values, block_height_value):
    """현재 블록 구성으로 검수 전용 면을 다시 만든다. 경사 블록의 내부 면은 숨긴다."""
    current_face_records=[]
    minimum_column_value=min(current_block_record['column'] for current_block_record in block_record_values)
    maximum_column_value=max(current_block_record['column'] for current_block_record in block_record_values)
    minimum_row_value=min(current_block_record['row'] for current_block_record in block_record_values)
    maximum_row_value=max(current_block_record['row'] for current_block_record in block_record_values)
    for current_block_record in block_record_values:
        current_base_height=current_block_record['layer']*block_height_value+current_block_record['offsetHeight']
        current_top_height=current_base_height+current_block_record['height']
        current_column=current_block_record['column']
        current_row=current_block_record['row']
        current_corners=[
            {'column':current_column-.5,'row':current_row-.5,'height':current_base_height},
            {'column':current_column+.5,'row':current_row-.5,'height':current_base_height},
            {'column':current_column+.5,'row':current_row+.5,'height':current_base_height},
            {'column':current_column-.5,'row':current_row+.5,'height':current_base_height},
        ]
        current_top_corners=[{**current_corner,'height':current_top_height} for current_corner in current_corners]
        if current_block_record['shape']=='ramp':
            high_side_name=current_block_record['highSide']
            current_top_corners=[dict(current_corner) for current_corner in current_corners]
            for current_corner in current_top_corners:
                if (high_side_name=='east' and current_corner['column']>current_column) or (high_side_name=='west' and current_corner['column']<current_column) or (high_side_name=='south' and current_corner['row']>current_row) or (high_side_name=='north' and current_corner['row']<current_row):
                    current_corner['height']+=current_block_record['height']
        current_face_records.append({'vertices':current_top_corners,'material':current_block_record['material'],'top':True})
        for current_corner_index in range(4):
            next_corner_index=(current_corner_index+1)%4
            if current_block_record['shape']=='ramp' and not (
                current_corner_index==0 and current_row==minimum_row_value or
                current_corner_index==1 and current_column==maximum_column_value or
                current_corner_index==2 and current_row==maximum_row_value or
                current_corner_index==3 and current_column==minimum_column_value
            ):
                continue
            current_face_records.append({'vertices':[current_corners[current_corner_index],current_corners[next_corner_index],current_top_corners[next_corner_index],current_top_corners[current_corner_index]],'material':current_block_record['material'],'top':False})
    return current_face_records


def build_block_map_review(output_directory_path):
    output_directory_path=Path(output_directory_path).resolve()
    if not output_directory_path.is_relative_to(WORKFLOW_ROOT_DIRECTORY/'.tmp'):
        raise ValueError('검수 출력은 .tmp 하위여야 합니다.')
    source_asset_directory=WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/game-data'
    town_block_height=load_town_block_height()
    current_material_record=yaml.safe_load((WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/blocks/materials.yaml').read_text())
    output_directory_path.mkdir(parents=True,exist_ok=True)
    prefab_source_records=yaml.safe_load((source_asset_directory.parent/'building-prefabs.yaml').read_text())['prefabs']
    building_tile_records={current_prefab_record['id']:{'roof':current_prefab_record['roof_tile'],'wall':current_prefab_record['ground_floor_plain_wall_tile'],'window':current_prefab_record['ground_floor_small_window_wall_tile'],'large_window':current_prefab_record['upper_floor_large_window_wall_tile'],'door':current_prefab_record['door_tile']} for current_prefab_record in prefab_source_records}
    (output_directory_path/'block-building-tiles.json').write_text(json.dumps(building_tile_records))
    exported_map_records=[]
    # 명시적으로 내보낸 맵 사본만 목록에 게시한다.
    source_manifest_path=source_asset_directory/'source-manifest.json'
    if not source_manifest_path.is_file():
        raise ValueError('게임 도시 맵 사본이 없습니다. slime-backend/scripts/export_city_map_review.py를 실행하세요.')
    source_manifest_record=json.loads(source_manifest_path.read_text())
    source_block_height=source_manifest_record.get('blockHeight')
    for source_map_path in sorted(source_asset_directory.glob('*.json')):
        if source_map_path.name=='source-manifest.json':
            continue
        current_map_record=json.loads(source_map_path.read_text())
        if current_map_record['id']!=source_map_path.stem or any(current_building_record['blockSchemaVersion']!=1 for current_building_record in current_map_record['buildings']):
            raise ValueError(f'블록 스키마 오류: {source_map_path.name}')
        normalize_game_block_heights(current_map_record,source_block_height,town_block_height)
        validate_town_block_heights(current_map_record,town_block_height)
        required_material_names=set(current_map_record['terrainCodes'].values())|{'wall','roof'}
        if required_material_names-set(current_material_record['materials']):
            raise ValueError(f'임시 재질이 정의되지 않았습니다: {source_map_path.name}')
        for current_building_record in current_map_record['buildings']:
            current_building_record['faces']=build_current_block_faces(current_building_record['blocks'],town_block_height)
        target_map_filename=f"block-map-{current_map_record['id']}.json"
        (output_directory_path/target_map_filename).write_text(json.dumps(current_map_record,ensure_ascii=False))
        exported_map_records.append({'id':current_map_record['id'],'name':current_map_record['name'],'path':target_map_filename})
    if not exported_map_records:
        raise ValueError('검수할 마을 맵이 없습니다.')
    (output_directory_path/'block-map-index.json').write_text(json.dumps(exported_map_records,ensure_ascii=False))
    (output_directory_path/'block-render-profile.json').write_text(json.dumps({'blockHeight':town_block_height}))
    shutil.copy2(source_asset_directory/'iseulon.json',output_directory_path/'block-map.json')
    (output_directory_path/'block-materials.json').write_text(json.dumps(current_material_record['materials']))
    # 게시 시 정식 에셋을 사본으로 전달하고 원본 해시를 보존한다.
    tile_catalog_record=yaml.safe_load((source_asset_directory.parent/'tile-catalog.yaml').read_text())
    if tile_catalog_record.get('source_tile_size')!=GAME_TILE_SOURCE_SIZE:
        raise ValueError(f'게임 타일 원본 크기는 {GAME_TILE_SOURCE_SIZE}px여야 합니다.')
    texture_source_root=WORKFLOW_ROOT_DIRECTORY.parent/'slime-frontend/src/assets'
    texture_output_directory=output_directory_path/'textures'
    texture_output_directory.mkdir(exist_ok=True)
    exported_texture_records={}
    for current_tile_record in tile_catalog_record['tiles']:
        texture_source_path=texture_source_root/current_tile_record['asset']
        with Image.open(texture_source_path) as source_texture_image:
            source_image_size=list(source_texture_image.size)
        normalization_warning_value=None if source_image_size==[GAME_TILE_SOURCE_SIZE,GAME_TILE_SOURCE_SIZE] else f'정규화 필요: 현재 {source_image_size[0]}×{source_image_size[1]}px, 기준 {GAME_TILE_SOURCE_SIZE}×{GAME_TILE_SOURCE_SIZE}px'
        texture_target_name=current_tile_record['id']+'.png'
        shutil.copy2(texture_source_path,texture_output_directory/texture_target_name)
        exported_texture_records[current_tile_record['id']]={'path':'textures/'+texture_target_name+'?v='+hashlib.sha256(texture_source_path.read_bytes()).hexdigest(),'source':current_tile_record['asset'],'sha256':hashlib.sha256(texture_source_path.read_bytes()).hexdigest(),'source_size':source_image_size,'expected_source_size':[GAME_TILE_SOURCE_SIZE,GAME_TILE_SOURCE_SIZE],'normalization_warning':normalization_warning_value}
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
