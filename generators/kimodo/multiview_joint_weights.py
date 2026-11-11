"""8방향 BODY18 관측의 사용자 가중치 계약."""
import math

MULTIVIEW_WEIGHT_VIEW_COUNT = 8
MULTIVIEW_WEIGHT_JOINT_COUNT = 18
MULTIVIEW_WEIGHT_SCHEMA_VERSION = 'kimodo-body18-view-weights-v1'


def validate_multiview_joint_weights(current_weight_record):
    """방향과 BODY18 관절별 가중치·판단 근거를 엄격하게 검사한다."""
    if not isinstance(current_weight_record, dict) or set(current_weight_record) != {'schema', 'views'} or current_weight_record['schema'] != MULTIVIEW_WEIGHT_SCHEMA_VERSION:
        raise ValueError('8방향 관절 가중치 스키마 오류')
    current_views = current_weight_record['views']
    if not isinstance(current_views, list) or len(current_views) != MULTIVIEW_WEIGHT_VIEW_COUNT:
        raise ValueError('관절 가중치에는 8방향이 필요합니다.')
    current_weight_rows = []
    for current_view_index, current_view in enumerate(current_views):
        if not isinstance(current_view, dict) or set(current_view) != {'observation', 'joints'} or type(current_view['observation']) is not int or current_view['observation'] != current_view_index + 1:
            raise ValueError('관절 가중치 방향 번호 또는 필드 오류')
        current_joint_records = current_view['joints']
        if not isinstance(current_joint_records, list) or len(current_joint_records) != MULTIVIEW_WEIGHT_JOINT_COUNT:
            raise ValueError('각 방향에 BODY18 관절 18개가 필요합니다.')
        current_joint_weights = []
        for current_joint_index, current_joint in enumerate(current_joint_records):
            if not isinstance(current_joint, dict) or set(current_joint) != {'joint', 'weight', 'reason'} or type(current_joint['joint']) is not int or current_joint['joint'] != current_joint_index:
                raise ValueError('관절 가중치 번호 또는 필드 오류')
            current_weight = current_joint['weight']
            if type(current_weight) not in (int, float) or not math.isfinite(current_weight) or not 0 <= current_weight <= 1:
                raise ValueError('관절 가중치는 0~1 숫자여야 합니다.')
            if not isinstance(current_joint['reason'], str) or not current_joint['reason'].strip():
                raise ValueError('관절 가중치 판단 근거가 필요합니다.')
            current_joint_weights.append(float(current_weight))
        current_weight_rows.append(current_joint_weights)
    return current_weight_rows
