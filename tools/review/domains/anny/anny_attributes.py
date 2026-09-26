import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from tools.review.ui_assets import resolve_review_ui_asset
from urllib.parse import urlsplit
import json, subprocess, threading, uuid, re, math, yaml
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[4]
BASELINE_SELECTION_PATH=ROOT/'generators/animation/config/anny_model_baseline.yaml'
JOBS=ROOT/'.tmp/anny-attribute-renderer'
PAGE=resolve_review_ui_asset('anny-attributes.html').read_text()
BONE_ROTATION_FIELDS={'upperleg_left_rotation_z':('upperleg01.L',2),'upperleg_right_rotation_z':('upperleg01.R',2)}
BONE_ROTATION_FIELDS.update({f'{part_label_value}_{side_label_value}_rotation_{axis_label_value}':(f'{part_label_value}01.{side_suffix_value}',axis_index_value) for part_label_value in ('upperarm','lowerarm') for side_label_value,side_suffix_value in [('left','L'),('right','R')] for axis_index_value,axis_label_value in enumerate(('x','y','z'))})
PROFILE_DIRECTORY_PATH=ROOT/'generators/animation/config/anny_profiles'
PROFILE_REQUIRED_FIELDS={'schema_version','profile_id','label','source_asset_id','asset_path','manifest_path','attributes_path','attributes_sha256','blend_path','glb_path','rig_path','status','attribute_overrides'}
def load_profile_record(profile_path):
 profile_path=Path(profile_path).resolve()
 if not profile_path.is_relative_to(PROFILE_DIRECTORY_PATH.resolve()) or not profile_path.is_file():raise ValueError('ANNY 프로필 경로 오류')
 profile_record=yaml.safe_load(profile_path.read_text())
 if not isinstance(profile_record,dict) or set(profile_record)!=PROFILE_REQUIRED_FIELDS or profile_record['schema_version']!=1 or not all(isinstance(profile_record[field_name],str) and profile_record[field_name] for field_name in PROFILE_REQUIRED_FIELDS-{'schema_version','attribute_overrides'}):raise ValueError('ANNY 프로필 형식 오류')
 if not isinstance(profile_record['attribute_overrides'],dict) or any(not isinstance(attribute_name,str) or type(attribute_value) not in (int,float) or not -1<=attribute_value<=1 for attribute_name,attribute_value in profile_record['attribute_overrides'].items()):raise ValueError('ANNY 프로필 속성 형식 오류')
 return profile_record
def load_active_profile():
 baseline_selection_record=yaml.safe_load(BASELINE_SELECTION_PATH.read_text())
 if not isinstance(baseline_selection_record,dict) or set(baseline_selection_record)!={'schema_version','active_profile_path'} or baseline_selection_record['schema_version']!=1:raise ValueError('ANNY 기본 프로필 선택 형식 오류')
 return load_profile_record(ROOT/baseline_selection_record['active_profile_path'])
def load_profile_by_identifier(profile_identifier):
 if not isinstance(profile_identifier,str) or not re.fullmatch(r'[a-z]+(?:_[a-z0-9]+)*_v[0-9]+',profile_identifier):raise ValueError('ANNY 프로필 식별자 오류')
 for profile_file_path in PROFILE_DIRECTORY_PATH.glob('*.yaml'):
  profile_record=load_profile_record(profile_file_path)
  if profile_record['profile_id']==profile_identifier:return profile_record
 raise ValueError('등록되지 않은 ANNY 프로필')
def load_attribute_defaults():
 return load_profile_attribute_defaults(load_active_profile())
def load_profile_attribute_defaults(profile_record):
 baseline_attribute_values=json.loads((ROOT/profile_record['attributes_path']).read_text())
 for attribute_name,attribute_value in profile_record['attribute_overrides'].items():
  if attribute_name not in baseline_attribute_values['phenotype_kwargs'] and attribute_name not in baseline_attribute_values['local_changes_kwargs'] and attribute_name not in baseline_attribute_values['facial_actions']:raise ValueError('ANNY 프로필 속성 대상 오류')
  for attribute_group_name in ('phenotype_kwargs','local_changes_kwargs','facial_actions'):
   if attribute_name in baseline_attribute_values[attribute_group_name]:baseline_attribute_values[attribute_group_name][attribute_name]=attribute_value
 baseline_attribute_values['local_changes_kwargs']['hip-waist-up']=0.0
 baseline_attribute_values['local_changes_kwargs']['measure-waist-circ-incr']=-0.5
 baseline_attribute_values['local_changes_kwargs']['torso-muscle-dorsi-incr']=0.0
 return baseline_attribute_values
def extract_bone_rotation(pose_matrix_values):
 rotation_angle_value=math.acos(max(-1,min(1,(sum(pose_matrix_values[axis_index_value][axis_index_value] for axis_index_value in range(3))-1)/2)))
 if rotation_angle_value<1e-8:return [0.0,0.0,0.0]
 rotation_scale_value=math.degrees(rotation_angle_value)/(2*math.sin(rotation_angle_value))
 return [(pose_matrix_values[2][1]-pose_matrix_values[1][2])*rotation_scale_value,(pose_matrix_values[0][2]-pose_matrix_values[2][0])*rotation_scale_value,(pose_matrix_values[1][0]-pose_matrix_values[0][1])*rotation_scale_value]
def apply_bone_rotations(attribute_pose_values,changed_attribute_values):
 # 추가 회전이 아니라 공식 데모의 절대 회전 벡터 값을 수정한다.
 for attribute_field_name,(target_bone_label,rotation_axis_index) in BONE_ROTATION_FIELDS.items():
  if attribute_field_name not in changed_attribute_values:continue
  original_pose_matrix=attribute_pose_values['pose_parameters'][target_bone_label]
  rotation_vector_values=extract_bone_rotation(original_pose_matrix)
  rotation_vector_values[rotation_axis_index]=changed_attribute_values[attribute_field_name]
  rotation_vector_values=[math.radians(component_axis_value) for component_axis_value in rotation_vector_values]
  rotation_angle_value=math.sqrt(sum(component_axis_value**2 for component_axis_value in rotation_vector_values))
  rotation_axis_values=[component_axis_value/rotation_angle_value for component_axis_value in rotation_vector_values] if rotation_angle_value else [0,0,0]
  axis_cross_matrix=[[0,-rotation_axis_values[2],rotation_axis_values[1]],[rotation_axis_values[2],0,-rotation_axis_values[0]],[-rotation_axis_values[1],rotation_axis_values[0],0]]
  for row_axis_index in range(3):
   for column_axis_index in range(3):original_pose_matrix[row_axis_index][column_axis_index]=math.cos(rotation_angle_value)*(row_axis_index==column_axis_index)+(1-math.cos(rotation_angle_value))*rotation_axis_values[row_axis_index]*rotation_axis_values[column_axis_index]+math.sin(rotation_angle_value)*axis_cross_matrix[row_axis_index][column_axis_index]
class AnnyAttributeManager:
 def send(self,h,status,payload,ctype='application/json; charset=utf-8'):
  data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode();h.send_response(status);h.send_header('Content-Type',ctype);h.send_header('Content-Length',str(len(data)));h.end_headers();h.wfile.write(data)
 def handle(self,h):
  path=urlsplit(h.path).path
  if not path.startswith('/anny-attributes'): return False
  try:
   if h.command=='GET' and path=='/anny-attributes/':self.send(h,200,PAGE.encode(),'text/html; charset=utf-8');return True
   if h.command=='GET' and path in ('/anny-attributes/studio.css','/anny-attributes/layout.css'):
    stylesheet_file_name='generation-studio.css' if path.endswith('/studio.css') else 'anny-attributes.css'
    self.send(h,200,resolve_review_ui_asset(stylesheet_file_name).read_bytes(),'text/css; charset=utf-8');return True
   if h.command=='GET' and path=='/anny-attributes/mesh-viewer.js':self.send(h,200,resolve_review_ui_asset('anny-mesh-viewer.js').read_bytes(),'text/javascript');return True
   if h.command=='GET' and path=='/anny-attributes/log-viewer.js':
    from tools.review.common.management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
    self.send(h,200,MANAGEMENT_LOG_VIEWER_SCRIPT.encode(),'text/javascript');return True
   if h.command=='GET' and path=='/anny-attributes/history-ui.js':self.send(h,200,resolve_review_ui_asset('generation-history.js').read_bytes(),'text/javascript');return True
   if h.command=='GET' and path=='/anny-attributes/history':
    stored_history_records=[]
    for history_record_path in sorted(JOBS.glob('*/history.json'),key=lambda item:item.stat().st_mtime,reverse=True):
     current_history_record=json.loads(history_record_path.read_text());current_history_record['path']=str(history_record_path.parent.resolve());current_history_record['status']=json.loads((history_record_path.parent/'status.json').read_text());
     if current_history_record.get('request',{}).get('kind')=='preview' and (history_record_path.parent/'render'/'mesh.json').is_file():current_history_record['status']={'status':'completed'}
     current_history_record['preview_ready']=all((history_record_path.parent/name).is_file() or (history_record_path.parent/'render'/name).is_file() for name in ('front.png','side.png'));stored_history_records.append(current_history_record)
    self.send(h,200,{'records':stored_history_records});return True
   if h.command=='POST' and path=='/anny-attributes/history/reset':
    if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
    if json.loads(h.rfile.read(int(h.headers['Content-Length'])))!={'action':'reset'}:raise ValueError('초기화 요청 오류')
    for history_record_path in JOBS.glob('*/history.json'):history_record_path.unlink()
    self.send(h,200,{'status':'cleared'});return True
   if h.command=='GET' and path=='/anny-attributes/profiles':
    profile_records=[load_profile_record(profile_file_path) for profile_file_path in sorted(PROFILE_DIRECTORY_PATH.glob('*.yaml'))];self.send(h,200,{'profiles':[{'id':profile_record['profile_id'],'label':profile_record['label']} for profile_record in profile_records]});return True
   if h.command=='GET' and (path=='/anny-attributes/base' or path.startswith('/anny-attributes/base/')):
    profile_record=load_active_profile() if path=='/anny-attributes/base' else load_profile_by_identifier(path.removeprefix('/anny-attributes/base/'));baseline_attribute_values=load_profile_attribute_defaults(profile_record);baseline_attribute_values['profile']={field_name:profile_record[field_name] for field_name in ('profile_id','label','source_asset_id')};baseline_attribute_values['bone_rotation_defaults']={attribute_field_name:round(extract_bone_rotation(baseline_attribute_values['pose_parameters'][target_bone_label])[rotation_axis_index],6) for attribute_field_name,(target_bone_label,rotation_axis_index) in BONE_ROTATION_FIELDS.items()};self.send(h,200,baseline_attribute_values);return True
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
   for locked_attribute_name in ('hip-waist-up','torso-muscle-dorsi-incr'):
    if locked_attribute_name in changed and (type(changed[locked_attribute_name]) not in (int,float) or changed[locked_attribute_name]!=0):raise ValueError(f'{locked_attribute_name}은 0으로 잠긴 속성입니다.')
   attrs=load_attribute_defaults()
   allowed_attribute_fields=set(attrs['phenotype_kwargs'])|set(attrs['local_changes_kwargs'])|set(attrs['facial_actions'])|set(BONE_ROTATION_FIELDS)|{'rotation_y'}
   if set(changed)-allowed_attribute_fields:raise ValueError('지원하지 않는 속성')
   for attribute_key_name,attribute_numeric_value in changed.items():
    rotation_attribute_flag=attribute_key_name=='rotation_y' or attribute_key_name in BONE_ROTATION_FIELDS
    attribute_minimum_value=-180 if rotation_attribute_flag else -1 if attribute_key_name in attrs['local_changes_kwargs'] else 0
    attribute_maximum_value=180 if rotation_attribute_flag else 1
    if type(attribute_numeric_value) not in (int,float) or not attribute_minimum_value<=attribute_numeric_value<=attribute_maximum_value:raise ValueError('속성 범위 오류')
   for attribute_group_name in ('phenotype_kwargs','local_changes_kwargs','facial_actions'):
    attrs[attribute_group_name].update({attribute_key_name:attribute_numeric_value for attribute_key_name,attribute_numeric_value in changed.items() if attribute_key_name in attrs[attribute_group_name]})
   apply_bone_rotations(attrs,changed)
   ident=uuid.uuid4().hex[:8];root=JOBS/ident;root.mkdir(parents=True);(root/'attributes.json').write_text(json.dumps(attrs));(root/'status.json').write_text(json.dumps({'status':'running'}))
   (root/'history.json').write_text(json.dumps({'id':ident,'created_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'request':{'attributes':{attribute_field_name:attribute_field_value for attribute_field_name,attribute_field_value in changed.items() if attribute_field_name!='rotation_y'},'render_settings':{'rotation_y':changed.get('rotation_y',0)},'kind':'preview' if path.endswith('/preview') else 'render'},'status':{'status':'running'}},ensure_ascii=False))
   preview_mesh_only=path=='/anny-attributes/preview'
   def work():
    code=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(root/'attributes.json'),'--output-dir',str(root/'render'),'--rotation-y',str(changed.get('rotation_y',0))]+(['--mesh-only'] if preview_mesh_only else []),stdout=(root/'worker.log').open('w'),stderr=subprocess.STDOUT).returncode
    for name in ('front.png','side.png'):
     source=root/'render'/name
     if source.exists():source.replace(root/name)
    (root/'status.json').write_text(json.dumps({'status':'completed' if code==0 else 'failed','exit_code':code}))
   threading.Thread(target=work,daemon=True).start();self.send(h,202,{'id':ident});return True
  except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
