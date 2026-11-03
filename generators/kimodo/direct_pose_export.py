"""검출 없이 SOMA 몸 관절을 Fun Control 규격 영상으로 내보낸다."""
import json
from pathlib import Path
import numpy as np
import imageio.v2 as imageio
from PIL import ImageOps
from generators.kimodo.soma_pose import project_recorded_camera_points, SOMA_BODY_JOINT_NAMES
from generators.kimodo.pose_rendering import render_fun_control_body

DIRECT_POSE_OUTPUT_FPS = 16
DIRECT_POSE_OUTPUT_SIZE = (832, 480)


def export_direct_pose_video(current_attempt_root, current_output_root, current_direction_names, current_scale_percent=85.0):
    if type(current_scale_percent) not in (int,float) or not np.isfinite(current_scale_percent) or not 10 <= current_scale_percent <= 100:
        raise ValueError('포즈 배율은 10~100 범위의 유한한 숫자여야 합니다.')
    current_output_root = Path(current_output_root)
    current_output_root.mkdir(parents=True, exist_ok=True)
    current_attempt_root = Path(current_attempt_root)
    current_render_record = json.loads((current_attempt_root/'soma-render.json').read_text())
    if 'cameras' not in current_render_record:
        raise ValueError('SOMA 카메라 기록이 필요합니다. 카메라 기록을 포함해 다시 렌더하세요.')
    current_joint_names = json.loads((current_attempt_root/'skeleton.json').read_text())['joint_names']
    with np.load(current_attempt_root/current_render_record['source'], allow_pickle=False) as current_motion_archive:
        current_joint_positions = current_motion_archive['posed_joints']
    current_reference_path = current_attempt_root/'reference-proportions.json'
    current_reference_record = json.loads(current_reference_path.read_text()) if current_reference_path.is_file() else None
    current_body_positions = np.zeros((len(current_joint_positions),18,3))
    for current_joint_index,current_joint_name in enumerate(SOMA_BODY_JOINT_NAMES):
        if current_joint_name:
            current_body_positions[:,current_joint_index] = current_joint_positions[:,current_joint_names.index(current_joint_name)]
    current_body_positions[:,1] = current_body_positions[:,[2,5]].mean(axis=1)
    if current_reference_record is not None:
        from generators.kimodo.reference_proportions import apply_reference_proportions
        current_body_positions = apply_reference_proportions(current_body_positions,current_reference_record)
    current_direction_points = {}
    for current_direction_name in current_direction_names:
        current_projected_points = project_recorded_camera_points(current_body_positions, current_render_record['cameras'][current_direction_name])
        current_body_points = np.zeros((len(current_projected_points),18,3))
        current_body_points[:,1:16,:2] = current_projected_points[:,1:16]
        current_body_points[:,1:16,2] = 1
        current_body_points[:,1:16,:2] = (current_body_points[:,1:16,:2]-np.array(DIRECT_POSE_OUTPUT_SIZE)/2)*current_scale_percent/100+np.array(DIRECT_POSE_OUTPUT_SIZE)/2
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
    current_metadata_record = {'reference_proportions': current_reference_record, 'proportion_basis': '3D 몸통 기준 보정 후 원본 카메라 투영', 'source': 'SOMA 3D joints', 'fps': DIRECT_POSE_OUTPUT_FPS, 'size': DIRECT_POSE_OUTPUT_SIZE, 'missing_points': [0,16,17], 'limitations': '코·귀·손 상세·얼굴 상세는 합성하지 않음. 목은 어깨 중점. 가림 판정 없음. confidence=1은 검출 확률이 아닌 대응 관절 존재 표시.', 'directions': current_output_records}
    (current_output_root/'soma-direct-pose.json').write_text(json.dumps(current_metadata_record, ensure_ascii=False))
    return current_metadata_record
