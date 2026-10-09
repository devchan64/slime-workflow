"""제약 적용된 ANNY 관절 투영을 COCO18 PNG·JSON으로 저장한다. 이미지 검출이 아니다."""
import json
import math
from PIL import Image, ImageDraw

OPENPOSE_BODY_CONNECTIONS = ((1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13))
OPENPOSE_BODY_COLORS = ((255, 0, 85), (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255))
OPENPOSE_STROKE_WIDTH = 4
OPENPOSE_HEAD_COLOR = (255, 0, 255)


def write_projected_openpose(current_image_record, current_output_path, current_image_resolution):
    current_flat_keypoints = current_image_record['pose_keypoints_2d']
    if len(current_flat_keypoints) != 54 or any(type(current_axis_value) not in (int, float) or not math.isfinite(current_axis_value) for current_axis_value in current_flat_keypoints):
        raise ValueError('COCO18 투영 관절은 유한한 54개 숫자여야 합니다.')
    current_joint_points = [current_flat_keypoints[current_joint_index:current_joint_index + 3] for current_joint_index in range(0, 54, 3)]
    current_head_points = current_image_record.get('head_bone_keypoints_2d', [])
    if current_head_points and (len(current_head_points) != 2 or any(len(current_head_point) != 3 for current_head_point in current_head_points)):
        raise ValueError('머리 본 가이드는 시작·끝 투영점 2개여야 합니다.')
    for current_point_x, current_point_y, current_point_present in [*current_joint_points, *current_head_points]:
        if any(type(current_axis_value) not in (int, float) or not math.isfinite(current_axis_value) for current_axis_value in (current_point_x, current_point_y, current_point_present)):
            raise ValueError('투영 관절은 유한한 숫자여야 합니다.')
        if current_point_present not in (0, 1) or not 0 <= current_point_x <= current_image_resolution or not 0 <= current_point_y <= current_image_resolution:
            raise ValueError('OpenPose 투영점 범위·존재 표시 오류')
    current_pose_image = Image.new('RGB', (current_image_resolution, current_image_resolution), 'black')
    current_drawing_context = ImageDraw.Draw(current_pose_image)
    for current_start_index, current_end_index in OPENPOSE_BODY_CONNECTIONS:
        if current_joint_points[current_start_index][2] and current_joint_points[current_end_index][2]:
            current_drawing_context.line([tuple(current_joint_points[current_start_index][:2]), tuple(current_joint_points[current_end_index][:2])], fill=OPENPOSE_BODY_COLORS[current_start_index], width=OPENPOSE_STROKE_WIDTH)
    for current_joint_index in range(1, 14):
        current_point_x, current_point_y, current_point_present = current_joint_points[current_joint_index]
        if current_point_present:
            current_drawing_context.ellipse((current_point_x - OPENPOSE_STROKE_WIDTH, current_point_y - OPENPOSE_STROKE_WIDTH, current_point_x + OPENPOSE_STROKE_WIDTH, current_point_y + OPENPOSE_STROKE_WIDTH), fill=OPENPOSE_BODY_COLORS[current_joint_index])
    # COCO18의 코·눈을 추측하지 않고 ANNY 머리 본을 별도 가이드로 표시한다.
    if current_head_points:
        for current_start_point, current_end_point in zip([current_joint_points[1], *current_head_points], current_head_points):
            if current_start_point[2] and current_end_point[2]:
                current_drawing_context.line([tuple(current_start_point[:2]), tuple(current_end_point[:2])], fill=OPENPOSE_HEAD_COLOR, width=OPENPOSE_STROKE_WIDTH)
        for current_head_point in current_head_points:
            if current_head_point[2]:
                current_point_x, current_point_y = current_head_point[:2]
                current_drawing_context.ellipse((current_point_x - OPENPOSE_STROKE_WIDTH, current_point_y - OPENPOSE_STROKE_WIDTH, current_point_x + OPENPOSE_STROKE_WIDTH, current_point_y + OPENPOSE_STROKE_WIDTH), fill=OPENPOSE_HEAD_COLOR)
    current_pose_image.save(current_output_path)
    current_output_path.with_suffix('.json').write_text(json.dumps({
        'version': 1.3, 'people': [{'pose_keypoints_2d': current_flat_keypoints}],
        'source': 'HY-Motion → ANNY 제약 적용 관절 → 렌더 카메라 투영',
        'source_frame': current_image_record['source_frame'], 'projection': current_image_record['projection'],
        'missing_face_indices': [0, 14, 15, 16, 17],
        'head_bone_keypoints_2d': current_head_points,
        'head_guide_note': '자홍색은 ANNY head 본 시작·끝 투영이며 COCO18 얼굴 관절이 아니다. PNG는 머리 본 가이드가 추가된 확장 포즈 맵이다.',
        'confidence_note': '1은 화면 안 투영점 존재이며 검출 확률·가림 판정이 아니다.',
    }, ensure_ascii=False, indent=2))
