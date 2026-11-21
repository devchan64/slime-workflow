"""얼굴 관측을 하나씩 제외한 공통 3D 재투영 오차를 기록한다."""
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_body_face_experiment import FACE_LANDMARK_INDICES, fit_multiview_body_face
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash,calculate_multiview_fit_context_hash


def calculate_face_holdout_report(current_reference_record, current_initial_record, current_visibility_rows, current_weight_table, current_baseline_record, current_body_holdout_record):
    """기존 몸 검증과 같은 입력에 대한 얼굴 제외 관측을 추가한다."""
    current_observation_hash = calculate_multiview_observation_hash(current_reference_record)
    if current_baseline_record.get('observation_sha256') != current_observation_hash or current_body_holdout_record.get('observation_sha256') != current_observation_hash:
        raise ValueError('제외 검증과 참조 관측 출처가 다릅니다.')
    if current_baseline_record.get('joint_weight_table') != current_weight_table or current_body_holdout_record.get('joint_weight_table') != current_weight_table:
        raise ValueError('제외 검증과 방향별 가중치가 다릅니다.')
    current_context_hash=calculate_multiview_fit_context_hash(current_observation_hash,current_initial_record,current_visibility_rows,current_weight_table)
    if current_baseline_record.get('fit_context_sha256')!=current_context_hash or current_body_holdout_record.get('fit_context_sha256')!=current_context_hash:
        raise ValueError('제외 검증의 초기 추정·가시성·가중치 출처가 다르거나 기록이 없습니다.')
    from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
    from generators.kimodo.multiview_reference_experiment import MULTIVIEW_MINIMUM_SCORE
    current_direction_weights = validate_multiview_joint_weights(current_weight_table)
    if not isinstance(current_visibility_rows,list) or len(current_visibility_rows)!=8 or any(not isinstance(current_row,list) or len(current_row)!=5 or any(type(current_value) is not bool for current_value in current_row) for current_row in current_visibility_rows):
        raise ValueError('얼굴 가시성은 8×5 불리언 배열이어야 합니다.')
    if not isinstance(current_baseline_record.get('views'),list) or len(current_baseline_record['views'])!=8:
        raise ValueError('기준 골격의 8방향 관측이 필요합니다.')
    for current_view_index, current_view_record in enumerate(current_baseline_record['views']):
        current_expected_weights = []
        for current_face_offset,current_joint_index in enumerate(FACE_LANDMARK_INDICES):
            current_score = current_reference_record['keypoints'][current_view_index][current_joint_index][2]
            current_expected_weights.append(min(float(current_score),1.)*current_direction_weights[current_view_index][current_joint_index] if current_visibility_rows[current_view_index][current_face_offset] and current_score>=MULTIVIEW_MINIMUM_SCORE else 0.)
        if not np.allclose(current_view_record['face_fit_weights'],current_expected_weights,atol=1e-10):
            raise ValueError('얼굴 가시성 또는 가중치가 기준 골격 적합 입력과 다릅니다.')
    current_records = list(current_body_holdout_record['excluded_observations'])
    if any(current_row.get('joint') in FACE_LANDMARK_INDICES for current_row in current_records):
        raise ValueError('몸 제외 검증에 얼굴 관절이 이미 포함되어 있습니다.')
    for current_view_index, current_view_record in enumerate(current_baseline_record['views']):
        for current_face_offset, current_joint_index in enumerate(FACE_LANDMARK_INDICES):
            if current_view_record['face_fit_weights'][current_face_offset] <= 0:
                continue
            current_observed = np.asarray(current_reference_record['keypoints'][current_view_index][current_joint_index][:2], dtype=float)
            try:
                current_fitted = fit_multiview_body_face(current_reference_record, current_initial_record, current_visibility_rows, current_excluded_face=(current_view_index,current_joint_index), current_joint_weight_table=current_weight_table)
            except ValueError as current_error:
                current_records.append({'observation':current_view_index+1,'joint':current_joint_index,'error_px':None,'reason':str(current_error)})
                continue
            current_predicted = np.asarray(current_fitted['views'][current_view_index]['face_xy'][current_face_offset], dtype=float)
            current_records.append({'observation':current_view_index+1,'joint':current_joint_index,'error_px':float(np.linalg.norm(current_predicted-current_observed)),'prediction':current_predicted.tolist(),'observed':current_observed.tolist()})
        print(f'Kimodo 얼굴 제외 관측 검증: {current_view_index+1}/8',flush=True)
    return {'observation_sha256':current_observation_hash,'fit_context_sha256':current_context_hash,'joint_weight_table':current_weight_table,'excluded_observations':current_records,'limitation':'초기 카메라와 다른 초기 관절은 기존 적합 결과를 사용하므로 완전히 독립된 검증이 아님. 골반은 정규화 기준이라 제외 검증하지 않음.'}


if __name__ == '__main__':
    import argparse
    current_parser = argparse.ArgumentParser(description='8방향 얼굴 관측 제외 검증')
    for current_name in ('reference','initial','visibility','weights','baseline','body_holdout','output'):
        current_parser.add_argument(current_name,type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 제외 검증 결과를 덮어쓰지 않습니다.')
    current_inputs=[json.loads(getattr(current_arguments,current_name).read_text()) for current_name in ('reference','initial','visibility','weights','baseline','body_holdout')]
    current_result=calculate_face_holdout_report(*current_inputs)
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
