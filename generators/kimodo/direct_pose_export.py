"""검출 없이 SOMA 몸 관절을 Fun Control 규격 영상으로 내보낸다."""
import json
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
from PIL import ImageOps
from generators.kimodo.soma_pose import project_recorded_camera_points, SOMA_BODY_JOINT_NAMES
from generators.kimodo.pose_rendering import render_fun_control_body

DIRECT_POSE_OUTPUT_FPS = 30
DIRECT_POSE_OUTPUT_SIZE = (832, 480)


def adjust_projected_body_axis(current_projected_points, current_reference_record, current_axis_basis_points=None):
    """화면에 투영된 얼굴·몸통 비율로 어깨와 팔을 함께 평행 이동한다."""
    from generators.kimodo.reference_proportions import calculate_reference_torso_gain
    current_projected_points = np.asarray(current_projected_points, dtype=float)
    current_axis_basis_points = current_projected_points if current_axis_basis_points is None else np.asarray(current_axis_basis_points,dtype=float)
    if current_axis_basis_points.shape != current_projected_points.shape or not np.isfinite(current_axis_basis_points).all():
        raise ValueError('몸통 축 기준 포즈의 좌표 형식 오류')
    current_torso_gain = calculate_reference_torso_gain(current_axis_basis_points, current_reference_record)
    current_shoulder_centers = current_axis_basis_points[:,[2,5]].mean(axis=1)
    current_hip_centers = current_axis_basis_points[:,[8,11]].mean(axis=1)
    current_shoulder_offsets = (current_shoulder_centers-current_hip_centers)*(current_torso_gain-1)
    current_adjusted_points = current_projected_points.copy()
    current_adjusted_points[:,[1,2,3,4,5,6,7]] += current_shoulder_offsets[:,None,:]
    return current_adjusted_points,current_torso_gain


def scale_pose_about_camera(current_projected_points, current_scale_percent, current_image_size=DIRECT_POSE_OUTPUT_SIZE):
    """보정 완료 좌표를 고정 카메라 화면 중심으로 균등 축소한다."""
    current_projected_points = np.asarray(current_projected_points, dtype=float)
    if not np.isfinite(current_scale_percent) or not 10 <= current_scale_percent <= 100:
        raise ValueError('포즈 배율은 10~100%여야 합니다.')
    if current_projected_points.ndim != 3 or current_projected_points.shape[1:] != (18, 2) or not np.isfinite(current_projected_points).all():
        raise ValueError('화면 중심 축소 좌표 형식 오류')
    current_camera_center = np.asarray(current_image_size, dtype=float)/2
    if current_camera_center.shape != (2,) or not np.isfinite(current_camera_center).all() or (current_camera_center <= 0).any():
        raise ValueError('카메라 화면 크기 오류')
    return current_camera_center + (current_projected_points-current_camera_center)*(current_scale_percent/100)


def export_direct_pose_video(current_attempt_root, current_output_root, current_direction_names, current_reference_ratio_path=None, current_face_anchor_calibration=None, current_scale_percent=80.0):
    current_output_root = Path(current_output_root)
    current_output_root.mkdir(parents=True, exist_ok=True)
    current_attempt_root = Path(current_attempt_root)
    current_render_record = json.loads((current_attempt_root/'soma-render.json').read_text())
    if 'cameras' not in current_render_record:
        raise ValueError('SOMA 카메라 기록이 필요합니다. 카메라 기록을 포함해 다시 렌더하세요.')
    current_joint_names = json.loads((current_attempt_root/'skeleton.json').read_text())['joint_names']
    with np.load(current_attempt_root/current_render_record['source'], allow_pickle=False) as current_motion_archive:
        current_joint_positions = current_motion_archive['posed_joints']
        current_joint_rotations = current_motion_archive['global_rot_mats']
    current_reference_path = Path(current_reference_ratio_path) if current_reference_ratio_path is not None else current_attempt_root/'reference-proportions.json'
    if current_reference_ratio_path is not None and not current_reference_path.is_file():
        raise ValueError(f'지정한 참조 신체 비율 파일 누락: {current_reference_path}')
    current_reference_record = json.loads(current_reference_path.read_text()) if current_reference_path.is_file() else None
    current_body_positions = np.zeros((len(current_joint_positions),18,3))
    for current_joint_index,current_joint_name in enumerate(SOMA_BODY_JOINT_NAMES):
        if current_joint_name:
            current_body_positions[:,current_joint_index] = current_joint_positions[:,current_joint_names.index(current_joint_name)]
    from generators.kimodo.contracts import KIMODO_CONFIG_ROOT,UniqueConfigLoader
    import yaml
    current_anchor_record=yaml.load((KIMODO_CONFIG_ROOT/'head-anchors.yaml').read_text(),Loader=UniqueConfigLoader)
    if current_anchor_record['schema_version']!=1 or set(current_anchor_record['anchors'])!={'nose','right_ear','left_ear'}:
        raise ValueError('코·귀 앵커 설정 계약 오류')
    current_head_index=current_joint_names.index('Head')
    for current_landmark_index,current_landmark_name in [(0,'nose'),(16,'right_ear'),(17,'left_ear')]:
        current_anchor_offset=np.asarray(current_anchor_record['anchors'][current_landmark_name]['local_offset'])
        if current_anchor_offset.shape!=(3,) or not np.isfinite(current_anchor_offset).all():
            raise ValueError('코·귀 앵커 좌표 오류')
        current_body_positions[:,current_landmark_index]=current_joint_positions[:,current_head_index]+np.einsum('nij,j->ni',current_joint_rotations[:,current_head_index],current_anchor_offset)
    current_body_positions[:,1] = current_body_positions[:,[2,5]].mean(axis=1)
    current_original_hip_y = current_body_positions[:,[8,11],1].mean(1).copy()
    current_axis_gain=None
    if current_reference_record is not None:
        from generators.kimodo.reference_proportions import apply_reference_proportions, calculate_reference_torso_gain
        current_axis_gain=calculate_reference_torso_gain(current_body_positions,current_reference_record)
        current_body_positions = apply_reference_proportions(current_body_positions,current_reference_record)
    current_axis_basis_positions = current_body_positions.copy()
    current_experimental_face_binding = None
    current_reference_face_source = None
    if current_face_anchor_calibration is not None:
        if current_reference_ratio_path is None or current_reference_record is None or 'weighted_body_face_candidate' not in current_reference_record:
            raise ValueError('얼굴 앵커 시험에는 명시적인 가중 3D 비율 후보가 필요합니다.')
        from generators.kimodo.multiview_face_anchor_experiment import apply_multiview_face_anchors, validate_face_anchor_calibration
        current_face_offsets = validate_face_anchor_calibration(current_face_anchor_calibration, current_reference_record['weighted_body_face_candidate'], current_joint_names)
        current_body_positions = apply_multiview_face_anchors(current_body_positions, current_joint_positions[:,current_head_index], current_joint_rotations[:,current_head_index], current_face_offsets)
        current_experimental_face_binding = current_face_anchor_calibration['binding_sha256']
    elif current_reference_record is not None:
        from generators.kimodo.reference_face_anchors import apply_registered_reference_face
        current_body_positions, current_reference_face_source = apply_registered_reference_face(
            current_body_positions, current_joint_positions[:,current_head_index],
            current_joint_rotations[:,current_head_index], current_reference_record)
    current_direction_points = {}
    current_direction_axis_gains = {}
    for current_direction_name in current_direction_names:
        current_projected_points = project_recorded_camera_points(current_body_positions, current_render_record['cameras'][current_direction_name])
        if current_reference_record is not None:
            current_axis_basis_points = project_recorded_camera_points(current_axis_basis_positions,current_render_record['cameras'][current_direction_name]) if current_experimental_face_binding is not None or current_reference_face_source is not None else None
            current_projected_points,current_projected_gain = adjust_projected_body_axis(current_projected_points,current_reference_record,current_axis_basis_points)
            current_direction_axis_gains[current_direction_name] = current_projected_gain
        current_projected_points = scale_pose_about_camera(current_projected_points, current_scale_percent, (current_render_record['cameras'][current_direction_name]['width'],current_render_record['cameras'][current_direction_name]['height']))
        current_body_points = np.zeros((len(current_projected_points),18,3))
        current_body_points[:,:,:2] = current_projected_points
        current_body_points[:,:,2] = 1
        current_direction_points[current_direction_name] = current_body_points
    current_output_records = {}
    for current_direction_name, current_pose_points in current_direction_points.items():
        current_frame_count = int((len(current_pose_points)-1)*DIRECT_POSE_OUTPUT_FPS/30)+1
        current_source_indices = [round(current_frame_index*30/DIRECT_POSE_OUTPUT_FPS) for current_frame_index in range(current_frame_count)]
        current_video_path = current_output_root/f'soma-direct-{current_direction_name}.mp4'
        if current_video_path.exists():
            raise ValueError('기존 직접 투영 결과는 덮어쓰지 않습니다.')
        with imageio.get_writer(str(current_video_path), fps=DIRECT_POSE_OUTPUT_FPS, codec='libx264', quality=8, macro_block_size=1) as current_video_writer:
            for current_source_index in current_source_indices:
                current_pose_image = render_fun_control_body(current_pose_points[current_source_index].tolist())
                current_video_writer.append_data(np.asarray(ImageOps.pad(current_pose_image, DIRECT_POSE_OUTPUT_SIZE, color='black')))
        current_output_records[current_direction_name] = {'video': current_video_path.name, 'source_frames': current_source_indices, 'body_points_832x480': current_pose_points[current_source_indices].tolist()}
    current_hip_anchor_record = {'basis':'각 프레임 SOMA 보정 전 좌우 고관절 중점 Y', 'unit':'meter', 'maximum_error':float(np.max(np.abs(current_body_positions[:,[8,11],1].mean(1)-current_original_hip_y))), 'frames':len(current_body_positions)}
    current_metadata_record = {'pelvis_y_anchor':current_hip_anchor_record, 'reference_proportions': current_reference_record, 'body_axis_torso_gain':current_axis_gain, 'projected_body_axis_gains':current_direction_axis_gains, 'proportion_basis': '3D 몸통 보정 후 방향별 2D 얼굴·어깨·골반 비율 보정', 'source': 'SOMA 3D joints', 'projection_scale_basis': '보정 완료 후 고정 카메라 화면 중심 XY 기준 균등 축소', 'additional_scale_percent': current_scale_percent, 'fps': DIRECT_POSE_OUTPUT_FPS, 'size': DIRECT_POSE_OUTPUT_SIZE, 'missing_points': [], 'head_anchors': current_anchor_record, 'experimental_face_anchor_binding':current_experimental_face_binding, 'limitations': '코·귀는 검증 기록이 있는 Head 로컬 앵커 추정. 참조 얼굴 비율도 2D 추정이며 실제 목 길이 복원이 아님. 손 상세·얼굴 상세는 합성하지 않음. 목은 어깨 중점. 가림 판정 없음. confidence=1은 검출 확률이 아닌 대응 관절 존재 표시.', 'directions': current_output_records}
    if current_experimental_face_binding is not None:
        current_metadata_record['experimental_face_calibration_source'] = current_face_anchor_calibration.get('source')
        current_metadata_record['limitations'] = '실험용 가중 3D 얼굴 앵커 사용. 참조 관절·초기 교정의 불확실성 및 얼굴 가림 판정 없음. 손 상세·얼굴 상세는 합성하지 않음. 목은 어깨 중점.'
    current_metadata_record['reference_face_anchors'] = current_reference_face_source
    if current_reference_face_source is not None:
        current_metadata_record['limitations'] = current_reference_face_source['limitations'] + ' 첫 프레임 몸 기준으로 정렬한 뒤 SOMA Head 상대 운동 적용. 얼굴 상세·가림 판정 없음.'
    (current_output_root/'soma-direct-pose.json').write_text(json.dumps(current_metadata_record, ensure_ascii=False))
    return current_metadata_record


if __name__ == '__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='SOMA 직접 포즈 출력')
    current_parser.add_argument('attempt',type=Path)
    current_parser.add_argument('output',type=Path)
    current_parser.add_argument('directions',nargs='+')
    current_parser.add_argument('--scale-percent',type=float,default=80.0)
    current_parser.add_argument('--request-json',type=Path)
    current_arguments=current_parser.parse_args()
    current_calibration=None
    current_reference_path=None
    if current_arguments.request_json is not None:
        current_request=json.loads(current_arguments.request_json.read_text())
        current_calibration=current_request.get('proportion_face_anchor_calibration')
        if current_calibration is None or 'proportion_reviewed_multiview' not in current_request:
            raise ValueError('얼굴 앵커와 검수 골격 요청이 필요합니다.')
        current_reference_path=current_arguments.attempt/'reference-proportions.json'
        current_ratio=json.loads(current_reference_path.read_text())
        if current_ratio.get('weighted_body_face_candidate') != current_request['proportion_reviewed_multiview']['skeleton']:
            raise ValueError('얼굴 앵커의 적용 골격이 요청과 다릅니다.')
    export_direct_pose_video(current_arguments.attempt,current_arguments.output,current_arguments.directions,current_reference_path,current_calibration,current_arguments.scale_percent)
