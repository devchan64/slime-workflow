"""에셋별 공통 앵커·접지 크기·표시 높이 계약."""
import math
import re

SPRITE_ANCHOR_FIELD_NAMES = {'anchorX', 'anchorY'}
SPRITE_LAYOUT_FIELD_NAMES = {'groundFootprintColumns', 'groundFootprintRows', 'displayHeight'}


def validate_sprite_display_properties(current_property_catalog):
    if not isinstance(current_property_catalog, dict):
        raise ValueError('스프라이트 공통 속성은 매핑이어야 합니다.')
    for current_texture_key, current_property_values in current_property_catalog.items():
        if not isinstance(current_texture_key, str) or not re.fullmatch('[a-z][a-z0-9-]*', current_texture_key):
            raise ValueError('공통 속성의 텍스처 ID 오류')
        if not isinstance(current_property_values, dict) or set(current_property_values) not in (SPRITE_ANCHOR_FIELD_NAMES, SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES):
            raise ValueError('공통 속성 필드 오류')
        for current_property_name, current_property_value in current_property_values.items():
            if type(current_property_value) not in (int, float) or not math.isfinite(current_property_value):
                raise ValueError('공통 속성은 유한한 숫자여야 합니다.')
            if current_property_name in SPRITE_ANCHOR_FIELD_NAMES and not 0 <= current_property_value <= 1:
                raise ValueError('앵커 범위 오류')
            if current_property_name.startswith('groundFootprint') and (type(current_property_value) is not int or not 1 <= current_property_value <= 8):
                raise ValueError('바닥 크기 범위 오류')
            if current_property_name == 'displayHeight' and not 0 < current_property_value <= 1024:
                raise ValueError('표시 높이 범위 오류')
    return current_property_catalog


def apply_sprite_display_properties(current_map_data, current_property_catalog):
    """공통 속성은 배치별 과거 값보다 우선하며 위치·점유 좌표는 보존한다."""
    for current_object_record in current_map_data.get('objects', []):
        current_object_record.update(current_property_catalog.get(current_object_record.get('textureKey'), {}))
    for current_building_record in current_map_data.get('buildings', []):
        current_sprite_record = current_building_record.get('sprite', {})
        current_shared_properties = current_property_catalog.get(current_sprite_record.get('textureKey'), {})
        current_sprite_record.update({current_property_name: current_property_value for current_property_name, current_property_value in current_shared_properties.items() if current_property_name in SPRITE_ANCHOR_FIELD_NAMES})
