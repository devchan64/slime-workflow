"""에셋별 공통 앵커·접지 크기·표시 높이 계약."""
import math
import re

SPRITE_ANCHOR_FIELD_NAMES = {'anchorX', 'anchorY'}
SPRITE_LAYOUT_FIELD_NAMES = {'groundFootprintColumns', 'groundFootprintRows', 'displayHeight'}
BILLBOARD_PLACEMENT_FIELD_NAMES = {'billboardPlacementAnchor', 'billboardBlocksMovement'}
BILLBOARD_SHADOW_DEFAULTS = {'shadowOffsetColumn':0, 'shadowOffsetRow':0, 'shadowScaleX':1, 'shadowScaleY':1}
BILLBOARD_SHADOW_FIELD_NAMES = set(BILLBOARD_SHADOW_DEFAULTS)
BILLBOARD_BLOCKING_HEIGHT_LIMIT = 80

def calculate_billboard_blocking_state(current_property_values):
    """공용 표시 높이를 기준으로 통행 차단 속성을 계산한다. 배율·줌은 제외한다."""
    if current_property_values.get('billboardAnchorMode') == 'tile-bottom-center':
        return (current_property_values['groundFootprintColumns'] > 1 or current_property_values['groundFootprintRows'] > 1 or (current_property_values['anchorY'] >= .5 and current_property_values['displayHeight'] > BILLBOARD_BLOCKING_HEIGHT_LIMIT))
    current_placement_anchor = current_property_values['billboardPlacementAnchor']
    current_oversized_ground = current_property_values['groundFootprintColumns'] > 1 or current_property_values['groundFootprintRows'] > 1
    if current_placement_anchor not in ('top', 'bottom'):
        raise ValueError('빌보드 배치 앵커는 top 또는 bottom이어야 합니다.')
    if current_placement_anchor == 'top' and current_oversized_ground:
        raise ValueError('1×1 초과 빌보드는 상단 배치할 수 없습니다.')
    return current_placement_anchor == 'bottom' and (current_oversized_ground or current_property_values['displayHeight'] > BILLBOARD_BLOCKING_HEIGHT_LIMIT)



def validate_sprite_display_properties(current_property_catalog):
    if not isinstance(current_property_catalog, dict):
        raise ValueError('스프라이트 공통 속성은 매핑이어야 합니다.')
    for current_texture_key, current_property_values in current_property_catalog.items():
        if not isinstance(current_texture_key, str) or not re.fullmatch('[a-z][a-z0-9-]*', current_texture_key):
            raise ValueError('공통 속성의 텍스처 ID 오류')
        if not isinstance(current_property_values, dict) or (set(current_property_values)-BILLBOARD_SHADOW_FIELD_NAMES-{'billboardAnchorMode'}) not in (SPRITE_ANCHOR_FIELD_NAMES, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES | {'billboardBlocksMovement'}, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES | BILLBOARD_PLACEMENT_FIELD_NAMES):
            raise ValueError('공통 속성 필드 오류')
        if 'billboardBlocksMovement' in current_property_values:
            if type(current_property_values['billboardBlocksMovement']) is not bool:
                raise ValueError('빌보드 통행 차단 속성은 불리언이어야 합니다.')
        if 'billboardAnchorMode' in current_property_values and current_property_values['billboardAnchorMode'] != 'tile-bottom-center':
            raise ValueError('알 수 없는 빌보드 앵커 규격')
        for current_property_name, current_property_value in current_property_values.items():
            if current_property_name in BILLBOARD_PLACEMENT_FIELD_NAMES or current_property_name == 'billboardAnchorMode':
                continue
            if type(current_property_value) not in (int, float) or not math.isfinite(current_property_value):
                raise ValueError('공통 속성은 유한한 숫자여야 합니다.')
            if current_property_name in SPRITE_ANCHOR_FIELD_NAMES and not ((-16 <= current_property_value <= 16) if current_property_values.get('billboardAnchorMode') == 'tile-bottom-center' else (0 <= current_property_value <= 1)):
                raise ValueError('앵커 범위 오류')
            if current_property_name.startswith('groundFootprint') and (type(current_property_value) is not int or not 1 <= current_property_value <= 8):
                raise ValueError('바닥 크기 범위 오류')
            if current_property_name.startswith('shadowOffset') and not -4 <= current_property_value <= 4:
                raise ValueError('그림자 이동은 -4~4타일이어야 합니다.')
            if current_property_name.startswith('shadowScale') and not 0.1 <= current_property_value <= 4:
                raise ValueError('그림자 배율은 0.1~4여야 합니다.')
            if current_property_name == 'displayHeight' and not 0 < current_property_value <= 1024:
                raise ValueError('표시 높이 범위 오류')
        if 'billboardBlocksMovement' in current_property_values:
            if current_property_values['billboardBlocksMovement'] != calculate_billboard_blocking_state(current_property_values):
                raise ValueError(f'빌보드 앵커·크기·높이와 통행 차단 속성 불일치: {current_texture_key}')
    return current_property_catalog


def apply_sprite_display_properties(current_map_data, current_property_catalog):
    """맵 원본의 표시 속성 재정의를 거절하고 에셋 공용값만 해석한다."""
    for current_object_record in current_map_data.get('objects', []):
        current_texture_key = current_object_record.get('textureKey')
        if current_texture_key is None:
            continue
        current_shared_properties = current_property_catalog.get(current_texture_key)
        if current_shared_properties is None or (set(current_shared_properties)-BILLBOARD_SHADOW_FIELD_NAMES-{'billboardAnchorMode'}) not in (SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES | {'billboardBlocksMovement'}, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES | BILLBOARD_PLACEMENT_FIELD_NAMES):
            raise ValueError(f'빌보드 공용 속성 누락: {current_texture_key}')
        current_override_fields = set(current_object_record) & (SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES | BILLBOARD_PLACEMENT_FIELD_NAMES | BILLBOARD_SHADOW_FIELD_NAMES | {'billboardAnchorMode'})
        if current_override_fields:
            raise ValueError(f'맵별 빌보드 공용 속성 재정의 금지: {current_texture_key}: {sorted(current_override_fields)}')
        current_object_record.update(current_shared_properties)
        if current_shared_properties.get('billboardAnchorMode') == 'tile-bottom-center':
            current_object_record['billboardPlacementAnchor'] = 'top' if current_shared_properties['anchorY'] < .5 else 'bottom'
    for current_ground_record in current_map_data.get('groundOverrides', []):
        if set(current_ground_record) - {'position', 'textureKey'}:
            raise ValueError('타일 배치는 위치·원본 선택만 지정할 수 있습니다. 표시 속성은 공용 렌더러를 사용합니다.')
    for current_building_record in current_map_data.get('buildings', []):
        current_sprite_record = current_building_record.get('sprite', {})
        current_texture_key = current_sprite_record.get('textureKey')
        current_shared_properties = current_property_catalog.get(current_texture_key)
        if current_shared_properties is None or not SPRITE_ANCHOR_FIELD_NAMES <= set(current_shared_properties):
            raise ValueError(f'건물 공용 속성 누락: {current_texture_key}')
        if set(current_sprite_record) & SPRITE_ANCHOR_FIELD_NAMES:
            raise ValueError(f'맵별 건물 앵커 재정의 금지: {current_texture_key}')
        current_sprite_record.update({current_property_name: current_property_value for current_property_name, current_property_value in current_shared_properties.items() if current_property_name in SPRITE_ANCHOR_FIELD_NAMES})


def collect_billboard_blocked_cells(current_object_records):
    """블로킹 빌보드의 선언된 접지 영역 전체를 통행 불가 셀로 반환한다."""
    current_blocked_cells = set()
    for current_object_record in current_object_records:
        if not current_object_record.get('billboardBlocksMovement', False):
            continue
        current_cell_position = current_object_record['position']
        current_blocked_cells.update((current_cell_position['column'] + current_column_offset, current_cell_position['row'] + current_row_offset)
            for current_column_offset in range(current_object_record['groundFootprintColumns'])
            for current_row_offset in range(current_object_record['groundFootprintRows']))
    return current_blocked_cells
