"""관리도구의 고정 프롬프트 MoMask 생성 작업 API."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, urlsplit
import json, os, re, signal, subprocess, threading, uuid
ROOT=Path(__file__).resolve().parents[2]
JOB_ROOT=ROOT/'.tmp/momask-generator/jobs'
HISTORY_ROOT=ROOT/'.tmp/momask-generator/history'
ACTIONS={'standing':{'label':'대기','frames':20},'deep_breath':{'label':'심호흡','frames':40},'stretch':{'label':'스트레칭','frames':40}}
DIRECTIONS=('down_left','down_right','up_left','up_right')
PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>MoMask 모션 생성기</title>
<style>
body{margin:0;padding:28px;background:#101814;color:#e7f2e9;font:14px system-ui}main{max-width:1100px;margin:auto;display:grid;grid-template-columns:360px 1fr;gap:20px}section{background:#16241b;border:1px solid #3c6249;border-radius:12px;padding:18px}label,button,select{font:inherit;margin:7px 5px 7px 0}button,select{padding:8px;background:#243b2d;color:#e7f2e9;border:1px solid #547560;border-radius:7px}button:disabled{opacity:.45}pre{white-space:pre-wrap;max-height:250px;overflow:auto;background:#07100b;padding:12px;border-radius:8px}.stage{min-height:420px;display:grid;place-items:center;background:#07100b}.stage img{max-width:100%;max-height:400px}progress{width:100%}.directions{display:grid;grid-template-columns:1fr 1fr}.history{margin-top:18px;border-top:1px solid #3c6249}.history-list{list-style:none;margin:8px 0;padding:0}.history-row{display:grid;grid-template-columns:1fr auto auto;gap:6px;align-items:center;padding:8px 0;border-bottom:1px solid #284333}.history-meta{color:#b7cfbc;font-size:12px}.pager{display:flex;align-items:center;gap:6px}@media(max-width:800px){main{grid-template-columns:1fr}}
</style>
<main><section><h1>MoMask 모션 생성기</h1><label>포즈 <select id="action"><option value="standing">대기 · 원본 20프레임</option><option value="deep_breath">심호흡 · 원본 40프레임</option><option value="stretch">스트레칭 · 원본 40프레임</option></select></label><div class="directions"><label><input type="checkbox" value="down_left" checked> 좌하향</label><label><input type="checkbox" value="down_right" checked> 우하향</label><label><input type="checkbox" value="up_left" checked> 좌상향</label><label><input type="checkbox" value="up_right" checked> 우상향</label></div><h2>고정 스크립트</h2><pre id="prompt"></pre><button id="run">생성</button><button id="cancel" disabled>취소</button><p id="status">대기 중</p><progress id="progress" max="100" value="0"></progress><pre id="log">로그 대기</pre><button id="refresh">로그·이력 새로고침</button><button id="clear">누적 이력 초기화</button><div class="history"><h2>생성 이력</h2><p id="history-summary">불러오는 중</p><ul id="history-list" class="history-list"></ul><div class="pager"><button id="history-prev" type="button">이전</button><span id="history-page"></span><button id="history-next" type="button">다음</button></div></div></section><section><h2>생성 결과 재생</h2><label>방향 <select id="resultDirection"></select></label><button id="play" disabled>재생</button><div class="stage"><img id="result" alt="생성 결과"></div><p id="frame"></p></section></main>
<script>
const fixed={standing:'A person stands still and gently shifts body weight from side to side. Both arms hang relaxed at the sides.',deep_breath:'A person stands in one spot and takes a deep breath while both arms hang by the body with hands near the thighs.',stretch:'A person starts standing still with both arms hanging by the body and hands near the thighs, raises both arms above the head for a gentle stretch, then lowers both arms back beside the body and ends in the same standing pose.'};
const labels={standing:'대기',deep_breath:'심호흡',stretch:'스트레칭'};let job=null,timer=null,index=0,frames=[],historyPage=1;const $=s=>document.querySelector(s);function selected(){return [...document.querySelectorAll('.directions input:checked')].map(x=>x.value)}function updatePrompt(){$('#prompt').textContent=fixed[$('#action').value]}$('#action').onchange=updatePrompt;updatePrompt();function draw(){if(!frames.length)return;$('#result').src=frames[index];$('#frame').textContent=`${index+1} / ${frames.length}`}function stop(){clearInterval(timer);timer=null;$('#play').textContent='재생'}async function poll(){if(!job)return;const r=await fetch('/momask-generator/jobs/'+job),d=await r.json();if(!r.ok){$('#status').textContent=d.error;return}$('#status').textContent=d.status;$('#log').textContent=d.log||'로그 대기';$('#progress').value=d.status==='completed'?100:0;$('#cancel').disabled=d.status!=='running';if(d.result){const dir=$('#resultDirection').value||d.result.directions[0];$('#resultDirection').replaceChildren(...d.result.directions.map(v=>new Option(v,v,v===dir)));frames=Array.from({length:d.result.frames},(_,i)=>`/momask-generator/jobs/${job}/result/${dir}/openpose-${String(i+1).padStart(4,'0')}.png`);index=0;draw();$('#play').disabled=false}if(d.status==='running')setTimeout(poll,1500);else refreshHistory()}
function copyId(id){navigator.clipboard.writeText(id).then(()=>$('#status').textContent='생성 이력 ID를 복사했습니다: '+id).catch(()=>$('#status').textContent='ID 복사에 실패했습니다: '+id)}
function selectHistory(id){job=id;stop();$('#play').disabled=true;frames=[];poll()}
function renderHistory(data){const list=$('#history-list');list.replaceChildren();$('#history-summary').textContent=`총 ${data.total}건 · 최신순`;for(const item of data.records){const row=document.createElement('li'),info=document.createElement('div'),play=document.createElement('button'),copy=document.createElement('button'),meta=document.createElement('div');info.textContent=labels[item.action]||item.action;meta.className='history-meta';meta.textContent=`${item.created_at} · ${item.status} · ${item.id}`;info.append(meta);play.type=copy.type='button';play.textContent='결과 보기';copy.textContent='ID 복사';play.onclick=()=>selectHistory(item.id);copy.onclick=()=>copyId(item.id);row.className='history-row';row.append(info,play,copy);list.append(row)}if(!data.records.length){const empty=document.createElement('li');empty.textContent='누적 생성 이력이 없습니다.';list.append(empty)}$('#history-page').textContent=`${data.page} / ${data.page_count}`;$('#history-prev').disabled=data.page<=1;$('#history-next').disabled=data.page>=data.page_count;$('#history-prev').onclick=()=>{historyPage--;refreshHistory()};$('#history-next').onclick=()=>{historyPage++;refreshHistory()};$('#run').disabled=data.running}
async function refreshHistory(){const r=await fetch('/momask-generator/history?page='+historyPage),d=await r.json();if(!r.ok){$('#history-summary').textContent=d.error;return}historyPage=d.page;renderHistory(d)}
$('#run').onclick=async()=>{const directions=selected();if(!directions.length)return $('#status').textContent='방향을 하나 이상 선택하세요.';const r=await fetch('/momask-generator/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:$('#action').value,directions})}),d=await r.json();if(!r.ok)return $('#status').textContent=d.error;job=d.id;historyPage=1;$('#run').disabled=true;poll();refreshHistory()};$('#cancel').onclick=async()=>{await fetch('/momask-generator/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:job})});poll()};$('#resultDirection').onchange=()=>{const dir=$('#resultDirection').value;frames=frames.map((_,i)=>`/momask-generator/jobs/${job}/result/${dir}/openpose-${String(i+1).padStart(4,'0')}.png`);index=0;draw()};$('#play').onclick=()=>{if(timer)stop();else{timer=setInterval(()=>{index=(index+1)%frames.length;draw()},250);$('#play').textContent='정지'}};$('#refresh').onclick=()=>{if(job)poll();refreshHistory()};$('#clear').onclick=async()=>{if(confirm('누적 이력만 초기화합니다.')){await fetch('/momask-generator/history/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'reset'})});historyPage=1;refreshHistory()}};refreshHistory();
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
   if h.command=='GET' and path in (self.route,self.route+'/'): self.send(h,200,PAGE.encode(),'text/html; charset=utf-8');return True
   if h.command=='GET' and path==self.route+'/history':
    page=max(1,int(query.get('page',['1'])[0]));page_size=8;records=self.history();total=len(records);page_count=max(1,(total+page_size-1)//page_size);page=min(page,page_count);start=(page-1)*page_size
    self.send(h,200,{'records':records[start:start+page_size],'total':total,'page':page,'page_size':page_size,'page_count':page_count,'running':self.process is not None and self.process.poll() is None});return True
   match=re.fullmatch(self.route+r'/jobs/([0-9a-f_-]+)(?:/result/(down_left|down_right|up_left|up_right)/(openpose-\d{4}\.png))?',path)
   if h.command=='GET' and match:
    root=JOB_ROOT/match[1]
    if match[2]: self.send(h,200,(root/'result'/match[2]/match[3]).read_bytes(),'image/png');return True
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
