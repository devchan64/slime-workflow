"""SOMA 원본과 직접 투영 몸 관절를 같은 프레임으로 비교한다. 추론은 실행하지 않는다."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

COMPARISON_PANEL_SIZE = 384
COMPARISON_LABEL_HEIGHT = 24
COMPARISON_LIMB_PAIRS = ((1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(0,15))
COMPARISON_LIMB_COLORS = ('#ff0000','#ff5500','#ffaa00','#ffff00','#aaff00','#55ff00','#00ff00','#00ff55','#00ffaa','#00ffff','#00aaff','#0055ff','#0000ff','#ff00ff','#aa00ff')


def render_pose_comparison(current_attempt_root, current_image_records):
    current_comparison_image = Image.new('RGB',(COMPARISON_PANEL_SIZE,(COMPARISON_PANEL_SIZE+COMPARISON_LABEL_HEIGHT)*len(current_image_records)),'white')
    for current_direction_index,current_image_record in enumerate(current_image_records):
        current_keypoint_values = current_image_record['pose_keypoints_2d']
        if len(current_keypoint_values)!=54 or any(type(current_number_value) not in (int,float) or not math.isfinite(current_number_value) for current_number_value in current_keypoint_values):
            raise ValueError('OpenPose COCO18 투영 좌표 계약 오류')
        current_pose_points = [current_keypoint_values[current_point_offset:current_point_offset+3] for current_point_offset in range(0,54,3)]
        current_pose_image = Image.new('RGB',(512,512),'black')
        current_pose_drawing = ImageDraw.Draw(current_pose_image)
        for current_limb_pair,current_limb_color in zip(COMPARISON_LIMB_PAIRS,COMPARISON_LIMB_COLORS):
            current_start_point,current_end_point = [current_pose_points[current_joint_index] for current_joint_index in current_limb_pair]
            if current_start_point[2]>0 and current_end_point[2]>0:
                current_pose_drawing.line([tuple(current_start_point[:2]),tuple(current_end_point[:2])],fill=current_limb_color,width=5)
                for current_joint_point in (current_start_point,current_end_point):
                    current_pose_drawing.ellipse((current_joint_point[0]-4,current_joint_point[1]-4,current_joint_point[0]+4,current_joint_point[1]+4),fill=current_limb_color)
        current_row_offset = current_direction_index*(COMPARISON_PANEL_SIZE+COMPARISON_LABEL_HEIGHT)
        for current_panel_index,current_panel_image in enumerate((current_pose_image,)):
            current_comparison_image.paste(current_panel_image.resize((COMPARISON_PANEL_SIZE,COMPARISON_PANEL_SIZE)),(current_panel_index*COMPARISON_PANEL_SIZE,current_row_offset+COMPARISON_LABEL_HEIGHT))
        current_label_drawing = ImageDraw.Draw(current_comparison_image)
        current_label_drawing.text((4,current_row_offset+6),'OPENPOSE (SOMA body)',fill='black')
        current_label_drawing.text((190,current_row_offset+6),current_image_record['direction'],fill='black')
    return current_comparison_image


def export_pose_comparison(current_attempt_root,current_direction_names):
    import imageio.v2 as imageio
    import numpy as np
    current_attempt_root = Path(current_attempt_root)
    from generators.kimodo.soma_pose import load_soma_pose_points, SOMA_POSE_SCHEMA_VERSION
    current_soma_points = load_soma_pose_points(current_attempt_root,current_direction_names)
    current_frame_count = len(next(iter(current_soma_points.values())))
    current_pose_record = {'schema_version':SOMA_POSE_SCHEMA_VERSION,'fps':30,'width':512,'height':512,'projection':'orthographic-horizontal','source':('motion-in-place.npz' if (current_attempt_root/'motion-in-place.npz').is_file() else 'motion.npz')+':posed_joints','missing_points':[16,17],'head_mapping':{'0':'Head (head-center proxy, not anatomical nose)','14':'RightEye','15':'LeftEye'},'directions':{current_direction_name:current_pose_values.tolist() for current_direction_name,current_pose_values in current_soma_points.items()}}
    current_temporary_path = current_attempt_root/'comparison.tmp.mp4'
    try:
        with imageio.get_reader(str(current_attempt_root/'joint-preview.mp4')) as current_soma_reader, imageio.get_writer(str(current_temporary_path),fps=30,codec='libx264',quality=8,macro_block_size=1) as current_video_writer:
            if current_soma_reader.count_frames()!=current_frame_count or abs(current_soma_reader.get_meta_data()['fps']-30)>0.01:
                raise ValueError('SOMA 원본과 포즈 프레임 수·FPS 불일치')
            for current_frame_index in range(current_frame_count):
                current_comparison_image = render_pose_comparison(current_attempt_root,[{'direction':current_direction_name,'source_frame':current_frame_index+1,'pose_keypoints_2d':current_soma_points[current_direction_name][current_frame_index].reshape(-1).tolist()} for current_direction_name in current_direction_names])
                current_soma_image = Image.fromarray(current_soma_reader.get_data(current_frame_index))
                current_output_image = Image.new('RGB',(COMPARISON_PANEL_SIZE*3,current_comparison_image.height),'white')
                current_output_image.paste(current_comparison_image,(COMPARISON_PANEL_SIZE*2,0))
                current_soma_panel = ImageOps.contain(current_soma_image,(COMPARISON_PANEL_SIZE*2,COMPARISON_PANEL_SIZE))
                current_output_image.paste(current_soma_panel,((COMPARISON_PANEL_SIZE*2-current_soma_panel.width)//2,COMPARISON_LABEL_HEIGHT))
                ImageDraw.Draw(current_output_image).text((4,6),'SOMA | FRONT + SIDE | synchronized frame',fill='black')
                current_video_writer.append_data(np.asarray(current_output_image))
        current_temporary_path.replace(current_attempt_root/'comparison.mp4')
        (current_attempt_root/'soma-pose.json').write_text(json.dumps(current_pose_record))
    finally:
        current_temporary_path.unlink(missing_ok=True)
    return current_attempt_root/'comparison.mp4'
