from pathlib import Path
from urllib.parse import urlsplit
import json, subprocess, threading, uuid
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'assets/motion-sheet/mannequin-walk-v6/inputs/attributes.json'
JOBS=ROOT/'.tmp/anny-attribute-renderer'
PAGE='''<!doctype html><meta charset="utf-8"><title>Anny 속성 렌더러</title><style>body{background:#101814;color:#e7f2e9;font:14px system-ui;padding:28px}main{max-width:900px;margin:auto}label{display:block;margin:12px 0}input{width:280px}img{max-width:48%;background:#000}pre{background:#07100b;padding:12px}</style><main><h1>Anny 속성 렌더러</h1><p>현재 사용 중인 Anny 기준 속성에서 값만 바꿔 프리뷰를 렌더합니다.</p><div id=f></div><p id=s>기준값 불러오는 중</p><section id=r></section></main><script>let timer;const f=document.querySelector('#f'),s=document.querySelector('#s'),r=document.querySelector('#r');const fields=[['age','나이',0,1],['weight','체중',0,1],['height','키',0,1],['torso-scale-horiz-incr','몸통 너비',-1,1],['torso-scale-depth-incr','몸통 깊이',-1,1],['measure-shoulder-dist-incr','어깨 너비',-1,1],['upperlegs-height-incr','다리 길이',-1,1]];let base;const values=()=>Object.fromEntries([...f.querySelectorAll('input')].map(x=>[x.name,+x.value]));async function render(){s.textContent='Anny 렌더 요청 중';let q=await fetch('/anny-attributes/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values())}),j=await q.json();if(!q.ok){s.textContent=j.error;return}let poll=async()=>{let a=await fetch('/anny-attributes/jobs/'+j.id),v=await a.json();s.textContent=v.status;if(v.status==='running')return setTimeout(poll,1000);if(v.status==='completed')r.innerHTML='<img src="/anny-attributes/jobs/'+j.id+'/front.png"><img src="/anny-attributes/jobs/'+j.id+'/side.png">'};poll()}fetch('/anny-attributes/base').then(x=>x.json()).then(x=>{base=x;for(const [n,l,min,max] of fields){let v=(x.phenotype_kwargs[n]??x.local_changes_kwargs[n]??0);f.insertAdjacentHTML('beforeend',`<label>${l} <input name="${n}" type=range min=${min} max=${max} step=.05 value=${v}><output>${v}</output></label>`)}f.oninput=e=>{e.target.nextElementSibling.textContent=e.target.value;clearTimeout(timer);timer=setTimeout(render,500)};s.textContent='기준값을 수정하면 자동으로 렌더합니다.'})</script>'''
class AnnyAttributeManager:
 def send(self,h,status,payload,ctype='application/json; charset=utf-8'):
  data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode();h.send_response(status);h.send_header('Content-Type',ctype);h.send_header('Content-Length',str(len(data)));h.end_headers();h.wfile.write(data)
 def handle(self,h):
  path=urlsplit(h.path).path
  if not path.startswith('/anny-attributes'): return False
  try:
   if h.command=='GET' and path=='/anny-attributes/':self.send(h,200,PAGE.encode(),'text/html; charset=utf-8');return True
   if h.command=='GET' and path=='/anny-attributes/base':self.send(h,200,json.loads(BASE.read_text()));return True
   if h.command=='GET' and path.startswith('/anny-attributes/jobs/'):
    parts=path.split('/');root=JOBS/parts[3]
    if len(parts)==4:self.send(h,200,json.loads((root/'status.json').read_text()));return True
    self.send(h,200,(root/parts[4]).read_bytes(),'image/png');return True
   if h.command!='POST' or path!='/anny-attributes/render':raise ValueError('요청 오류')
   changed=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
   if set(changed)-{'age','weight','height','torso-scale-horiz-incr','torso-scale-depth-incr','measure-shoulder-dist-incr','upperlegs-height-incr'}:raise ValueError('지원하지 않는 속성')
   attrs=json.loads(BASE.read_text());attrs['phenotype_kwargs'].update({k:v for k,v in changed.items() if k in attrs['phenotype_kwargs']});attrs['local_changes_kwargs'].update({k:v for k,v in changed.items() if k not in attrs['phenotype_kwargs']})
   ident=uuid.uuid4().hex[:8];root=JOBS/ident;root.mkdir(parents=True);(root/'attributes.json').write_text(json.dumps(attrs));(root/'status.json').write_text(json.dumps({'status':'running'}))
   def work():
    code=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(root/'attributes.json'),'--output-dir',str(root/'render')],stdout=(root/'worker.log').open('w'),stderr=subprocess.STDOUT).returncode
    for name in ('front.png','side.png'):
     source=root/'render'/name
     if source.exists():source.replace(root/name)
    (root/'status.json').write_text(json.dumps({'status':'completed' if code==0 else 'failed'}))
   threading.Thread(target=work,daemon=True).start();self.send(h,202,{'id':ident});return True
  except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
