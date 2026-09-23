from pathlib import Path
from PIL import Image,ImageDraw
import json
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
DIRECTION_NAME_VALUES=['down_left','down_right','up_left','up_right']
current_sheet_image=Image.new('RGB',(2048,1152),'#dedede')
current_sheet_draw=ImageDraw.Draw(current_sheet_image)
current_animation_frames=[]
for current_direction_index,current_direction_name in enumerate(DIRECTION_NAME_VALUES):
 for current_frame_number in range(1,9):
  current_frame_image=Image.open(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'preview-{current_frame_number:04d}.png').convert('RGBA')
  assert current_frame_image.size==(512,512)
  current_frame_image=current_frame_image.resize((256,256))
  current_sheet_image.paste(current_frame_image,((current_frame_number-1)*256,current_direction_index*288+24),current_frame_image)
  current_sheet_draw.text(((current_frame_number-1)*256+8,current_direction_index*288+6),f'{current_direction_name} / {current_frame_number} / 45 deg',fill='black')
current_sheet_image.save(EXPERIMENT_OUTPUT_ROOT/'camera45-32-frame-sheet.jpg',quality=95)
for current_frame_number in range(1,9):
 current_animation_image=Image.new('RGB',(1536,408),'#dedede')
 current_animation_draw=ImageDraw.Draw(current_animation_image)
 for current_direction_index,current_direction_name in enumerate(DIRECTION_NAME_VALUES):
  current_frame_image=Image.open(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'preview-{current_frame_number:04d}.png').convert('RGBA').resize((384,384))
  current_animation_image.paste(current_frame_image,(current_direction_index*384,24),current_frame_image)
  current_animation_draw.text((current_direction_index*384+8,6),current_direction_name,fill='black')
 current_animation_frames.append(current_animation_image)
current_animation_frames[0].save(EXPERIMENT_OUTPUT_ROOT/'camera45-four-view.gif',save_all=True,append_images=current_animation_frames[1:],duration=150,loop=0)
assert json.loads((EXPERIMENT_OUTPUT_ROOT/'loop-validation.json').read_text())['status']=='passed'
(EXPERIMENT_OUTPUT_ROOT/'README.md').write_text('# v5 리그 수평 45도 32프레임 검수\n\n기존 v5 모션·리그·쉐이딩 유지. 카메라 XY를 각각 ±sqrt(26)으로 바꾸어 수평각을 33.6901°에서 45°로 변경했다. 수평 거리 sqrt(52), 카메라 높이 3m, 주시점 높이 0.8m, 하향각 16.9662°, 정사영 배율 2를 유지했다.\n\n4방향 × 8프레임 PNG 및 관절 투영 OpenPose 맵, 방향별 시트, 전체 검수 시트·GIF 생성. MoMask 신규 추론이나 AnyPose 캐릭터 생성은 하지 않았다. 정식 v5 원본은 유지한다. 32장 512×512 및 루프 끝점 검증 통과.\n')
print('32프레임 시트·GIF·검증 완료')
