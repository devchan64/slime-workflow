from pathlib import Path
from PIL import Image,ImageDraw
import json,time
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
POSE_EDGE_INDICES=[(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0)]
POSE_EDGE_COLORS=['#ff5500','#ffaa00','#ffff00','#aaff00','#55ff00','#00ff00','#00ff55','#00ffaa','#00ffff','#00aaff','#0055ff','#0000ff','#ff0000']
current_keypoint_record=json.loads((EXPERIMENT_OUTPUT_ROOT/'openpose-keypoints.json').read_text())
for current_sheet_name in ['pose-sheets','rig-sheets']:(EXPERIMENT_OUTPUT_ROOT/current_sheet_name).mkdir(exist_ok=True)
for current_direction_name,current_frame_points in current_keypoint_record['frames'].items():
 current_pose_sheet=Image.new('RGB',(2048,1024),'black')
 current_rig_sheet=Image.new('RGB',(2048,1024),'white')
 for current_frame_index,current_joint_points in enumerate(current_frame_points):
  current_pose_image=Image.new('RGB',(512,512),'black')
  current_drawing_context=ImageDraw.Draw(current_pose_image)
  for current_edge_pair,current_edge_color in zip(POSE_EDGE_INDICES,POSE_EDGE_COLORS):
   current_drawing_context.line([tuple(current_joint_points[current_joint_index]) for current_joint_index in current_edge_pair],fill=current_edge_color,width=5)
  for current_joint_point,current_joint_color in zip(current_joint_points,POSE_EDGE_COLORS+[POSE_EDGE_COLORS[0]]):
   current_pixel_x,current_pixel_y=current_joint_point
   current_drawing_context.ellipse((current_pixel_x-4,current_pixel_y-4,current_pixel_x+4,current_pixel_y+4),fill=current_joint_color)
  current_pose_image.save(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'openpose-{current_frame_index+1:04d}.png')
  current_rig_image=Image.open(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'preview-{current_frame_index+1:04d}.png').convert('RGBA')
  current_tile_position=((current_frame_index%4)*512,(current_frame_index//4)*512)
  current_pose_sheet.paste(current_pose_image,current_tile_position)
  current_rig_sheet.paste(current_rig_image,current_tile_position,current_rig_image)
 current_pose_sheet.save(EXPERIMENT_OUTPUT_ROOT/'pose-sheets'/f'{current_direction_name}.png')
 current_rig_sheet.save(EXPERIMENT_OUTPUT_ROOT/'rig-sheets'/f'{current_direction_name}.png')
(EXPERIMENT_OUTPUT_ROOT/'preview.html').write_text('''<!doctype html><meta charset="utf-8"><title>ANNY v4 32프레임</title><style>body{background:#222;color:white;font:16px system-ui}main{display:grid;grid-template-columns:repeat(4,1fr)}img{width:100%}</style><h1>mannequin-walk/v4 · 4방향 × 8프레임</h1><p>MoMask 파생 루프 → 새 ANNY104 리그 → 동일 카메라 관절 투영. OpenPose 검출 결과가 아닌 투영 맵입니다.</p><select id="mode"><option value="preview">리그</option><option value="openpose">OpenPose</option></select><button id="play">일시정지</button><main></main><script>const directions=['down_left','down_right','up_left','up_right'];let frame=0,playing=true;for(const direction of directions)document.querySelector('main').insertAdjacentHTML('beforeend','<section><h2>'+direction+'</h2><img data-direction="'+direction+'"></section>');function update(){for(const img of document.querySelectorAll('img'))img.src=img.dataset.direction+'/'+document.querySelector('#mode').value+'-'+String(frame+1).padStart(4,'0')+'.png'}document.querySelector('#mode').onchange=update;document.querySelector('#play').onclick=()=>{playing=!playing};setInterval(()=>{if(playing){frame=(frame+1)%8;update()}},150);update()</script>''')
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/asset-package/complete')
