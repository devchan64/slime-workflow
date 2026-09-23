from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,time
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
DIRECTION_NAME_VALUES=['down_left','down_right','up_left','up_right']
current_result_records=[]
for current_direction_name in DIRECTION_NAME_VALUES:
 current_sheet_image=Image.new('RGB',(2048,1024),'white')
 current_animation_frames=[]
 for current_frame_number in range(1,9):
  current_frame_path=EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'frame-{current_frame_number:02d}'
  current_result_record=json.loads((current_frame_path/'result.json').read_text())
  if current_result_record['status']!='completed':raise ValueError('미완료 프레임')
  current_result_image=Image.open(current_frame_path/'result.png').convert('RGB')
  if current_result_image.size!=(512,512):raise ValueError('출력 크기 오류')
  current_sheet_image.paste(current_result_image,(((current_frame_number-1)%4)*512,((current_frame_number-1)//4)*512))
  current_animation_frames.append(current_result_image)
  current_result_records.append({'direction':current_direction_name,'frame':current_frame_number,'sha256':hashlib.sha256((current_frame_path/'result.png').read_bytes()).hexdigest()})
 current_sheet_image.save(EXPERIMENT_OUTPUT_ROOT/f'{current_direction_name}-sheet.png')
 current_animation_frames[0].save(EXPERIMENT_OUTPUT_ROOT/f'{current_direction_name}.gif',save_all=True,append_images=current_animation_frames[1:],duration=150,loop=0)
(EXPERIMENT_OUTPUT_ROOT/'validation.json').write_text(json.dumps({'status':'passed','count':len(current_result_records),'frames':current_result_records},indent=2))
(EXPERIMENT_OUTPUT_ROOT/'preview.html').write_text('''<!doctype html><meta charset="utf-8"><title>AnyPose · 마네킹 v6 · 32프레임</title><style>body{font:16px system-ui;background:#20252b;color:white;margin:24px}main{display:grid;grid-template-columns:repeat(4,1fr)}img{width:100%}a{color:lightblue}</style><h1>AnyPose · 마네킹 v6 · 32프레임</h1><p>캐릭터 baseline-v2 + 마네킹 v6 리그 참조 / AnyPose + Lightning 4steps / 512×512 / 150ms 재생</p><button id="play">일시정지</button><select id="mode"><option value="result">결과</option><option value="rig-reference">리그 참조</option><option value="character-reference">캐릭터 참조</option></select><span id="frame"></span><main></main><script>const directions=['down_left','down_right','up_left','up_right'];let frame=1,playing=true;for(const direction of directions)document.querySelector('main').insertAdjacentHTML('beforeend','<section><h2>'+direction+'</h2><img data-direction="'+direction+'"><a href="'+direction+'-sheet.png">8프레임 시트</a></section>');function update(){for(const img of document.querySelectorAll('img'))img.src=img.dataset.direction+'/frame-'+String(frame).padStart(2,'0')+'/'+document.querySelector('#mode').value+'.png';document.querySelector('#frame').textContent=frame+'/8'}document.querySelector('#play').onclick=()=>{playing=!playing};document.querySelector('#mode').onchange=update;setInterval(()=>{if(playing){frame=frame%8+1;update()}},150);update()</script>''')
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/review/complete frames={len(current_result_records)}')
