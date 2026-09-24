from pathlib import Path
from urllib.parse import urlsplit
import json, subprocess, threading, uuid, re
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'assets/motion-sheet/mannequin-walk-v6/inputs/attributes.json'
JOBS=ROOT/'.tmp/anny-attribute-renderer'
PAGE=Path(__file__).with_name('anny-attributes.html').read_text()
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
    parts=path.split('/')
    if len(parts) not in (4,5) or not re.fullmatch(r'[0-9a-f]{8}',parts[3]):raise ValueError('잘못된 작업 경로')
    if len(parts)==5 and parts[4] not in {'front.png','side.png'}:raise ValueError('허용하지 않는 결과 파일')
    root=JOBS/parts[3]
    if len(parts)==4:
     state=json.loads((root/'status.json').read_text());state['log']=(root/'worker.log').read_text(errors='replace')[-2000:] if (root/'worker.log').exists() else '';self.send(h,200,state);return True
    self.send(h,200,(root/parts[4]).read_bytes(),'image/png');return True
   if h.command!='POST' or path!='/anny-attributes/render':raise ValueError('요청 오류')
   if h.headers.get('Origin')!=f'http://127.0.0.1:{h.server.server_port}':raise ValueError('허용하지 않는 요청 출처')
   changed=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
   if not isinstance(changed,dict):raise ValueError('속성 객체가 필요합니다.')
   if set(changed)-{'age','weight','height','torso-scale-horiz-incr','torso-scale-depth-incr','measure-shoulder-dist-incr','upperlegs-height-incr','lowerlegs-height-incr'}:raise ValueError('지원하지 않는 속성')
   if not isinstance(changed,dict):raise ValueError('속성 객체가 필요합니다.')
   for attribute_key_name,attribute_numeric_value in changed.items():
    attribute_minimum_value=0 if attribute_key_name in {'age','weight','height'} else -1
    if type(attribute_numeric_value) not in (int,float) or not attribute_minimum_value<=attribute_numeric_value<=1:raise ValueError('속성 범위 오류')
   attrs=json.loads(BASE.read_text());attrs['phenotype_kwargs'].update({k:v for k,v in changed.items() if k in attrs['phenotype_kwargs']});attrs['local_changes_kwargs'].update({k:v for k,v in changed.items() if k not in attrs['phenotype_kwargs']})
   ident=uuid.uuid4().hex[:8];root=JOBS/ident;root.mkdir(parents=True);(root/'attributes.json').write_text(json.dumps(attrs));(root/'status.json').write_text(json.dumps({'status':'running'}))
   def work():
    code=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'generators/animation/render_anny_attribute_preview.py'),'--attributes',str(root/'attributes.json'),'--output-dir',str(root/'render')],stdout=(root/'worker.log').open('w'),stderr=subprocess.STDOUT).returncode
    for name in ('front.png','side.png'):
     source=root/'render'/name
     if source.exists():source.replace(root/name)
    (root/'status.json').write_text(json.dumps({'status':'completed' if code==0 else 'failed','exit_code':code}))
   threading.Thread(target=work,daemon=True).start();self.send(h,202,{'id':ident});return True
  except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as e:self.send(h,400,{'error':str(e)});return True
