"""원본 관절의 고정 카메라 투영. 루트 이동·회전과 관절은 보정하지 않는다."""
import math
import numpy as np
from PIL import Image, ImageDraw

SKELETON_PARENT_INDICES = (-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19)
PREVIEW_MARGIN_PIXELS = 32
PREVIEW_BACKGROUND_COLOR = (245, 245, 245)
PREVIEW_BONE_COLOR = (38, 71, 94)
PREVIEW_LINE_WIDTH = 4
HEAD_GUIDE_LENGTH_METERS = 0.18
WRIST_GUIDE_LENGTH_METERS = 0.12
WRIST_AXIS_COLORS = ((220, 50, 50), (40, 170, 70), (40, 100, 230))


def validate_motion_output(current_output_arrays, expected_frame_count):
    current_expected_shapes = {'keypoints3d': (expected_frame_count, 52, 3), 'world_joints': (expected_frame_count, 52, 3), 'rot6d': (expected_frame_count, 22, 6), 'transl': (expected_frame_count, 3), 'root_rotations_mat': (expected_frame_count, 3, 3), 'latent_denorm': (expected_frame_count, 201)}
    if set(current_output_arrays) != set(current_expected_shapes):
        raise ValueError('HY-Motion 출력 필드 불일치')
    for current_field_name, current_expected_shape in current_expected_shapes.items():
        current_array_value = current_output_arrays[current_field_name]
        if current_array_value.shape != current_expected_shape or not np.issubdtype(current_array_value.dtype, np.floating) or not np.isfinite(current_array_value).all():
            raise ValueError(f'HY-Motion 출력 크기·자료형·유한값 오류: {current_field_name}, {current_array_value.shape}')


def render_motion_previews(current_joint_frames, current_request_record, current_config_record, current_output_path, current_progress_callback, current_head_rotations=None, current_wrist_rotations=None):
    current_has_head_guide = current_head_rotations is not None
    if current_has_head_guide:
        if current_head_rotations.shape != (len(current_joint_frames), 3, 3) or not np.isfinite(current_head_rotations).all():
            raise ValueError('머리 회전 가이드 입력 크기·유한값 오류')
        current_guide_axes = np.array([[0., 0., 1.], [0., 1., 0.]])
        current_guide_points = current_joint_frames[:, 15:16] + np.einsum('fij,aj->fai', current_head_rotations, current_guide_axes) * HEAD_GUIDE_LENGTH_METERS
        current_joint_frames = np.concatenate([current_joint_frames, current_guide_points], axis=1)
    if current_wrist_rotations is not None:
        if not current_has_head_guide or current_wrist_rotations.shape != (len(current_joint_frames), 2, 3, 3) or not np.isfinite(current_wrist_rotations).all():
            raise ValueError('손목 가이드는 머리 가이드와 유한한 [프레임,2,3,3] 회전이 필요합니다.')
        current_wrist_points = current_joint_frames[:, 20:22, None, :] + np.einsum('fsij,aj->fsai', current_wrist_rotations, np.eye(3)) * WRIST_GUIDE_LENGTH_METERS
        current_joint_frames = np.concatenate([current_joint_frames, current_wrist_points.reshape(len(current_joint_frames), 6, 3)], axis=1)
    current_sample_indices = np.arange(0, len(current_joint_frames), 30 / current_config_record['preview_fps']).astype(int)
    current_preview_size = current_config_record['preview_size']
    current_elevation_angle = math.radians(current_config_record['camera_elevation'])
    for current_direction_name in current_request_record['directions']:
        current_camera_angle = math.radians(current_config_record['camera_angles'][current_direction_name])
        current_depth_values = current_joint_frames[..., 0] * math.sin(current_camera_angle) + current_joint_frames[..., 2] * math.cos(current_camera_angle)
        current_horizontal_values = current_joint_frames[..., 0] * math.cos(current_camera_angle) - current_joint_frames[..., 2] * math.sin(current_camera_angle)
        current_vertical_values = current_joint_frames[..., 1] * math.cos(current_elevation_angle) - current_depth_values * math.sin(current_elevation_angle)
        current_projected_points = np.stack([current_horizontal_values, -current_vertical_values], axis=-1)
        current_lower_bound = current_projected_points.min(axis=(0, 1))
        current_upper_bound = current_projected_points.max(axis=(0, 1))
        current_center_point = (current_lower_bound + current_upper_bound) / 2
        current_scale_value = (current_preview_size - 2 * PREVIEW_MARGIN_PIXELS) / max(float((current_upper_bound - current_lower_bound).max()), .1)
        current_pixel_points = (current_projected_points - current_center_point) * current_scale_value + current_preview_size / 2
        current_direction_path = current_output_path / current_direction_name
        current_direction_path.mkdir(parents=True)
        for current_frame_index, current_source_index in enumerate(current_sample_indices, 1):
            current_frame_image = Image.new('RGB', (current_preview_size, current_preview_size), PREVIEW_BACKGROUND_COLOR)
            current_drawing_context = ImageDraw.Draw(current_frame_image)
            for current_joint_index, current_parent_index in enumerate(SKELETON_PARENT_INDICES):
                if current_parent_index >= 0:
                    current_drawing_context.line([tuple(current_pixel_points[current_source_index, current_parent_index]), tuple(current_pixel_points[current_source_index, current_joint_index])], fill=PREVIEW_BONE_COLOR, width=PREVIEW_LINE_WIDTH)
            current_frame_image.save(current_direction_path / f'frame-{current_frame_index:04d}.png')
            if current_has_head_guide:
                for current_guide_index, current_guide_color in ((22, (220, 50, 50)), (23, (40, 100, 230))):
                    current_drawing_context.line([tuple(current_pixel_points[current_source_index, 15]), tuple(current_pixel_points[current_source_index, current_guide_index])], fill=current_guide_color, width=PREVIEW_LINE_WIDTH)
                current_drawing_context.text((8, 8), 'Head: red=forward / blue=up', fill=PREVIEW_BONE_COLOR)
                if current_wrist_rotations is not None:
                    for current_side_index, current_side_label in enumerate(('L', 'R')):
                        current_wrist_pixel = tuple(current_pixel_points[current_source_index, 20 + current_side_index])
                        for current_axis_index, current_axis_color in enumerate(WRIST_AXIS_COLORS):
                            current_axis_pixel = tuple(current_pixel_points[current_source_index, 24 + 3 * current_side_index + current_axis_index])
                            current_drawing_context.line([current_wrist_pixel, current_axis_pixel], fill=current_axis_color, width=PREVIEW_LINE_WIDTH)
                        current_drawing_context.text(current_wrist_pixel, current_side_label, fill=PREVIEW_BONE_COLOR)
                    current_drawing_context.text((8, 24), 'Wrist L/R: red=X green=Y blue=Z (source axes)', fill=PREVIEW_BONE_COLOR)
                current_frame_image.save(current_direction_path / f'frame-{current_frame_index:04d}-rotation.png')
        current_progress_callback('preview', f'{current_direction_name} 미리보기 {len(current_sample_indices)}프레임 저장')
    return {'frames': len(current_sample_indices), 'source_frames': len(current_joint_frames), 'source_fps': 30, 'preview_fps': current_config_record['preview_fps'], 'source_indices': (current_sample_indices + 1).tolist(), 'directions': current_request_record['directions'], 'wrist_rotation_guide': current_wrist_rotations is not None}
