"""관리도구의 고정 프롬프트 MoMask 생성 작업 API."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from urllib.parse import parse_qs, urlsplit
import json, re
from tools.review.common.management_gateway import execute_momask_command
from tools.review.domains.momask.momask_jobs import start_generation_job, cancel_generation_job, check_generation_running, list_generation_history, read_generation_status, reset_generation_history
from tools.review.domains.momask.openpose_maps import generate_openpose_maps
from tools.review.common.management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
ROOT=Path(__file__).resolve().parents[4]
JOB_ROOT=ROOT/'.tmp/momask-generator/jobs'
HISTORY_ROOT=ROOT/'.tmp/momask-generator/history'
ACTIONS={'standing':{'label':'대기','frames':16},'walking':{'label':'걷기','frames':32}}
HISTORICAL_ACTIONS={**ACTIONS,'stretch':{'label':'스트레칭','frames':120},'deep_breath':{'label':'심호흡','frames':32}}
DIRECTIONS=('down_left','down_right','up_left','up_right')
def render_position_retarget_policy():
 return '<p><strong>위치 채널 기반 공통 리타깃</strong></p><p>모든 동작에 같은 관절 대응과 회전 계산을 적용합니다. 원본 관절 위치를 동작별로 보정하지 않으며 회전 제한·쇄골 상승·손가락 자동 자세·관절 스무딩·접지 보정을 추가하지 않습니다. 위치로 알 수 없는 비틀림은 연속 전달하고 손가락 등 미대응 본은 기준 자세를 유지합니다. 새 생성부터 적용되며 기존 결과는 유지됩니다.</p>'


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
    self.send(h,410,{'error':'이전 관리 화면은 폐기되었습니다. /management/에서 Gradio 화면을 여세요.'});return True
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
