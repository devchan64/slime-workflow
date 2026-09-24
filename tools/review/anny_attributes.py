from pathlib import Path
from urllib.parse import urlsplit
import json, subprocess, threading, uuid, re, math
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'assets/motion-sheet/mannequin-walk-v6/inputs/attributes.json'
JOBS=ROOT/'.tmp/anny-attribute-renderer'
PAGE=Path(__file__).with_name('anny-attributes.html').read_text()
THIGH_ROTATION_FIELDS={f'thigh_{side_label_value}_{axis_label_value}':(bone_label_value,axis_index_value) for side_label_value,bone_label_value in [('left','upperleg01.L'),('right','upperleg01.R')] for axis_index_value,axis_label_value in enumerate(('x','y','z'))}
def apply_thigh_rotation(attribute_pose_values,changed_attribute_values):
 # 공식 데모와 같은 회전 벡터(도)를 현재 본의 로컬 회전에 합성한다.
 for target_bone_label in ('upperleg01.L','upperleg01.R'):
  rotation_vector_values=[0.0,0.0,0.0]
  for attribute_field_name,(mapped_bone_label,rotation_axis_index) in THIGH_ROTATION_FIELDS.items():
   if mapped_bone_label==target_bone_label:rotation_vector_values[rotation_axis_index]=math.radians(changed_attribute_values.get(attribute_field_name,0))
  rotation_angle_value=math.sqrt(sum(component_axis_value**2 for component_axis_value in rotation_vector_values))
  if rotation_angle_value==0:continue
  rotation_axis_values=[component_axis_value/rotation_angle_value for component_axis_value in rotation_vector_values]
  axis_cross_matrix=[[0,-rotation_axis_values[2],rotation_axis_values[1]],[rotation_axis_values[2],0,-rotation_axis_values[0]],[-rotation_axis_values[1],rotation_axis_values[0],0]]
  rotation_delta_matrix=[[math.cos(rotation_angle_value)*(row_axis_index==column_axis_index)+(1-math.cos(rotation_angle_value))*rotation_axis_values[row_axis_index]*rotation_axis_values[column_axis_index]+math.sin(rotation_angle_value)*axis_cross_matrix[row_axis_index][column_axis_index] for column_axis_index in range(3)] for row_axis_index in range(3)]
  original_pose_matrix=attribute_pose_values['pose_parameters'][target_bone_label]
  updated_pose_matrix=[matrix_row_values[:] for matrix_row_values in original_pose_matrix]
  for row_axis_index in range(3):
   for column_axis_index in range(3):updated_pose_matrix[row_axis_index][column_axis_index]=sum(original_pose_matrix[row_axis_index][inner_axis_index]*rotation_delta_matrix[inner_axis_index][column_axis_index] for inner_axis_index in range(3))
  attribute_pose_values['pose_parameters'][target_bone_label]=updated_pose_matrix
class AnnyAttributeManager:
 def send(self,h,status,payload,ctype='application/json; charset=utf-8'):
  data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode();h.send_response(status);h.send_header('Content-Type',ctype);h.send_header('Content-Length',str(len(data)));h.end_headers();h.wfile.write(data)
 def handle(self,h):
  path=urlsplit(h.path).path
  if not path.startswith('/anny-attributes'): return False
  try:
   if h.command=='GET' and path=='/anny-attributes/':self.send(h,200,PAGE.encode(),'text/html; charset=utf-8');return True
   if h.command=='GET' and path=='/anny-attributes/mesh-viewer.js':self.send(h,200,Path(__file__).with_name('anny-mesh-viewer.js').read_bytes(),'text/javascript');return True
   if h.command=='GET' and path=='/anny-attributes/history-ui.js':self.send(h,200,Path(__file__).with_name('generation-history.js').read_bytes(),'text/javascript');return True
   if h.command=='GET' and path=='/anny-attributes/history':
    stored_history_records=[]
    for history_record_path in sorted(JOBS.glob('*/history.json'),key=lambda item:item.stat().st_mtime,reverse=True):
     current_history_record=json.loads(history_record_path.read_text());current_history_record['status']=json.loads((history_record_path.parent/'status.json').read_text());
     if current_history_record.get('request',{}).get('kind')=='preview' and (history_record_path.parent/'render'/'mesh.json').is_file():current_history_record['status']={'status':'completed'}
     current_history_record['preview_ready']=all((history_record_path.parent/name).is_file() or (history_record_path.parent/'render'/name).is_file() for name in ('front.png','side.png'));stored_history_records.append(current_history_record)
    self.send(h,200,{'records':stored_history_records});return True
   if h.command=='POST' and path=='/anny-attributes/history/reset':
    if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
    if json.loads(h.rfile.read(int(h.headers['Content-Length'])))!={'action':'reset'}:raise ValueError('초기화 요청 오류')
    for history_record_path in JOBS.glob('*/history.json'):history_record_path.unlink()
    self.send(h,200,{'status':'cleared'});return True
   if h.command=='GET' and path=='/anny-attributes/base':self.send(h,200,json.loads(BASE.read_text()));return True
   if h.command=='GET' and path.startswith('/anny-attributes/jobs/'):
    parts=path.split('/')
    if len(parts) not in (4,5) or not re.fullmatch(r'[0-9a-f]{8}',parts[3]):raise ValueError('잘못된 작업 경로')
    if len(parts)==5 and parts[4] not in {'front.png','side.png','mesh.json'}:raise ValueError('허용하지 않는 결과 파일')
    root=JOBS/parts[3]
    if len(parts)==4:
     state=json.loads((root/'status.json').read_text());state['preview_ready']=all((root/name).is_file() or (root/'render'/name).is_file() for name in ('front.png','side.png'));state['mesh_ready']=(root/'render'/'mesh.json').is_file();
     if state['mesh_ready'] and (root/'history.json').is_file() and json.loads((root/'history.json').read_text()).get('request',{}).get('kind')=='preview':state['status']='completed'
     state['log']=(root/'worker.log').read_text(errors='replace')[-2000:] if (root/'worker.log').exists() else '';self.send(h,200,state);return True
    preview_image_path=root/parts[4]
    if not preview_image_path.is_file():preview_image_path=root/'render'/parts[4]
    self.send(h,200,preview_image_path.read_bytes(),'application/json' if parts[4]=='mesh.json' else 'image/png');return True
   if h.command!='POST' or path not in {'/anny-attributes/render','/anny-attributes/preview'}:raise ValueError('요청 오류')
   if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
   changed=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
   if not isinstance(changed,dict):raise ValueError('속성 객체가 필요합니다.')
   if set(changed)-set(THIGH_ROTATION_FIELDS)-{'age','weight','height','torso-scale-horiz-incr','torso-scale-depth-incr','measure-shoulder-dist-incr','upperlegs-height-incr','lowerlegs-height-incr','rotation_y'}:raise ValueError('지원하지 않는 속성')
   if not isinstance(changed,dict):raise ValueError('속성 객체가 필요합니다.')
   for attribute_key_name,attribute_numeric_value in changed.items():
    attribute_minimum_value=-180 if (attribute_key_name=='rotation_y' or attribute_key_name in THIGH_ROTATION_FIELDS) else 0 if attribute_key_name in {'age','weight','height'} else -1
    if type(attribute_numeric_value) not in (int,float) or not attribute_minimum_value<=attribute_numeric_value<=(180 if (attribute_key_name=='rotation_y' or attribute_key_name in THIGH_ROTATION_FIELDS) else 1):raise ValueError('속성 범위 오류')
   attrs=json.loads(BASE.read_text());attrs['phenotype_kwargs'].update({k:v for k,v in changed.items() if k in attrs['phenotype_kwargs']});attrs['local_changes_kwargs'].update({k:v for k,v in changed.items() if k not in attrs['phenotype_kwargs'] and k!='rotation_y' and k not in THIGH_ROTATION_FIELDS})
   apply_thigh_rotation(attrs,changed)
   ident=uuid.uuid4().hex[:8];root=JOBS/ident;root.mkdir(parents=True);(root/'attributes.json').write_text(json.dumps(attrs));(root/'status.json').write_text(json.dumps({'status':'running'}))
   (root/'history.json').write_text(json.dumps({'id':ident,'created_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'request':{'attributes':changed,'kind':'preview' if path.endswith('/preview') else 'render'},'status':{'status':'running'}},ensure_ascii=False))
   preview_mesh_only=path=='/anny-attributes/preview'
   def work():
    code=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(root/'attributes.json'),'--output-dir',str(root/'render'),'--rotation-y',str(changed.get('rotation_y',0))]+(['--mesh-only'] if preview_mesh_only else []),stdout=(root/'worker.log').open('w'),stderr=subprocess.STDOUT).returncode
    for name in ('front.png','side.png'):
     source=root/'render'/name
     if source.exists():source.replace(root/name)
    (root/'status.json').write_text(json.dumps({'status':'completed' if code==0 else 'failed','exit_code':code}))
   threading.Thread(target=work,daemon=True).start();self.send(h,202,{'id':ident});return True
  except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
