import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from tools.review.common.generation_cleanup import delete_generation_job_files, describe_generation_cleanup, read_cleanup_confirmation
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation, resume_gpu_generation
from tools.review.common.queue_generation_telemetry import read_queue_generation_metrics
from tools.review.ui_assets import resolve_review_ui_asset
from tools.review.common.strict_yaml import UniqueConfigLoader
from generators.animation.anny_attribute_contract import validate_anny_attribute_structure
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
HEAD_SCALE_ATTRIBUTE_NAMES={'head-scale-horiz-incr','head-scale-vert-incr','head-scale-depth-incr'}
PROFILE_REQUIRED_FIELDS={'schema_version','profile_id','label','source_asset_id','asset_path','manifest_path','attributes_path','attributes_sha256','blend_path','glb_path','rig_path','status','attribute_overrides'}
ANNY_ACTIVE_HISTORY_STATES={'running','queued'}
ANNY_HISTORY_SERVICE_LOCK=threading.RLock()

def read_anny_generation_status(current_job_directory):
 current_status_record=json.loads((current_job_directory/'status.json').read_text())
 if current_status_record.get('status')!='queued':
  current_metrics_record=read_queue_generation_metrics(current_job_directory)
  if current_metrics_record:
   current_status_record['metrics']=current_metrics_record
   current_status_record['estimate']=current_metrics_record.get('estimate') or {}
 return current_status_record


def read_anny_history_status(job_directory_path):
 status_file_path=job_directory_path/'status.json'
 if not status_file_path.is_file():raise ValueError('작업 상태 기록이 없습니다.')
 status_record=json.loads(status_file_path.read_text())
 if not isinstance(status_record,dict) or not isinstance(status_record.get('status'),str):raise ValueError('작업 상태 기록 형식 오류')
 return status_record['status']

def delete_anny_history_record(generation_job_identifier):
 if not isinstance(generation_job_identifier,str) or not re.fullmatch(r'[0-9a-f]{8}',generation_job_identifier):raise ValueError('작업 ID 오류')
 with ANNY_HISTORY_SERVICE_LOCK:
  current_cleanup_result=delete_generation_job_files(JOBS,[JOBS/generation_job_identifier])
  return {**current_cleanup_result,'deleted':generation_job_identifier}

def preview_anny_history_cleanup():
 with ANNY_HISTORY_SERVICE_LOCK:
  current_job_targets=[current_job_path for current_job_path in JOBS.iterdir() if re.fullmatch('[a-f0-9]{8}',current_job_path.name)] if JOBS.exists() else []
  return describe_generation_cleanup(JOBS,current_job_targets)

def clear_anny_history_records(current_expected_jobs=None):
 with ANNY_HISTORY_SERVICE_LOCK:
  current_job_targets=[current_job_path for current_job_path in JOBS.iterdir() if re.fullmatch('[a-f0-9]{8}',current_job_path.name)] if JOBS.exists() else []
  return delete_generation_job_files(JOBS,current_job_targets,current_expected_jobs=current_expected_jobs)

def load_profile_record(current_profile_path):
 current_profile_path=Path(current_profile_path).resolve()
 if not current_profile_path.is_relative_to(PROFILE_DIRECTORY_PATH.resolve()) or not current_profile_path.is_file():raise ValueError('ANNY 프로필 경로 오류')
 current_profile_record=yaml.load(current_profile_path.read_text(),Loader=UniqueConfigLoader)
 if not isinstance(current_profile_record,dict) or set(current_profile_record)!=PROFILE_REQUIRED_FIELDS or type(current_profile_record['schema_version']) is not int or current_profile_record['schema_version']!=1 or not all(isinstance(current_profile_record[current_field_name],str) and current_profile_record[current_field_name] for current_field_name in PROFILE_REQUIRED_FIELDS-{'schema_version','attribute_overrides'}):raise ValueError('ANNY 프로필 형식 오류')
 if not isinstance(current_profile_record['attribute_overrides'],dict) or any(not isinstance(current_attribute_name,str) or type(current_attribute_value) not in (int,float) or not -1<=current_attribute_value<=(3 if current_attribute_name in HEAD_SCALE_ATTRIBUTE_NAMES else 1) for current_attribute_name,current_attribute_value in current_profile_record['attribute_overrides'].items()):raise ValueError('ANNY 프로필 속성 형식 오류')
 return current_profile_record
def load_active_profile():
 baseline_selection_record=yaml.load(BASELINE_SELECTION_PATH.read_text(),Loader=UniqueConfigLoader)
 if not isinstance(baseline_selection_record,dict) or set(baseline_selection_record)!={'schema_version','active_profile_path'} or type(baseline_selection_record['schema_version']) is not int or baseline_selection_record['schema_version']!=1 or not isinstance(baseline_selection_record['active_profile_path'],str) or not baseline_selection_record['active_profile_path'].strip():raise ValueError('ANNY 기본 프로필 선택 형식 오류')
 return load_profile_record(ROOT/baseline_selection_record['active_profile_path'])
def load_profile_by_identifier(profile_identifier):
 if not isinstance(profile_identifier,str) or not re.fullmatch(r'[a-z]+(?:_[a-z0-9]+)*_v[0-9]+',profile_identifier):raise ValueError('ANNY 프로필 식별자 오류')
 for profile_file_path in PROFILE_DIRECTORY_PATH.glob('*.yaml'):
  profile_record=load_profile_record(profile_file_path)
  if profile_record['profile_id']==profile_identifier:return profile_record
 raise ValueError('등록되지 않은 ANNY 프로필')
def load_attribute_defaults():
 return load_profile_attribute_defaults(load_active_profile())
def parse_unique_attribute_fields(current_field_pairs):
 current_attribute_record={}
 for current_field_name,current_field_value in current_field_pairs:
  if current_field_name in current_attribute_record:raise ValueError(f'ANNY 기본 속성 중복 필드: {current_field_name}')
  current_attribute_record[current_field_name]=current_field_value
 return current_attribute_record

def reject_attribute_nonfinite_constant(current_constant_name):
 raise ValueError(f'ANNY 기본 속성의 비유한 숫자: {current_constant_name}')

def load_profile_attribute_defaults(current_profile_record):
 baseline_attribute_values=json.loads((ROOT/current_profile_record['attributes_path']).read_text(),object_pairs_hook=parse_unique_attribute_fields,parse_constant=reject_attribute_nonfinite_constant)
 validate_anny_attribute_structure(baseline_attribute_values)
 for current_attribute_name,current_attribute_value in current_profile_record['attribute_overrides'].items():
  if current_attribute_name not in baseline_attribute_values['phenotype_kwargs'] and current_attribute_name not in baseline_attribute_values['local_changes_kwargs'] and current_attribute_name not in baseline_attribute_values['facial_actions']:raise ValueError('ANNY 프로필 속성 대상 오류')
  for attribute_group_name in ('phenotype_kwargs','local_changes_kwargs','facial_actions'):
   if current_attribute_name in baseline_attribute_values[attribute_group_name]:baseline_attribute_values[attribute_group_name][current_attribute_name]=current_attribute_value
 validate_anny_attribute_structure(baseline_attribute_values)
 baseline_attribute_values['local_changes_kwargs']['hip-waist-up']=0.0
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
  with ANNY_HISTORY_SERVICE_LOCK:
   return self.handle_locked_request(h)
 def handle_locked_request(self,h):
  path=urlsplit(h.path).path
  if not path.startswith('/anny-attributes'): return False
  try:
   if h.command=='GET' and path in {'/anny-attributes/','/anny-attributes/embedded/'}:self.send(h,200,PAGE.encode(),'text/html; charset=utf-8');return True
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
     current_history_record=json.loads(history_record_path.read_text());current_history_record['path']=str(history_record_path.parent.resolve());current_history_record['status']=read_anny_generation_status(history_record_path.parent);
     current_history_record['preview_ready']=all((history_record_path.parent/name).is_file() or (history_record_path.parent/'render'/name).is_file() for name in ('front.png','side.png'));stored_history_records.append(current_history_record)
    self.send(h,200,{'records':stored_history_records});return True
   if h.command=='POST' and path in ('/anny-attributes/cancel','/anny-attributes/resume'):
    if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
    selected_request_record=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
    if set(selected_request_record)!={'id'} or not re.fullmatch(r'[0-9a-f]{8}',selected_request_record['id']):raise ValueError('작업 ID 오류')
    selected_job_directory=JOBS/selected_request_record['id']
    if path.endswith('/resume') and not (selected_job_directory/'gpu-command.json').exists():
     saved_request_record=json.loads((selected_job_directory/'history.json').read_text())['request']
     saved_command_values=[str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(selected_job_directory/'attributes.json'),'--output-dir',str(selected_job_directory/'render'),'--rotation-y',str(saved_request_record.get('render_settings',{}).get('rotation_y',0))]+(['--mesh-only'] if saved_request_record.get('kind')=='preview' else [])
     (selected_job_directory/'gpu-command.json').write_text(json.dumps({'command':saved_command_values,'service':'anny'}))
    self.send(h,200,(resume_gpu_generation if path.endswith('/resume') else cancel_gpu_generation)(JOBS/selected_request_record['id']));return True
   history_delete_match=re.fullmatch(r'/anny-attributes/history/([0-9a-f]{8})/delete',path)
   if h.command=='POST' and history_delete_match:
    if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
    selected_request_record=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
    if selected_request_record!={'id':history_delete_match.group(1)}:raise ValueError('삭제 대상 작업 ID 오류')
    self.send(h,200,delete_anny_history_record(history_delete_match.group(1)));return True
   if h.command=='GET' and path=='/anny-attributes/history/reset-preview':
    self.send(h,200,preview_anny_history_cleanup());return True
   if h.command=='POST' and path=='/anny-attributes/history/reset':
    if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
    current_expected_jobs=read_cleanup_confirmation(json.loads(h.rfile.read(int(h.headers['Content-Length']))))
    self.send(h,200,clear_anny_history_records(current_expected_jobs));return True
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
     state=read_anny_generation_status(root);state['preview_ready']=all((root/name).is_file() or (root/'render'/name).is_file() for name in ('front.png','side.png'));state['mesh_ready']=(root/'render'/'mesh.json').is_file();
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
    attribute_maximum_value=180 if rotation_attribute_flag else 3 if attribute_key_name in HEAD_SCALE_ATTRIBUTE_NAMES else 1
    if type(attribute_numeric_value) not in (int,float) or not attribute_minimum_value<=attribute_numeric_value<=attribute_maximum_value:raise ValueError('속성 범위 오류')
   for attribute_group_name in ('phenotype_kwargs','local_changes_kwargs','facial_actions'):
    attrs[attribute_group_name].update({attribute_key_name:attribute_numeric_value for attribute_key_name,attribute_numeric_value in changed.items() if attribute_key_name in attrs[attribute_group_name]})
   apply_bone_rotations(attrs,changed)
   ident=uuid.uuid4().hex[:8];root=JOBS/ident;root.mkdir(parents=True);(root/'attributes.json').write_text(json.dumps(attrs));(root/'status.json').write_text(json.dumps({'status':'running'}))
   (root/'history.json').write_text(json.dumps({'id':ident,'created_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'request':{'attributes':{attribute_field_name:attribute_field_value for attribute_field_name,attribute_field_value in changed.items() if attribute_field_name!='rotation_y'},'render_settings':{'rotation_y':changed.get('rotation_y',0)},'kind':'preview' if path.endswith('/preview') else 'render'},'status':{'status':'running'}},ensure_ascii=False))
   preview_mesh_only=path=='/anny-attributes/preview'
   with (root/'worker.log').open('w') as worker_log_stream:
    launch_gpu_process([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(root/'attributes.json'),'--output-dir',str(root/'render'),'--rotation-y',str(changed.get('rotation_y',0))]+(['--mesh-only'] if preview_mesh_only else []),root,'anny',stdout=worker_log_stream,stderr=subprocess.STDOUT,start_new_session=True)
   self.send(h,202,{'id':ident});return True

  except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
