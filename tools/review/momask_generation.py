"""관리도구의 고정 프롬프트 MoMask 생성 작업 API."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, urlsplit
import json, os, re, signal, subprocess, threading, uuid, html, yaml
try:
 from .management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
except ImportError:
 from management_log_viewer import MANAGEMENT_LOG_VIEWER_SCRIPT
ROOT=Path(__file__).resolve().parents[2]
JOB_ROOT=ROOT/'.tmp/momask-generator/jobs'
HISTORY_ROOT=ROOT/'.tmp/momask-generator/history'
ACTIONS={'standing':{'label':'대기','frames':16},'deep_breath':{'label':'심호흡','frames':32},'stretch':{'label':'스트레칭','frames':40},'walking':{'label':'걷기','frames':32}}
DIRECTIONS=('down_left','down_right','up_left','up_right')
def render_standing_corrections(correction_file_name='standing-corrections.yaml'):
 correction_config_values=yaml.safe_load((ROOT/'generators/momask/config'/correction_file_name).read_text())
 correction_display_fields=[('max_torso_pitch_degrees','상체 전방 기울기 제한','°',1),('upper_arm_outward_degrees','위팔 바깥 벌림','°',1),('forearm_outward_degrees','아래팔 바깥 벌림','°',1),('chest_backward_rotation_degrees','가슴 후방 회전','°',1)]
 return '<dl>'+''.join('<dt>'+display_field_label+'</dt><dd>'+str(correction_config_values[config_field_name]*display_unit_scale)+' '+display_unit_label+'</dd>' for config_field_name,display_field_label,display_unit_label,display_unit_scale in correction_display_fields)+'</dl><p>가슴 아래를 중심으로 뒤로 회전 · 어깨 상하 이동 보정 없음 · 골반·발 위치 고정 · 원본 프레임 수 유지</p>'

PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>MoMask 모션 생성기</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/momask-generator/studio.css">
<link rel="stylesheet" href="/momask-generator/layout.css">
<header class="app-header"><h1>MoMask 모션 생성기</h1><p>고정 동작을 생성하고, OpenPose와 ANNY 모델을 같은 프레임으로 검토합니다.</p><p>새 생성 기준 모델: __ANNY_BASELINE_MODEL__</p></header>
<main class="motion-studio-layout"><section class="studio-panel control-panel"><h2>생성 설정</h2><label class="form-label">포즈 <select id="action"><option value="standing">대기 · 원본 16프레임</option><option value="deep_breath">심호흡 · 원본 32프레임</option><option value="stretch">스트레칭 · 원본 40프레임</option><option value="walking">걷기 · 원본 32프레임</option></select></label><h3>방향</h3><div class="directions"><label><input type="checkbox" value="down_left" checked> 좌하향</label><label><input type="checkbox" value="down_right" checked> 우하향</label><label><input type="checkbox" value="up_left" checked> 좌상향</label><label><input type="checkbox" value="up_right" checked> 우상향</label></div><details data-correction-action="standing"><summary>대기 모션 보정값</summary><p>대기 생성에만 적용됩니다. 관절 이동량이며 피부 표면의 이동량과는 다를 수 있습니다.</p>__STANDING_CORRECTION_DETAILS__</details><details data-correction-action="deep_breath" hidden><summary>심호흡 모션 보정값 · 32프레임</summary>__DEEP_BREATH_CORRECTION_DETAILS__</details><h3>고정 스크립트</h3><pre id="prompt"></pre><div class="action-row"><button id="run" class="primary">모션 생성 시작</button><button id="cancel" disabled>실행 중인 생성 취소</button></div><h3 class="status-heading">현재 작업 상태</h3><p id="status" class="status-line" role="status">대기 중 · 설정을 고른 뒤 ‘모션 생성 시작’을 누르세요.</p><p class="status-help">생성이 시작되면 진행 상태와 로그가 자동으로 갱신됩니다.</p><details id="log-details" class="log-details"><summary>현재 작업 로그</summary><pre id="log">로그 대기</pre></details></section><section class="studio-panel result-panel"><div class="result-toolbar"><h2>생성 결과</h2><div><label>방향 <select id="resultDirection"></select></label><button id="previous" disabled>← 이전</button><button id="play" disabled>재생</button><button id="stop" disabled>중지</button><button id="next" disabled>다음 →</button><label>속도 <select id="speed"><option value="500">2fps</option><option value="250" selected>4fps</option><option value="125">8fps</option></select></label><input id="frame-range" class="frame-scrubber" type="range" min="0" max="0" value="0" disabled aria-label="프레임 선택"></div></div><div class="stages"><figure class="stage"><figcaption>OpenPose</figcaption><img id="openpose-result" alt="OpenPose 생성 결과" decoding="async"></figure><figure class="stage"><figcaption id="rig-caption">Anny 모델</figcaption><img id="rig-result" alt="Anny 모델 생성 결과" decoding="async"></figure></div><p id="frame" class="frame-count">결과 이력에서 ‘결과 보기’를 선택하세요.</p></section><section class="studio-panel motion-history-panel" aria-label="생성 이력"><div class="history-actions"><p>생성 이력 관리</p><div class="action-row"><button id="refresh">생성 이력 새로고침</button><button id="clear" class="danger">생성 이력 모두 초기화</button></div></div><div class="history"><div class="history-header"><h2>생성 이력</h2><span id="history-summary">불러오는 중</span></div><ul id="history-list" class="history-list"></ul><div class="pager"><button id="history-prev" type="button">← 이전</button><span id="history-page"></span><button id="history-next" type="button">다음 →</button></div></div></section></main>
<script>__MANAGEMENT_LOG_VIEWER_SCRIPT__</script>
<script>
const fixed={walking:'A person walks forward at a relaxed pace.',standing:'A person stands.',deep_breath:"A person starts in a neutral standing posture with both arms relaxed at the sides, takes a deep breath in and out, then returns to the same neutral standing posture.",stretch:'A person starts standing still with both arms hanging by the body and hands near the thighs, raises both arms above the head for a gentle stretch, then lowers both arms back beside the body and ends in the same standing pose.'};
const labels={walking:'걷기',standing:'대기',deep_breath:'심호흡',stretch:'스트레칭'},statusLabels={running:'생성 진행 중',completed:'생성 완료',failed:'생성 실패',cancelled:'생성 취소됨'};let activeBaselineModelId='',job=null,timer=null,index=0,frames={openpose:[],rig:[]},resultLayout='legacy',historyPage=1,intervalMs=250;const $=s=>document.querySelector(s);const logViewer=window.ManagementLogViewer.attach($('#log-details'),$('#log'));function selected(){return [...document.querySelectorAll('.directions input:checked')].map(x=>x.value)}function updatePrompt(){const selectedActionValue=$('#action').value;$('#prompt').textContent=fixed[selectedActionValue];for(const correctionPanelElement of document.querySelectorAll('[data-correction-action]')){correctionPanelElement.hidden=correctionPanelElement.dataset.correctionAction!==selectedActionValue}}$('#action').onchange=updatePrompt;updatePrompt();const decodedFrames=new Map();function prefetch(url){if(!url||decodedFrames.has(url))return;const image=new Image();image.decoding='async';image.src=url;decodedFrames.set(url,image);image.decode?.().catch(()=>{});if(decodedFrames.size>12)decodedFrames.delete(decodedFrames.keys().next().value)}function setFrameImage(element,url){if(url&&element.dataset.frameUrl!==url){element.dataset.frameUrl=url;element.src=url}}function draw(){if(!frames.openpose.length)return;const annyUrl=frames.rig[index]||'';setFrameImage($('#openpose-result'),frames.openpose[index]);setFrameImage($('#rig-result'),annyUrl);for(const offset of [1,2]){const next=(index+offset)%frames.openpose.length;prefetch(frames.openpose[next]);prefetch(frames.rig[next])}$('#rig-caption').textContent=frames.rig.length?'Anny 모델'+(activeBaselineModelId?' · '+activeBaselineModelId:''):'Anny 모델 · 이전 이력에는 없음';$('#frame-range').max=Math.max(0,frames.openpose.length-1);$('#frame-range').value=index;$('#frame').textContent=`${index+1} / ${frames.openpose.length}`}function stop(){clearInterval(timer);timer=null;$('#play').textContent='재생'}function step(amount){if(!frames.openpose.length)return;index=(index+amount+frames.openpose.length)%frames.openpose.length;requestAnimationFrame(draw)}async function poll(){if(!job)return;const r=await fetch('/momask-generator/jobs/'+job),d=await r.json();if(!r.ok){$('#status').textContent=d.error;return}$('#status').textContent=statusLabels[d.status]||d.status;logViewer.update(d.log);$('#cancel').disabled=d.status!=='running';if(d.result){activeBaselineModelId=d.result.baseline_model?.baseline_id||'';const dir=$('#resultDirection').value||d.result.directions[0];resultLayout=d.result.anny_frames===d.result.frames?'paired':'legacy';const openposeRoot=resultLayout==='paired'?`/momask-generator/jobs/${job}/result/openpose/${dir}`:`/momask-generator/jobs/${job}/result/${dir}`;$('#resultDirection').replaceChildren(...d.result.directions.map(v=>new Option(v,v,v===dir)));frames.openpose=Array.from({length:d.result.frames},(_,i)=>`${openposeRoot}/openpose-${String(i+1).padStart(4,'0')}.png?frame=${i}&job=${job}`);frames.rig=resultLayout==='paired'?Array.from({length:d.result.frames},(_,i)=>`/momask-generator/jobs/${job}/result/anny/${dir}/frames/anny-${String(i+1).padStart(4,'0')}.png?frame=${i}&job=${job}`):[];index=0;draw();$('#play').disabled=false;$('#stop').disabled=false;$('#previous').disabled=false;$('#next').disabled=false;$('#frame-range').disabled=false}if(d.status==='running')setTimeout(poll,1500);else refreshHistory()}
function copyId(id){navigator.clipboard.writeText(id).then(()=>$('#status').textContent='생성 이력 ID를 복사했습니다: '+id).catch(()=>$('#status').textContent='ID 복사에 실패했습니다: '+id)}
function selectHistory(id){job=id;stop();$('#play').disabled=true;frames={openpose:[],rig:[]};poll()}
function renderHistory(data){const list=$('#history-list');list.replaceChildren();$('#history-summary').textContent=`총 ${data.total}건 · 최신순`;for(const item of data.records){const row=document.createElement('li'),info=document.createElement('div'),play=document.createElement('button'),copy=document.createElement('button'),meta=document.createElement('div');info.textContent=labels[item.action]||item.action;meta.className='history-meta';meta.textContent=`${item.created_at} · ${item.status} · ${item.id}`;info.append(meta);play.type=copy.type='button';play.textContent='결과 보기';copy.textContent='ID 복사';play.onclick=()=>selectHistory(item.id);copy.onclick=()=>copyId(item.id);row.className='history-row'+(item.id===job?' selected':'');row.append(info,play,copy);list.append(row)}if(!data.records.length){const empty=document.createElement('li');empty.textContent='누적 생성 이력이 없습니다.';list.append(empty)}$('#history-page').textContent=`${data.page} / ${data.page_count}`;$('#history-prev').disabled=data.page<=1;$('#history-next').disabled=data.page>=data.page_count;$('#history-prev').onclick=()=>{historyPage--;refreshHistory()};$('#history-next').onclick=()=>{historyPage++;refreshHistory()};$('#run').disabled=data.running}
async function refreshHistory(){const r=await fetch('/momask-generator/history?page='+historyPage),d=await r.json();if(!r.ok){$('#history-summary').textContent=d.error;return}historyPage=d.page;renderHistory(d)}
$('#run').onclick=async()=>{const directions=selected();if(!directions.length)return $('#status').textContent='방향을 하나 이상 선택하세요.';const r=await fetch('/momask-generator/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:$('#action').value,directions})}),d=await r.json();if(!r.ok)return $('#status').textContent=d.error;job=d.id;historyPage=1;$('#run').disabled=true;poll();refreshHistory()};$('#cancel').onclick=async()=>{await fetch('/momask-generator/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:job})});poll()};$('#resultDirection').onchange=()=>{const dir=$('#resultDirection').value;const openposeRoot=resultLayout==='paired'?`/momask-generator/jobs/${job}/result/openpose/${dir}`:`/momask-generator/jobs/${job}/result/${dir}`;frames.openpose=frames.openpose.map((_,i)=>`${openposeRoot}/openpose-${String(i+1).padStart(4,'0')}.png?frame=${i}&job=${job}`);frames.rig=frames.rig.map((_,i)=>`/momask-generator/jobs/${job}/result/anny/${dir}/frames/anny-${String(i+1).padStart(4,'0')}.png?frame=${i}&job=${job}`);index=0;draw()};$('#previous').onclick=()=>step(-1);$('#next').onclick=()=>step(1);$('#stop').onclick=stop;$('#frame-range').oninput=()=>{index=Number($('#frame-range').value);draw()};$('#speed').onchange=()=>{intervalMs=Number($('#speed').value);if(timer){stop();$('#play').click()}};document.addEventListener('keydown',event=>{if(event.target.matches('input,select,textarea'))return;if(event.key==='ArrowLeft'){event.preventDefault();step(-1)}if(event.key==='ArrowRight'){event.preventDefault();step(1)}if(event.key===' '&&frames.openpose.length){event.preventDefault();$('#play').click()}});$('#play').onclick=()=>{if(timer)stop();else{timer=setInterval(()=>step(1),intervalMs);$('#play').textContent='일시정지'}};$('#refresh').onclick=()=>{if(job)poll();refreshHistory()};$('#clear').onclick=async()=>{if(confirm('누적 이력만 초기화합니다.')){await fetch('/momask-generator/history/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'reset'})});historyPage=1;refreshHistory()}};refreshHistory();
</script>"""
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d: raise ValueError('중복 필드')
  d[k]=v
 return d
class MoMaskGenerationManager:
 route='/momask-generator'
 def __init__(self): self.process=None;self.job=None;self.lock=threading.Lock()
 def send(self,h,status,payload,ctype='application/json; charset=utf-8'):
  data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode();h.send_response(status);h.send_header('Content-Type',ctype);h.send_header('Content-Length',str(len(data)));h.send_header('Cache-Control','no-store');h.end_headers();h.wfile.write(data)
 def history(self):
  HISTORY_ROOT.mkdir(parents=True,exist_ok=True);return [json.loads(p.read_text()) for p in sorted(HISTORY_ROOT.glob('*.json'),reverse=True)]
 def status(self,identifier):
  root=JOB_ROOT/identifier;state=json.loads((root/'status.json').read_text());log=(root/'worker.log').read_text(errors='replace')[-12000:] if (root/'worker.log').exists() else '';state['log']=log
  if (root/'result.json').exists(): state['result']=json.loads((root/'result.json').read_text())
  return state
 def handle(self,h):
  request=urlsplit(h.path);path=request.path;query=parse_qs(request.query)
  if not(path==self.route or path.startswith(self.route+'/')): return False
  try:
   origin=f'http://127.0.0.1:{h.server.server_port}'
   if h.headers.get('Host')!=origin.removeprefix('http://'): raise ValueError('허용하지 않는 Host')
   if h.command=='GET' and path in (self.route,self.route+'/'): self.send(h,200,PAGE.replace('__DEEP_BREATH_CORRECTION_DETAILS__',render_standing_corrections('deep-breath-corrections.yaml')).replace('__STANDING_CORRECTION_DETAILS__',render_standing_corrections()).replace('__ANNY_BASELINE_MODEL__',html.escape(yaml.safe_load((ROOT/'generators/animation/config/anny_model_baseline.yaml').read_text())['baseline_id'])).replace('__MANAGEMENT_LOG_VIEWER_SCRIPT__',MANAGEMENT_LOG_VIEWER_SCRIPT).encode(),'text/html; charset=utf-8');return True
   if h.command=='GET' and path in (self.route+'/studio.css',self.route+'/layout.css'):
    stylesheet_file_name='generation-studio.css' if path.endswith('/studio.css') else 'momask-studio.css'
    self.send(h,200,Path(__file__).with_name(stylesheet_file_name).read_bytes(),'text/css; charset=utf-8');return True
   if h.command=='GET' and path==self.route+'/history':
    page=max(1,int(query.get('page',['1'])[0]));page_size=8;records=self.history();total=len(records);page_count=max(1,(total+page_size-1)//page_size);page=min(page,page_count);start=(page-1)*page_size
    self.send(h,200,{'records':records[start:start+page_size],'total':total,'page':page,'page_size':page_size,'page_count':page_count,'running':self.process is not None and self.process.poll() is None});return True
   match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)',path)
   frame_match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)/result/(openpose|rig)/(down_left|down_right|up_left|up_right)/((?:openpose|rig)-\d{4}\.png)',path)
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
   if path==self.route+'/history/reset':
    if body!={'action':'reset'}: raise ValueError('초기화 요청 오류')
    for p in HISTORY_ROOT.glob('*.json'):p.unlink()
    self.send(h,200,{'status':'cleared'});return True
   if path==self.route+'/cancel':
    if set(body)!={'id'} or body['id']!=self.job or not self.process or self.process.poll() is not None: raise ValueError('실행 중인 작업이 아닙니다.')
    os.killpg(self.process.pid,signal.SIGTERM);(JOB_ROOT/self.job/'status.json').write_text(json.dumps({'status':'cancelled'}));self.send(h,200,{'status':'cancelled'});return True
   if path!=self.route+'/jobs' or set(body)!={'action','directions'} or body['action'] not in ACTIONS or not isinstance(body['directions'],list) or not body['directions'] or set(body['directions'])-set(DIRECTIONS) or len(set(body['directions']))!=len(body['directions']): raise ValueError('포즈 또는 방향 요청 오류')
   with self.lock:
    if self.process and self.process.poll() is None: raise ValueError('MoMask 생성 작업이 실행 중입니다.')
    identifier=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8];root=JOB_ROOT/identifier;root.mkdir(parents=True);(root/'status.json').write_text(json.dumps({'status':'running'}));(root/'request.json').write_text(json.dumps(body,ensure_ascii=False));log=(root/'worker.log').open('w');self.process=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/momask/run_managed_generation.py'),'--job-dir',str(root),'--action',body['action'],'--directions',','.join(body['directions'])],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);self.job=identifier;HISTORY_ROOT.mkdir(parents=True,exist_ok=True);record={'id':identifier,'created_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'action':body['action'],'directions':body['directions'],'status':'running'};(HISTORY_ROOT/(identifier+'.json')).write_text(json.dumps(record,ensure_ascii=False))
    def watch():
     code=self.process.wait();state={'status':'completed' if code==0 else 'failed','exit_code':code};status_path=root/'status.json';
     if json.loads(status_path.read_text()).get('status')=='running':status_path.write_text(json.dumps(state,ensure_ascii=False))
     record['status']=json.loads(status_path.read_text()).get('status');(HISTORY_ROOT/(identifier+'.json')).write_text(json.dumps(record,ensure_ascii=False))
    threading.Thread(target=watch,daemon=True).start()
   self.send(h,202,{'id':identifier,'status':'running'});return True
  except (ValueError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
