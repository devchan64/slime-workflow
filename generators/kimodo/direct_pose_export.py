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


def adjust_projected_body_axis(current_projected_points, current_reference_record):
    """화면에 투영된 얼굴·몸통 비율로 어깨와 팔을 함께 평행 이동한다."""
    from generators.kimodo.reference_proportions import calculate_reference_torso_gain
    current_projected_points = np.asarray(current_projected_points, dtype=float)
    current_torso_gain = calculate_reference_torso_gain(current_projected_points, current_reference_record)
    current_shoulder_centers = current_projected_points[:,[2,5]].mean(axis=1)
    current_hip_centers = current_projected_points[:,[8,11]].mean(axis=1)
    current_shoulder_offsets = (current_shoulder_centers-current_hip_centers)*(current_torso_gain-1)
    current_adjusted_points = current_projected_points.copy()
    current_adjusted_points[:,[1,2,3,4,5,6,7]] += current_shoulder_offsets[:,None,:]
    return current_adjusted_points,current_torso_gain


def export_direct_pose_video(current_attempt_root, current_output_root, current_direction_names, current_reference_ratio_path=None):
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
    current_axis_gain=None
    if current_reference_record is not None:
        from generators.kimodo.reference_proportions import apply_reference_proportions, calculate_reference_torso_gain
        current_axis_gain=calculate_reference_torso_gain(current_body_positions,current_reference_record)
        current_body_positions = apply_reference_proportions(current_body_positions,current_reference_record)
    current_direction_points = {}
    current_direction_axis_gains = {}
    for current_direction_name in current_direction_names:
        current_projected_points = project_recorded_camera_points(current_body_positions, current_render_record['cameras'][current_direction_name])
        if current_reference_record is not None:
            current_projected_points,current_projected_gain = adjust_projected_body_axis(current_projected_points,current_reference_record)
            current_direction_axis_gains[current_direction_name] = current_projected_gain
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
    current_metadata_record = {'reference_proportions': current_reference_record, 'body_axis_torso_gain':current_axis_gain, 'projected_body_axis_gains':current_direction_axis_gains, 'proportion_basis': '3D 몸통 보정 후 방향별 2D 얼굴·어깨·골반 비율 보정', 'source': 'SOMA 3D joints', 'projection_scale_basis': '기록된 SOMA 카메라 배율 그대로 사용 · 추가 배율 없음', 'additional_scale_percent': 100.0, 'fps': DIRECT_POSE_OUTPUT_FPS, 'size': DIRECT_POSE_OUTPUT_SIZE, 'missing_points': [], 'head_anchors': current_anchor_record, 'limitations': '코·귀는 검증 기록이 있는 Head 로컬 앵커 추정. 참조 얼굴 비율도 2D 추정이며 실제 목 길이 복원이 아님. 손 상세·얼굴 상세는 합성하지 않음. 목은 어깨 중점. 가림 판정 없음. confidence=1은 검출 확률이 아닌 대응 관절 존재 표시.', 'directions': current_output_records}
    (current_output_root/'soma-direct-pose.json').write_text(json.dumps(current_metadata_record, ensure_ascii=False))
    return current_metadata_record


if __name__ == '__main__':
    import sys
    export_direct_pose_video(Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3:])
