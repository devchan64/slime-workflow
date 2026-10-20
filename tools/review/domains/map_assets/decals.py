"""단일 지면 타일 데칼의 명시적인 배치 계약을 검증한다."""
import math

GROUND_DECAL_TEXTURE_KEYS = {'boar-hoof-pair-v1', 'boar-hoof-trail-v1', 'boar-hoof-worn-v1'}
GROUND_DECAL_RECORD_FIELDS = {'id', 'textureKey', 'position', 'offsetX', 'offsetY', 'scale', 'rotation', 'opacity', 'order'}


def validate_ground_decal_records(current_decal_records, current_column_count, current_row_count):
    if not isinstance(current_decal_records, list):
        raise ValueError('데칼 목록 형식 오류')
    current_seen_identifiers = set()
    for current_decal_record in current_decal_records:
        if not isinstance(current_decal_record, dict) or set(current_decal_record) != GROUND_DECAL_RECORD_FIELDS:
            raise ValueError('데칼 필드 오류')
        current_decal_identifier = current_decal_record['id']
        if not isinstance(current_decal_identifier, str) or not current_decal_identifier or current_decal_identifier in current_seen_identifiers:
            raise ValueError('데칼 ID 누락·중복')
        current_seen_identifiers.add(current_decal_identifier)
        if current_decal_record['textureKey'] not in GROUND_DECAL_TEXTURE_KEYS:
            raise ValueError('미등록 데칼 텍스처')
        current_cell_position = current_decal_record['position']
        if not isinstance(current_cell_position, dict) or set(current_cell_position) != {'column', 'row'} or any(type(current_cell_position[current_axis_name]) is not int for current_axis_name in ('column', 'row')):
            raise ValueError('데칼 좌표 형식 오류')
        if not 0 <= current_cell_position['column'] < current_column_count or not 0 <= current_cell_position['row'] < current_row_count:
            raise ValueError('데칼 맵 범위 초과')
        for current_field_name in ('offsetX', 'offsetY', 'scale', 'rotation', 'opacity'):
            current_field_value = current_decal_record[current_field_name]
            if type(current_field_value) not in (int, float) or not math.isfinite(current_field_value):
                raise ValueError('데칼 유한 수치 오류')
        if type(current_decal_record['order']) is not int or current_decal_record['order'] < 0 or not 0 < current_decal_record['scale'] <= 1 or not 0 <= current_decal_record['rotation'] < 360 or not 0 <= current_decal_record['opacity'] <= 1:
            raise ValueError('데칼 수치 범위 오류')
        current_rotation_angle = math.radians(current_decal_record['rotation'])
        current_half_extent = current_decal_record['scale'] * (abs(math.sin(current_rotation_angle)) + abs(math.cos(current_rotation_angle))) / 2
        if min(current_decal_record['offsetX'], current_decal_record['offsetY'], 1-current_decal_record['offsetX'], 1-current_decal_record['offsetY']) < current_half_extent:
            raise ValueError('데칼은 동일 고도 한 타일 안에 배치해야 합니다.')
