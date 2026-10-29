"""ANNY 투영 관절과 리그를 같은 프레임·카메라로 비교한다. 추론은 실행하지 않는다."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

COMPARISON_PANEL_SIZE = 384
COMPARISON_LABEL_HEIGHT = 24
COMPARISON_LIMB_PAIRS = ((1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13))
COMPARISON_LIMB_COLORS = ('#ff0000','#ff5500','#ffaa00','#ffff00','#aaff00','#55ff00','#00ff00','#00ff55','#00ffaa','#00ffff','#0055ff','#aa00ff')


def render_pose_comparison(current_attempt_root, current_image_records):
    current_comparison_image = Image.new('RGB',(COMPARISON_PANEL_SIZE*2,(COMPARISON_PANEL_SIZE+COMPARISON_LABEL_HEIGHT)*len(current_image_records)),'white')
    for current_direction_index,current_image_record in enumerate(current_image_records):
        current_keypoint_values = current_image_record['pose_keypoints_2d']
        if len(current_keypoint_values)!=54 or any(type(current_number_value) not in (int,float) or not math.isfinite(current_number_value) for current_number_value in current_keypoint_values):
            raise ValueError('OpenPose COCO18 투영 좌표 계약 오류')
        current_image_path = current_attempt_root/'anny'/current_image_record['path']
        if not current_image_path.resolve().is_relative_to((current_attempt_root/'anny').resolve()):
            raise ValueError('ANNY 비교 이미지 경로 이탈')
        current_pose_points = [current_keypoint_values[current_point_offset:current_point_offset+3] for current_point_offset in range(0,54,3)]
        current_pose_image = Image.new('RGB',(512,512),'black')
        current_pose_drawing = ImageDraw.Draw(current_pose_image)
        for current_limb_pair,current_limb_color in zip(COMPARISON_LIMB_PAIRS,COMPARISON_LIMB_COLORS):
            current_start_point,current_end_point = [current_pose_points[current_joint_index] for current_joint_index in current_limb_pair]
            if current_start_point[2]>0 and current_end_point[2]>0:
                current_pose_drawing.line([tuple(current_start_point[:2]),tuple(current_end_point[:2])],fill=current_limb_color,width=5)
                for current_joint_point in (current_start_point,current_end_point):
                    current_pose_drawing.ellipse((current_joint_point[0]-4,current_joint_point[1]-4,current_joint_point[0]+4,current_joint_point[1]+4),fill=current_limb_color)
        with Image.open(current_image_path) as current_rig_image:
            if current_rig_image.mode!='RGBA' or current_rig_image.size!=(512,512):
                raise ValueError('ANNY 비교 이미지 형식 오류')
            current_body_image = Image.alpha_composite(Image.new('RGBA',(512,512),'white'),current_rig_image).convert('RGB')
        current_row_offset = current_direction_index*(COMPARISON_PANEL_SIZE+COMPARISON_LABEL_HEIGHT)
        for current_panel_index,current_panel_image in enumerate((current_pose_image,current_body_image)):
            current_comparison_image.paste(current_panel_image.resize((COMPARISON_PANEL_SIZE,COMPARISON_PANEL_SIZE)),(current_panel_index*COMPARISON_PANEL_SIZE,current_row_offset+COMPARISON_LABEL_HEIGHT))
        current_label_drawing = ImageDraw.Draw(current_comparison_image)
        current_label_drawing.text((4,current_row_offset+6),'OPENPOSE (ANNY projection)',fill='black')
        current_label_drawing.text((COMPARISON_PANEL_SIZE+4,current_row_offset+6),f'ANNY | {current_image_record["direction"]} | frame {current_image_record["source_frame"]}',fill='black')
    return current_comparison_image


def export_pose_comparison(current_attempt_root):
    import imageio.v2 as imageio
    import numpy as np
    current_attempt_root = Path(current_attempt_root)
    current_manifest_record = json.loads((current_attempt_root/'anny/render-manifest.json').read_text())
    current_image_records = current_manifest_record['images']
    if not current_image_records:
        raise ValueError('ANNY 비교 프레임이 없습니다.')
    current_direction_names = list(dict.fromkeys(current_image_record['direction'] for current_image_record in current_image_records))
    current_direction_frames = [[current_image_record for current_image_record in current_image_records if current_image_record['direction']==current_direction_name] for current_direction_name in current_direction_names]
    current_frame_count = len(current_direction_frames[0])
    for current_frame_records in current_direction_frames:
        if [current_image_record['source_frame'] for current_image_record in current_frame_records]!=list(range(1,current_frame_count+1)):
            raise ValueError('방향별 비교 프레임 수·순서 불일치')
    current_temporary_path = current_attempt_root/'comparison.tmp.mp4'
    try:
        with imageio.get_writer(str(current_temporary_path),fps=30,codec='libx264',quality=8,macro_block_size=1) as current_video_writer:
            for current_frame_index in range(current_frame_count):
                current_comparison_image = render_pose_comparison(current_attempt_root,[current_frame_records[current_frame_index] for current_frame_records in current_direction_frames])
                current_video_writer.append_data(np.asarray(current_comparison_image))
        current_temporary_path.replace(current_attempt_root/'comparison.mp4')
    finally:
        current_temporary_path.unlink(missing_ok=True)
    return current_attempt_root/'comparison.mp4'
