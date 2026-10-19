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
    """맵 원본의 표시 속성 재정의를 거절하고 에셋 공용값만 해석한다."""
    for current_object_record in current_map_data.get('objects', []):
        current_texture_key = current_object_record.get('textureKey')
        if current_texture_key is None:
            continue
        current_shared_properties = current_property_catalog.get(current_texture_key)
        if current_shared_properties is None or set(current_shared_properties) != SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES:
            raise ValueError(f'빌보드 공용 속성 누락: {current_texture_key}')
        current_override_fields = set(current_object_record) & (SPRITE_ANCHOR_FIELD_NAMES | SPRITE_LAYOUT_FIELD_NAMES)
        if current_override_fields:
            raise ValueError(f'맵별 빌보드 공용 속성 재정의 금지: {current_texture_key}: {sorted(current_override_fields)}')
        current_object_record.update(current_shared_properties)
    for current_ground_record in current_map_data.get('groundOverrides', []):
        if set(current_ground_record) - {'position', 'textureKey'}:
            raise ValueError('타일 배치는 위치·원본 선택만 지정할 수 있습니다. 표시 속성은 공용 렌더러를 사용합니다.')
    for current_building_record in current_map_data.get('buildings', []):
        current_sprite_record = current_building_record.get('sprite', {})
        current_shared_properties = current_property_catalog.get(current_sprite_record.get('textureKey'), {})
        current_sprite_record.update({current_property_name: current_property_value for current_property_name, current_property_value in current_shared_properties.items() if current_property_name in SPRITE_ANCHOR_FIELD_NAMES})
