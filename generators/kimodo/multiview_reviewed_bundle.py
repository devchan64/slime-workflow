"""8방향 스켈레톤 후보를 생성 입력으로 옮기기 위한 출처 계약.

출처 검증은 관절의 정확성이나 사람의 최종 승인을 뜻하지 않는다.
"""
import copy
import json

from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash
from generators.kimodo.multiview_review_report import build_multiview_review_report
from generators.kimodo.multiview_reference_candidate import build_multiview_ratio_candidate
from generators.kimodo.reference_proportions import REFERENCE_RATIO_SCHEMA, REFERENCE_SEGMENT_GROUPS

REVIEWED_BUNDLE_SCHEMA_VERSION = 'kimodo-reviewed-multiview-bundle-v1'
REVIEWED_BUNDLE_MAXIMUM_BYTES = 2 * 1024 * 1024


def validate_reviewed_multiview_bundle(current_bundle_record, current_image_hashes):
    """참조 이미지·관측·가중치·3D 골격이 같은 출처인지 확인한다."""
    if not isinstance(current_bundle_record, dict) or set(current_bundle_record) != {'schema','reference_observations','skeleton'} or current_bundle_record['schema'] != REVIEWED_BUNDLE_SCHEMA_VERSION:
        raise ValueError('검수 스켈레톤 묶음 계약 오류')
    try:
        current_payload_size=len(json.dumps(current_bundle_record,ensure_ascii=False,allow_nan=False).encode())
    except (TypeError,ValueError) as current_error:
        raise ValueError('검수 스켈레톤 묶음 직렬화 오류') from current_error
    if current_payload_size > REVIEWED_BUNDLE_MAXIMUM_BYTES:
        raise ValueError('검수 스켈레톤 묶음이 2MiB를 초과합니다.')
    if not isinstance(current_image_hashes,list) or not current_image_hashes or any(not isinstance(current_hash,str) or len(current_hash)!=64 or any(current_character not in '0123456789abcdef' for current_character in current_hash) for current_hash in current_image_hashes):
        raise ValueError('생성 참조 이미지 해시 형식 오류')
    current_reference=current_bundle_record['reference_observations']
    current_skeleton=current_bundle_record['skeleton']
    if not isinstance(current_reference,dict) or not isinstance(current_skeleton,dict):
        raise ValueError('검수 관측 또는 스켈레톤 형식 오류')
    if current_reference.get('reference_image_sha256') != current_image_hashes or current_skeleton.get('reference_image_sha256') != current_image_hashes:
        raise ValueError('검수 스켈레톤의 참조 이미지가 생성 입력과 다릅니다.')
    if current_skeleton.get('observation_sha256') != calculate_multiview_observation_hash(current_reference):
        raise ValueError('검수 스켈레톤의 참조 관측이 다릅니다.')
    build_multiview_review_report(current_reference,current_skeleton)
    current_temporary_ratio={'schema':REFERENCE_RATIO_SCHEMA,'body_axis':{},'ratios':{current_name:1.0 for current_name in REFERENCE_SEGMENT_GROUPS}}
    build_multiview_ratio_candidate(current_temporary_ratio,current_skeleton)
    return copy.deepcopy(current_bundle_record)


def apply_reviewed_multiview_bundle(current_ratio_record, current_bundle_record, current_image_hashes):
    """저장된 입력 출처를 재검증한 뒤 작업용 신체 비율 후보를 만든다."""
    current_validated_bundle = validate_reviewed_multiview_bundle(current_bundle_record, current_image_hashes)
    if current_ratio_record.get('reference_image_sha256') != current_image_hashes:
        raise ValueError('작업 참조 이미지 해시가 검수 입력과 다릅니다.')
    current_candidate = build_multiview_ratio_candidate(current_ratio_record, current_validated_bundle['skeleton'])
    current_candidate['weighted_reference_observations'] = current_validated_bundle['reference_observations']
    current_candidate['method'] = '명시적으로 선택한 검수용 가중 3D 몸·얼굴 골격 비율 후보'
    return current_candidate
