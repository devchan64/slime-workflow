"""에셋 원본을 직접 읽는 맵 검수 UI와 연결 정보를 게시한다."""
from pathlib import Path
import hashlib
import json
import shutil
import yaml
from PIL import Image
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_tile, resolve_registered_sprite

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
GAME_TILE_SOURCE_SIZE=256
TOWN_BLOCK_HEIGHT=80
TOWN_BUILDING_TILE_OVERRIDES={
    'reedhaven':{
        'roof':'wood_roof',
        'wall':'wood_wall',
        'window':'wood_window_wall',
        'large_window':'wood_window_wall',
        'roof_underlay':'wood_crossbar_wall',
        'door':'wood_door_wall',
    },
    'stonewarm':{
        'roof':'stonewarm-stone-roof',
        'wall':'stonewarm-stone-wall',
        'window':'stonewarm-small-window-wall',
        'large_window':'stonewarm-large-window-wall',
        'roof_underlay':'stonewarm-stone-wall-crossbar',
        'door':'stonewarm-stone-door',
    },
}

# 두 신규 도시는 같은 등록 목재 원본을 참조한다.
TOWN_BUILDING_TILE_OVERRIDES.update({current_city_identifier: dict(TOWN_BUILDING_TILE_OVERRIDES['reedhaven']) for current_city_identifier in ('grainstead', 'saltford')})

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
    source_asset_directory=WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon'
    town_block_height=load_town_block_height()
    current_material_record=yaml.safe_load((WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/blocks/materials.yaml').read_text())
    output_directory_path.mkdir(parents=True,exist_ok=True)
    prefab_source_records=yaml.safe_load((source_asset_directory/'building-prefabs.yaml').read_text())['prefabs']
    building_tile_records={current_prefab_record['id']:{'roof':current_prefab_record['roof_tile'],'wall':current_prefab_record['ground_floor_plain_wall_tile'],'window':current_prefab_record['ground_floor_small_window_wall_tile'],'large_window':current_prefab_record['upper_floor_large_window_wall_tile'],'roof_underlay':current_prefab_record.get('roof_underlay_wall_tile',current_prefab_record['ground_floor_plain_wall_tile']),'door':current_prefab_record['door_tile']} for current_prefab_record in prefab_source_records}
    building_tile_records['stonewarm-guild'] = {'roof': 'stonewarm-guild-red-stone-roof'}
    (output_directory_path/'block-building-tiles.json').write_text(json.dumps(building_tile_records))
    exported_map_records=[]
    # 등록된 맵 원본 인덱스를 따라 검수 목록을 구성한다.
    from tools.review.common.map_asset_sources import load_review_map_identifiers
    _, current_map_identifiers = load_review_map_identifiers()
    for current_map_identifier in current_map_identifiers:
        current_map_record = build_registered_map_review(current_map_identifier)
        required_material_names=set(current_map_record['terrainCodes'].values())|{'wall','roof'}
        if required_material_names-set(current_material_record['materials']):
            raise ValueError('맵 검수 재질 누락: '+current_map_identifier)
        exported_map_records.append({'id':current_map_identifier,'name':current_map_record['name'],'path':'/management/map-assets/maps/'+current_map_identifier})
    if not exported_map_records:
        raise ValueError('검수할 마을 맵이 없습니다.')
    (output_directory_path/'block-map-index.json').write_text(json.dumps(exported_map_records,ensure_ascii=False))
    (output_directory_path/'block-render-profile.json').write_text(json.dumps({'blockHeight':town_block_height}))
    (output_directory_path/'block-materials.json').write_text(json.dumps(current_material_record['materials']))
    # 등록 원본을 직접 제공하며 이미지 사본을 만들지 않는다.
    tile_catalog_record=yaml.safe_load((source_asset_directory/'tile-catalog.yaml').read_text())
    if tile_catalog_record.get('source_tile_size')!=GAME_TILE_SOURCE_SIZE:
        raise ValueError(f'게임 타일 원본 크기는 {GAME_TILE_SOURCE_SIZE}px여야 합니다.')
    texture_source_root=WORKFLOW_ROOT_DIRECTORY.parent/'slime-frontend/assets'
    texture_output_directory=output_directory_path/'textures'
    texture_output_directory.mkdir(exist_ok=True)
    exported_texture_records={}
    asset_repository_path, registered_tile_records = load_registered_tiles()
    for current_tile_record in tile_catalog_record['tiles']:
        texture_source_path, tile_provenance_record = resolve_registered_tile(current_tile_record['asset'], asset_repository_path, registered_tile_records)
        with Image.open(texture_source_path) as source_texture_image:
            source_image_size=list(source_texture_image.size)
        normalization_warning_value=None if source_image_size==[GAME_TILE_SOURCE_SIZE,GAME_TILE_SOURCE_SIZE] else f'정규화 필요: 현재 {source_image_size[0]}×{source_image_size[1]}px, 기준 {GAME_TILE_SOURCE_SIZE}×{GAME_TILE_SOURCE_SIZE}px'
        exported_texture_records[current_tile_record['id']]={**tile_provenance_record,'path':'/management/map-assets/files/'+current_tile_record['asset']+'?v='+tile_provenance_record['sha256'],'source':current_tile_record['asset'],'sha256':hashlib.sha256(texture_source_path.read_bytes()).hexdigest(),'source_size':source_image_size,'expected_source_size':[GAME_TILE_SOURCE_SIZE,GAME_TILE_SOURCE_SIZE],'normalization_warning':normalization_warning_value}
    (output_directory_path/'block-textures.json').write_text(json.dumps(exported_texture_records))
    from tools.review.common.game_render_metrics import load_game_render_metrics
    game_render_metrics=load_game_render_metrics(texture_source_root.parent)
    (output_directory_path/'game-render-metrics.json').write_text(json.dumps(game_render_metrics))
    character_metadata_path,character_metadata_provenance=resolve_registered_sprite('assets/characters/default/animations/idle-v6/down-left-8frames-v1/idle-v6.animation.json')
    character_source_path,character_source_provenance=resolve_registered_sprite('assets/characters/default/animations/idle-v6/down-left-8frames-v1/source.json')
    character_metadata_record=json.loads(character_metadata_path.read_text())
    character_source_record=json.loads(character_source_path.read_text())
    character_frame_record=next(current_frame_record for current_frame_record in character_metadata_record['frames'] if current_frame_record['frameId']=='down_left.0')
    character_image_path,character_image_provenance=resolve_registered_sprite('assets/characters/default/animations/idle-v6/down-left-8frames-v1/idle-v6.png')
    shutil.copy2(character_image_path,texture_output_directory/'review-character.png')
    (output_directory_path/'review-character.json').write_text(json.dumps({'image':'textures/review-character.png?v='+hashlib.sha256(character_image_path.read_bytes()).hexdigest(),'frame':character_frame_record,'bodyHeight':character_source_record['referenceBodyHeight'],'displayHeight':game_render_metrics['characterHeight'],'source':'assets/characters/default/animations/idle-v6','provenance':{'image':character_image_provenance,'animation':character_metadata_provenance,'metadata':character_source_provenance}}))
    source_ui_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map'
    shutil.copy2(source_ui_directory/'block-map-review.html',output_directory_path/'map-review.html')
    shutil.copy2(source_ui_directory/'block-map-review.js',output_directory_path/'block-map-review.js')
    return output_directory_path


def build_registered_map_review(map_identifier_value):
    from tools.review.common.map_asset_sources import load_registered_map_review, MAP_SOURCE_BLOCK_HEIGHT, load_review_map_identifiers
    current_map_record = load_registered_map_review(map_identifier_value)
    current_city_identifiers, _ = load_review_map_identifiers()
    current_map_record['reviewLabel'] = '마을맵 검수' if map_identifier_value in current_city_identifiers else '필드맵 검수'
    current_block_height = load_town_block_height()
    normalize_game_block_heights(current_map_record,MAP_SOURCE_BLOCK_HEIGHT,current_block_height)
    validate_town_block_heights(current_map_record,current_block_height)
    current_map_record['buildingTileOverrides'] = TOWN_BUILDING_TILE_OVERRIDES.get(map_identifier_value,{})
    for current_building_record in current_map_record['buildings']:
        current_building_record['faces'] = build_current_block_faces(current_building_record['blocks'],current_block_height)
    return current_map_record
