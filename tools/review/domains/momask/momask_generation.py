"""관리도구의 고정 프롬프트 MoMask 생성 작업 API."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from urllib.parse import parse_qs, urlsplit
import json, re
from tools.review.common.management_gateway import execute_momask_command
from tools.review.domains.momask.momask_jobs import start_generation_job, cancel_generation_job, check_generation_running, list_generation_history, read_generation_status, reset_generation_history
from tools.review.common.management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
ROOT=Path(__file__).resolve().parents[4]
JOB_ROOT=ROOT/'.tmp/momask-generator/jobs'
HISTORY_ROOT=ROOT/'.tmp/momask-generator/history'
ACTIONS={'standing':{'label':'대기','frames':16},'walking':{'label':'걷기','frames':32},'resting':{'label':'휴식','frames':160}}
HISTORICAL_ACTIONS={**ACTIONS,'custom':{'label':'커스텀','frames':120},'stretch':{'label':'스트레칭','frames':120},'deep_breath':{'label':'심호흡','frames':32}}
DIRECTIONS=('down_left','down_right','up_left','up_right')
def render_position_retarget_policy():
 return '<p>모든 동작에 같은 관절 대응과 회전 계산을 적용합니다. 원본 관절 위치를 동작별로 보정하지 않으며 회전 제한·쇄골 상승·손가락 자동 자세·관절 스무딩·접지 보정을 추가하지 않습니다. 위치로 알 수 없는 비틀림은 연속 전달하고 손가락 등 미대응 본은 기준 자세를 유지합니다. 새 생성부터 적용되며 기존 결과는 유지됩니다.</p>'


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
   self.send(h,410,{'error':'MoMask 포즈 생성기와 과거 기록은 폐기되었습니다. HY-Motion을 사용하세요.'});return True
  except (ValueError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
