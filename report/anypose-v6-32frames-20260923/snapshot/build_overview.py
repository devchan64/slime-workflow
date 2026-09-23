from pathlib import Path
from PIL import Image,ImageDraw
import time
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
DIRECTION_NAME_VALUES=['down_left','down_right','up_left','up_right']
current_overview_image=Image.new('RGB',(2048,1152),'white')
current_drawing_context=ImageDraw.Draw(current_overview_image)
current_animation_frames=[]
for current_direction_index,current_direction_name in enumerate(DIRECTION_NAME_VALUES):
 for current_frame_index in range(8):
  current_source_image=Image.open(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'frame-{current_frame_index+1:02d}'/'result.png').convert('RGB')
  current_overview_image.paste(current_source_image.resize((256,256)),(current_frame_index*256,current_direction_index*288+24))
  current_drawing_context.text((current_frame_index*256+8,current_direction_index*288+6),f'{current_direction_name} / {current_frame_index+1}',fill='black')
current_overview_image.save(EXPERIMENT_OUTPUT_ROOT/'anypose-v6-32-frame-sheet.jpg',quality=95)
for current_frame_index in range(8):
 current_animation_image=Image.new('RGB',(1536,408),'white')
 current_animation_draw=ImageDraw.Draw(current_animation_image)
 for current_direction_index,current_direction_name in enumerate(DIRECTION_NAME_VALUES):
  current_source_image=Image.open(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'frame-{current_frame_index+1:02d}'/'result.png').convert('RGB')
  current_animation_image.paste(current_source_image.resize((384,384)),(current_direction_index*384,24))
  current_animation_draw.text((current_direction_index*384+8,6),current_direction_name,fill='black')
 current_animation_frames.append(current_animation_image)
current_animation_frames[0].save(EXPERIMENT_OUTPUT_ROOT/'anypose-v6-four-view.gif',save_all=True,append_images=current_animation_frames[1:],duration=150,loop=0)
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/overview/complete')
