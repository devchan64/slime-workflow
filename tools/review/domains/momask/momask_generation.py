"""관리도구의 고정 프롬프트 MoMask 생성 작업 API."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from tools.review.ui_assets import resolve_review_ui_asset
from tools.review.domains.anny.anny_attributes import load_active_profile
from urllib.parse import parse_qs, urlsplit
import json, re, html, yaml, ast
from tools.review.common.management_gateway import execute_momask_command
from tools.review.domains.momask.momask_jobs import start_generation_job, cancel_generation_job, check_generation_running, list_generation_history, read_generation_status, reset_generation_history
from tools.review.domains.momask.openpose_maps import generate_openpose_maps
from tools.review.common.management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
ROOT=Path(__file__).resolve().parents[4]
JOB_ROOT=ROOT/'.tmp/momask-generator/jobs'
HISTORY_ROOT=ROOT/'.tmp/momask-generator/history'
ACTIONS={'standing':{'label':'대기','frames':16},'stretch':{'label':'스트레칭','frames':120},'walking':{'label':'걷기','frames':32}}
HISTORICAL_ACTIONS={**ACTIONS,'deep_breath':{'label':'심호흡','frames':32}}
DIRECTIONS=('down_left','down_right','up_left','up_right')
def render_standing_corrections(correction_file_name='standing-corrections.yaml'):
 correction_config_values=yaml.safe_load((ROOT/'generators/momask/config'/correction_file_name).read_text())
 correction_display_fields=[('max_torso_pitch_degrees','상체 전방 기울기 제한','°',1),('upper_arm_outward_degrees','위팔 바깥 벌림','°',1),('forearm_outward_degrees','아래팔 바깥 벌림','°',1),('chest_backward_rotation_degrees','가슴 후방 회전','°',1)]
 return '<dl>'+''.join('<dt>'+display_field_label+'</dt><dd>'+str(correction_config_values[config_field_name]*display_unit_scale)+' '+display_unit_label+'</dd>' for config_field_name,display_field_label,display_unit_label,display_unit_scale in correction_display_fields)+'</dl><p>가슴 아래를 중심으로 뒤로 회전 · 골반·발 위치 고정 · 원본 프레임 수 유지</p>'

def read_correction_constants(source_relative_path, selected_constant_names):
 source_syntax_tree=ast.parse((ROOT/source_relative_path).read_text())
 return {assignment_node.targets[0].id:ast.literal_eval(assignment_node.value) for assignment_node in source_syntax_tree.body if isinstance(assignment_node,ast.Assign) and isinstance(assignment_node.targets[0],ast.Name) and assignment_node.targets[0].id in selected_constant_names}

def render_stretch_arm_corrections():
 correction_config_values=yaml.safe_load((ROOT/'generators/momask/config/stretch-arm-corrections.yaml').read_text())
 smoothing_constant_values=read_correction_constants('generators/momask/render_anny_frames.py',{'JOINT_SMOOTHING_FACTOR','JOINT_SMOOTHING_ITERATIONS'})
 finger_constant_values=read_correction_constants('generators/momask/anny_hand_pose.py',{'FINGER_CURL_DEGREES','THUMB_CURL_DEGREES'})
 correction_display_fields=[('upper_arm_twist_degrees','위팔 추가 비틀림 한도','°'),('forearm_twist_degrees','아래팔 추가 비틀림 한도','°'),('max_twist_step_degrees','프레임당 추가 비틀림 변화 한도','°')]
 correction_rows=[(label,str(correction_config_values[key])+unit) for key,label,unit in correction_display_fields]
 correction_rows.extend([
 ('추가 비틀림 적용 비율',str(round(correction_config_values['twist_strength']*100))+'%'),
 ('위팔 전체 회전 변화 한도',str(correction_config_values['max_upper_arm_step_degrees'])+'°/프레임'),
 ('아래팔 전체 회전 변화 한도',str(correction_config_values['max_forearm_step_degrees'])+'°/프레임'),
 ('쇄골·어깨','팔 올림에 따라 쇄골 최대 '+str(correction_config_values['shoulder_elevation_degrees'])+'° 상승'),
 ('스키닝','볼륨 보존 ON'),
 ('관절 스무딩 강도',str(smoothing_constant_values['JOINT_SMOOTHING_FACTOR'])),
 ('관절 스무딩 반복',str(smoothing_constant_values['JOINT_SMOOTHING_ITERATIONS'])+'회'),
 ('손가락 굽힘 · 첫째/둘째/셋째 관절',' / '.join(str(value)+'°' for value in finger_constant_values['FINGER_CURL_DEGREES'])),
 ('엄지 굽힘 · 첫째/둘째/셋째 관절',' / '.join(str(value)+'°' for value in finger_constant_values['THUMB_CURL_DEGREES'])),
 ('발 접지','프레임별 최저 표면 높이 보정 · 발 고정 IK 없음')])
 return '<p>새 스트레칭 생성에 적용할 현재 설정입니다. 과거 결과의 설정과는 다를 수 있습니다.</p><dl>'+''.join('<dt>'+html.escape(label)+'</dt><dd>'+html.escape(value)+'</dd>' for label,value in correction_rows)+'</dl><p>추가 비틀림 제한은 팔을 들어 올리는 전체 회전량을 제한하지 않습니다.</p>'

def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d: raise ValueError('중복 필드')
  d[k]=v
 return d
class MoMaskGenerationManager:
 route='/momask-generator'
 def send(self,h,status,payload,ctype='application/json; charset=utf-8'):
  data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode();h.send_response(status);h.send_header('Content-Type',ctype);h.send_header('Cross-Origin-Resource-Policy','cross-origin' if ctype=='image/png' else 'same-origin');h.send_header('Content-Length',str(len(data)));h.send_header('Cache-Control','no-store');h.end_headers();h.wfile.write(data)
 def history(self):
  return execute_momask_command('history',{})
 def status(self,identifier):
  return execute_momask_command('status',{'id':identifier})
 def handle(self,h):
  request=urlsplit(h.path);path=request.path;query=parse_qs(request.query)
  if not(path==self.route or path.startswith(self.route+'/')): return False
  try:
   origin=f'http://127.0.0.1:{h.server.server_port}'
   if h.headers.get('Host')!=origin.removeprefix('http://'): raise ValueError('허용하지 않는 Host')
   if h.command=='GET' and path in (self.route,self.route+'/'):
    from tools.review.common.gradio_process import ensure_gradio_server
    gradio_page_url=ensure_gradio_server(h.server.server_port)
    h.send_response(302);h.send_header('Location',gradio_page_url);h.send_header('Cache-Control','no-store');h.end_headers();return True
   if h.command=='GET' and path in (self.route+'/studio.css',self.route+'/layout.css'):
    stylesheet_file_name='generation-studio.css' if path.endswith('/studio.css') else 'momask-studio.css'
    self.send(h,200,resolve_review_ui_asset(stylesheet_file_name).read_bytes(),'text/css; charset=utf-8');return True
   if h.command=='GET' and path==self.route+'/history-ui.js':self.send(h,200,resolve_review_ui_asset('generation-history.js').read_bytes(),'text/javascript');return True
   if h.command=='GET' and path==self.route+'/history':
    records=self.history()
    for history_record_value in records:
     history_status_value=history_record_value['status']
     history_record_value['status']={'status':history_status_value}
     history_record_value['request']={'action':history_record_value['action'],'directions':history_record_value.get('directions',[]),'frames':HISTORICAL_ACTIONS[history_record_value['action']]['frames']}
     history_record_value['playable']=history_status_value=='completed'
     history_record_value['path']=str(JOB_ROOT/history_record_value['id'])
     if history_status_value!='completed':continue
     history_result_root=JOB_ROOT/history_record_value['id']/'result'
     history_preview_paths=sorted(history_result_root.glob('anny/*/frames/anny-0001.png')) or sorted(history_result_root.glob('openpose/*/openpose-0001.png')) or sorted(history_result_root.glob('*/openpose-0001.png'))
     if history_preview_paths:history_record_value['thumbnail']=self.route+'/jobs/'+history_record_value['id']+'/result/'+history_preview_paths[0].relative_to(history_result_root).as_posix()
    self.send(h,200,{'records':records,'running':check_generation_running()});return True
   match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)',path)
   frame_match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)/result/(openpose-map|openpose|rig)/(down_left|down_right|up_left|up_right)/((?:openpose-map|openpose|rig)-\d{4}\.png)',path)
   legacy_frame_match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)/result/(down_left|down_right|up_left|up_right)/(openpose-\d{4}\.png)',path)
   anny_frame_match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)/result/anny/(down_left|down_right|up_left|up_right)/frames/(anny-\d{4}\.png)',path)
   if h.command=='GET' and (match or frame_match or legacy_frame_match or anny_frame_match):
    if frame_match:
     root=JOB_ROOT/frame_match[1]
     if not frame_match[4].startswith(frame_match[2]+'-'): raise ValueError('결과 프레임 경로 오류')
     self.send(h,200,(root/'result'/frame_match[2]/frame_match[3]/frame_match[4]).read_bytes(),'image/png');return True
    if anny_frame_match:
     root=JOB_ROOT/anny_frame_match[1];self.send(h,200,(root/'result'/'anny'/anny_frame_match[2]/'frames'/anny_frame_match[3]).read_bytes(),'image/png');return True
    if legacy_frame_match:
     root=JOB_ROOT/legacy_frame_match[1];self.send(h,200,(root/'result'/legacy_frame_match[2]/legacy_frame_match[3]).read_bytes(),'image/png');return True
    self.send(h,200,self.status(match[1]));return True
   if h.command!='POST' or h.headers.get('Origin')!=origin or h.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('요청 형식 오류')
   body=json.loads(h.rfile.read(int(h.headers.get('Content-Length','0'))),object_pairs_hook=unique)
   if path==self.route+'/openpose-map':
    if set(body)-{'id','face'} or 'id' not in body or not re.fullmatch(r'[0-9a-f_-]+',body['id']):raise ValueError('생성 이력 ID 오류')
    if self.status(body['id'])['status']!='completed':raise ValueError('완료된 생성 이력이 필요합니다.')
    self.send(h,200,execute_momask_command('openpose-map',body));return True
   if path==self.route+'/history/reset':
    if body!={'action':'reset'}: raise ValueError('초기화 요청 오류')
    self.send(h,200,execute_momask_command('history-reset',{}));return True
   if path==self.route+'/resume':
    if set(body)!={'id'}: raise ValueError('재개 요청 오류')
    self.send(h,202,execute_momask_command('resume',body));return True
   if path==self.route+'/cancel':
    if set(body)!={'id'}: raise ValueError('취소 요청 오류')
    self.send(h,200,execute_momask_command('cancel',body));return True
   if path!=self.route+'/jobs' or set(body)-{'action','directions','face'} or not {'action','directions'}<=set(body) or body['action'] not in ACTIONS or not isinstance(body['directions'],list) or not body['directions'] or set(body['directions'])-set(DIRECTIONS) or len(set(body['directions']))!=len(body['directions']): raise ValueError('포즈 또는 방향 요청 오류')
   self.send(h,202,execute_momask_command('generate',body));return True
  except (ValueError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
