"""8방향 관측의 출처 일치 여부를 검증한다."""
import hashlib
import json


def calculate_multiview_observation_hash(current_reference_record):
    """관절과 검출 상자·순서를 정규 직렬화해 식별자를 만든다."""
    current_points = current_reference_record.get('keypoints')
    current_sources = current_reference_record.get('observation_sources')
    if not isinstance(current_points, list) or len(current_points) != 8 or not isinstance(current_sources, list) or len(current_sources) != 8:
        raise ValueError('8방향 관절과 관측 출처가 필요합니다.')
    current_boxes = []
    for current_index, current_source in enumerate(current_sources):
        if not isinstance(current_source, dict) or not isinstance(current_source.get('bbox'), list) or len(current_source['bbox']) != 4:
            raise ValueError(f'{current_index+1}번 관측 검출 상자 형식 오류')
        current_boxes.append(current_source['bbox'])
    try:
        current_bytes = json.dumps({'keypoints':current_points,'bboxes':current_boxes},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (TypeError,ValueError) as current_error:
        raise ValueError('8방향 관측을 직렬화할 수 없습니다.') from current_error
    return hashlib.sha256(current_bytes).hexdigest()


def calculate_multiview_fit_context_hash(current_observation_hash,current_initial_record,current_visibility_rows,current_weight_table):
    """관측·초기 카메라·가시성·방향 가중치의 조합을 식별한다."""
    if not isinstance(current_observation_hash,str) or not current_observation_hash:
        raise ValueError('관측 출처 해시가 필요합니다.')
    try:
        current_payload={'observation_sha256':current_observation_hash,'initial':current_initial_record,'visibility':current_visibility_rows,'weights':current_weight_table}
        current_bytes=json.dumps(current_payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (TypeError,ValueError) as current_error:
        raise ValueError('3D 추정 입력 출처를 직렬화할 수 없습니다.') from current_error
    return hashlib.sha256(current_bytes).hexdigest()
