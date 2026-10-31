"""VideoX-Fun DWPose BODY18 색상·선·관절 규칙에 맞춘 RGB 렌더러."""
import math
import numpy as np
from PIL import Image, ImageDraw

# 기준: VideoX-Fun/comfyui/annotator/dwpose_utils/util.py draw_bodypose.
POSE_RENDER_SOURCE_URL = 'https://github.com/aigc-apps/VideoX-Fun/blob/main/comfyui/annotator/dwpose_utils/util.py'
POSE_RENDER_SCHEMA_VERSION = 'videox-fun-dwpose-body18-v1'
POSE_BODY_LIMB_PAIRS = ((1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17))
POSE_BODY_PALETTE_RGB = ((255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),(255,0,255),(255,0,170),(255,0,85))
POSE_LIMB_COLOR_SCALE = 0.6
POSE_LIMB_HALF_WIDTH = 4
POSE_JOINT_PIXEL_RADIUS = 4
POSE_ELLIPSE_ANGLE_DEGREES = np.arange(361)


def render_body_pose_image(current_pose_points,current_image_size=(512,512)):
    """픽셀 좌표와 confidence를 받아 RGB 이미지를 만든다. 누락점은 그리지 않는다."""
    current_point_array = np.asarray(current_pose_points,dtype=float)
    if current_point_array.shape != (18,3) or not np.isfinite(current_point_array).all() or np.any((current_point_array[:,2]<0)|(current_point_array[:,2]>1)):
        raise ValueError('BODY18 좌표·confidence 계약 오류')
    current_canvas_array = np.zeros((current_image_size[1],current_image_size[0],3),dtype=np.uint8)
    current_canvas_image = Image.fromarray(current_canvas_array)
    current_drawing_context = ImageDraw.Draw(current_canvas_image)
    for current_limb_pair,current_limb_color in zip(POSE_BODY_LIMB_PAIRS,POSE_BODY_PALETTE_RGB):
        current_start_point,current_end_point = current_point_array[list(current_limb_pair)]
        if min(current_start_point[2],current_end_point[2]) <= 0:
            continue
        current_middle_point = (current_start_point[:2]+current_end_point[:2])/2
        current_delta_vector = current_start_point[:2]-current_end_point[:2]
        current_limb_length = float(np.linalg.norm(current_delta_vector))
        current_limb_angle = math.degrees(math.atan2(current_delta_vector[1],current_delta_vector[0]))
        current_rotation_angle = math.radians(int(current_limb_angle))
        current_ellipse_angles = np.deg2rad(POSE_ELLIPSE_ANGLE_DEGREES)
        current_local_horizontal = int(current_limb_length/2)*np.cos(current_ellipse_angles)
        current_local_vertical = POSE_LIMB_HALF_WIDTH*np.sin(current_ellipse_angles)
        current_middle_point = current_middle_point.astype(int)
        current_limb_polygon = np.rint(np.column_stack((current_middle_point[0]+current_local_horizontal*np.cos(current_rotation_angle)-current_local_vertical*np.sin(current_rotation_angle),current_middle_point[1]+current_local_horizontal*np.sin(current_rotation_angle)+current_local_vertical*np.cos(current_rotation_angle)))).astype(int)
        current_drawing_context.polygon([tuple(current_polygon_point) for current_polygon_point in current_limb_polygon],fill=tuple(int(current_color_value*POSE_LIMB_COLOR_SCALE) for current_color_value in current_limb_color))
    # 점 색은 연결 순서와 독립적인 관절 인덱스로 마지막에 그린다.
    for current_joint_point,current_joint_color in zip(current_point_array,POSE_BODY_PALETTE_RGB):
        if current_joint_point[2]>0:
            current_joint_horizontal,current_joint_vertical = current_joint_point[:2].astype(int)
            current_drawing_context.ellipse((current_joint_horizontal-POSE_JOINT_PIXEL_RADIUS,current_joint_vertical-POSE_JOINT_PIXEL_RADIUS,current_joint_horizontal+POSE_JOINT_PIXEL_RADIUS,current_joint_vertical+POSE_JOINT_PIXEL_RADIUS),fill=current_joint_color)
    return current_canvas_image
