"""DWPose와 공통 3D 재투영·가중치를 나란히 검수하는 산출물."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
from generators.kimodo.multiview_body_face_experiment import FACE_LANDMARK_INDICES

REVIEW_BODY_JOINT_INDICES = tuple(range(2,14))
REVIEW_BODY_EDGES = ((2,5),(2,3),(3,4),(5,6),(6,7),(2,8),(5,11),(8,11),(8,9),(9,10),(11,12),(12,13))
REVIEW_FACE_EDGES = ((0,14),(14,16),(0,15),(15,17))
REVIEW_VIEW_COUNT = 8


def build_multiview_review_report(current_reference_record, current_skeleton_record, current_heldout_record=None):
    """방향·관절별 관측, 가중치, 재투영과 제외 검증 값을 보존한다."""
    if current_skeleton_record.get('schema') != 'kimodo-multiview-body-face-experiment-v1' or current_skeleton_record.get('body18_joint_indices') != list(REVIEW_BODY_JOINT_INDICES) or current_skeleton_record.get('face_joint_indices') != list(FACE_LANDMARK_INDICES):
        raise ValueError('검수할 몸·얼굴 3D 골격 계약 오류')
    if current_skeleton_record.get('excluded_body') is not None or current_skeleton_record.get('excluded_face') is not None:
        raise ValueError('전체 관측 최종 골격이 필요합니다.')
    from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash
    if current_skeleton_record.get('observation_sha256') != calculate_multiview_observation_hash(current_reference_record):
        raise ValueError('3D 골격의 참조 관절 출처가 일치하지 않습니다.')
    if current_skeleton_record.get('reference_image_sha256') != current_reference_record.get('reference_image_sha256'):
        raise ValueError('참조 이미지 출처 기록이 일치하지 않습니다.')
    current_table = current_skeleton_record.get('joint_weight_table')
    current_input_weights = validate_multiview_joint_weights(current_table)
    current_views = current_skeleton_record.get('views')
    current_reference_points = current_reference_record.get('keypoints')
    if not isinstance(current_views, list) or len(current_views) != REVIEW_VIEW_COUNT or not isinstance(current_reference_points, list) or len(current_reference_points) != REVIEW_VIEW_COUNT:
        raise ValueError('검수할 8방향 관측이 필요합니다.')
    current_heldout_map = {}
    if current_heldout_record is not None:
        if not isinstance(current_heldout_record, dict) or not isinstance(current_heldout_record.get('excluded_observations'), list):
            raise ValueError('제외 관측 검증 기록 형식 오류')
        if current_heldout_record.get('observation_sha256') != current_skeleton_record['observation_sha256'] or current_heldout_record.get('joint_weight_table') != current_table:
            raise ValueError('제외 관측의 입력 관절 또는 가중치가 일치하지 않습니다.')
        if current_heldout_record.get('fit_context_sha256') != current_skeleton_record.get('fit_context_sha256'):
            raise ValueError('제외 관측과 골격의 초기 추정·가시성 출처가 일치하지 않습니다.')
        for current_row in current_heldout_record['excluded_observations']:
            if not isinstance(current_row, dict) or type(current_row.get('observation')) is not int or type(current_row.get('joint')) is not int or not 1 <= current_row['observation'] <= 8 or current_row['joint'] not in (*REVIEW_BODY_JOINT_INDICES, *FACE_LANDMARK_INDICES):
                raise ValueError('제외 관측 번호 오류')
            current_key = (current_row['observation'], current_row['joint'])
            current_error = current_row.get('error_px')
            if current_key in current_heldout_map or (current_error is not None and (type(current_error) not in (int,float) or not np.isfinite(current_error) or current_error < 0)):
                raise ValueError('제외 관측 중복 또는 오차 오류')
            current_heldout_map[current_key] = current_row
    current_results = []
    for current_view_index, (current_view, current_points) in enumerate(zip(current_views, current_reference_points)):
        current_points = np.asarray(current_points, dtype=float)
        current_body = np.asarray(current_view.get('body_xy'), dtype=float)
        current_face = np.asarray(current_view.get('face_xy'), dtype=float)
        current_body_weights = np.asarray(current_view.get('body_fit_weights'), dtype=float)
        current_face_weights = np.asarray(current_view.get('face_fit_weights'), dtype=float)
        if current_view.get('observation') != current_view_index + 1 or current_points.shape != (18,3) or current_body.shape != (12,2) or current_face.shape != (5,2) or current_body_weights.shape != (12,) or current_face_weights.shape != (5,) or not all(np.isfinite(current_array).all() for current_array in (current_points,current_body,current_face,current_body_weights,current_face_weights)) or np.any(current_body_weights < 0) or np.any(current_face_weights < 0):
            raise ValueError('검수할 관절 좌표 또는 가중치 형식 오류')
        current_joints = []
        for current_joint_index in (*REVIEW_BODY_JOINT_INDICES, *FACE_LANDMARK_INDICES):
            current_is_body = current_joint_index in REVIEW_BODY_JOINT_INDICES
            current_offset = current_joint_index - 2 if current_is_body else FACE_LANDMARK_INDICES.index(current_joint_index)
            current_projected = (current_body if current_is_body else current_face)[current_offset]
            current_effective_weight = float((current_body_weights if current_is_body else current_face_weights)[current_offset])
            current_distance = float(np.linalg.norm(current_projected-current_points[current_joint_index,:2]))
            current_source_record = current_table['views'][current_view_index]['joints'][current_joint_index]
            current_joints.append({'joint':current_joint_index, 'observed_xy':current_points[current_joint_index,:2].tolist(), 'projected_xy':current_projected.tolist(), 'detector_score':float(current_points[current_joint_index,2]), 'declared_weight':current_input_weights[current_view_index][current_joint_index], 'effective_weight':current_effective_weight, 'weight_reason':current_source_record['reason'], 'fitted_error_px':current_distance if current_effective_weight > 0 else None, 'heldout':current_heldout_map.get((current_view_index+1,current_joint_index))})
        current_results.append({'observation':current_view_index+1,'fitted_yaw_degrees':current_view['fitted_yaw_degrees'],'joints':current_joints})
    return {'schema':'kimodo-multiview-review-v1','views':current_results,'limitations':['관절별 방향 가중치는 사용자가 제공한 판단이며 참조 이미지 정답을 보장하지 않음','제외 검증은 초기 카메라와 다른 관절의 이전 적합에 의존할 수 있음', '이전 기록에 입력 묶음 해시가 없으면 초기 추정·가시성 일치를 확인할 수 없음','표시된 학습 오차는 독립 정확도 검증이 아님','목 관절은 양 어깨의 파생 중심이며 이 추정의 독립 관측에 포함되지 않음']}


def render_multiview_review_overlay(current_image, current_report):
    """참조 이미지에 사용한 DWPose와 3D 재투영을 함께 표시한다."""
    current_output = current_image.convert('RGB').copy()
    current_draw = ImageDraw.Draw(current_output)
    for current_view in current_report['views']:
        current_points = {current_joint['joint']:current_joint for current_joint in current_view['joints']}
        for current_start, current_end in (*REVIEW_BODY_EDGES,*REVIEW_FACE_EDGES):
            current_first,current_second = current_points[current_start],current_points[current_end]
            if current_first['effective_weight'] <= 0 or current_second['effective_weight'] <= 0:
                continue
            for current_field,current_color in (('observed_xy',(0,180,0)),('projected_xy',(220,0,200))):
                current_draw.line([tuple(current_first[current_field]),tuple(current_second[current_field])],fill=current_color,width=2)
        for current_joint in current_view['joints']:
            if current_joint['effective_weight'] <= 0:
                continue
            for current_field,current_color in (('observed_xy',(0,180,0)),('projected_xy',(220,0,200))):
                current_x,current_y = current_joint[current_field]
                current_draw.ellipse((current_x-3,current_y-3,current_x+3,current_y+3),fill=current_color)
    return current_output


if __name__ == '__main__':
    import argparse
    current_parser = argparse.ArgumentParser(description='8방향 DWPose와 공통 3D 골격 검수 기록')
    current_parser.add_argument('reference_json',type=Path)
    current_parser.add_argument('skeleton_json',type=Path)
    current_parser.add_argument('reference_image',type=Path)
    current_parser.add_argument('output_dir',type=Path)
    current_parser.add_argument('--heldout-json',type=Path)
    current_arguments = current_parser.parse_args()
    current_output_json = current_arguments.output_dir/'multiview-review.json'
    current_output_image = current_arguments.output_dir/'multiview-review.png'
    if current_output_json.exists() or current_output_image.exists():
        raise ValueError('기존 검수 결과를 덮어쓰지 않습니다.')
    current_reference = json.loads(current_arguments.reference_json.read_text())
    current_skeleton = json.loads(current_arguments.skeleton_json.read_text())
    current_heldout = json.loads(current_arguments.heldout_json.read_text()) if current_arguments.heldout_json else None
    current_report = build_multiview_review_report(current_reference,current_skeleton,current_heldout)
    current_report['reference_image_sha256'] = hashlib.sha256(current_arguments.reference_image.read_bytes()).hexdigest()
    if current_skeleton.get('reference_image_sha256') != [current_report['reference_image_sha256']]:
        raise ValueError('3D 골격의 참조 이미지 해시가 없거나 일치하지 않습니다.')
    with Image.open(current_arguments.reference_image) as current_image:
        current_overlay = render_multiview_review_overlay(current_image,current_report)
    current_arguments.output_dir.mkdir(parents=True,exist_ok=True)
    current_overlay.save(current_output_image)
    current_output_json.write_text(json.dumps(current_report,ensure_ascii=False,indent=2))
    print(f'8방향 검수 기록 저장: {current_arguments.output_dir}',flush=True)
