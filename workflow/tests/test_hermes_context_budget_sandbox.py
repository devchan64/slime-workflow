"""격리 Hermes 런타임에서 기준 초과 후 추가 요약 경로를 확인한다."""
import json, os, shutil, socket, subprocess, tempfile, threading, unittest
from http.server import HTTPServer
from pathlib import Path
from workflow.domains.hermes_agent.worker import serve_worker_model_proxy
from workflow.tests.test_hermes_context_sandbox import MockModel, RUNTIME, DOMAIN

class BudgetModel(MockModel):
    counts = None
    summaries = 0
    def do_POST(self):
        if self.path == '/tokenize':
            self.rfile.read(int(self.headers['Content-Length']))
            size = next(type(self).counts)
            body = json.dumps({'tokens':[0]*size}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            if self.path == '/v1/chat/completions': type(self).summaries += 1
            super().do_POST()

class BudgetSandboxTest(unittest.TestCase):
    def test_real_runtime_second_summary_is_bounded(self):
        if not shutil.which('bwrap') or not (RUNTIME / '.venv/bin/python').is_file(): self.skipTest('런타임 또는 bubblewrap 없음')
        BudgetModel.counts=iter([100000,70000,20000,40000]); BudgetModel.summaries=0
        with tempfile.TemporaryDirectory(prefix='hermes-budget-') as tmp:
            root=Path(tmp); (root/'workspace').mkdir(); exchange=root/'exchange'; exchange.mkdir()
            messages=[{'role':'user' if n%2==0 else 'assistant','content':('task %s '%n)*300} for n in range(20)]
            (exchange/'input.json').write_text(json.dumps({'messages':messages,'automatic':True,'force':True}))
            (root/'query.txt').write_text('follow-up task')
            server=HTTPServer(('127.0.0.1',0),BudgetModel); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with socket.socket(socket.AF_UNIX) as listener:
                    listener.bind(str(root/'model.sock'));listener.listen();threading.Thread(target=serve_worker_model_proxy,args=(listener,server.server_port),daemon=True).start()
                    cmd=['bwrap','--die-with-parent','--unshare-all','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/etc/ssl','/etc/ssl','--tmpfs','/tmp','--dir','/control','--ro-bind',str(RUNTIME),'/runtime','--ro-bind',str(root/'workspace'),'/workspace','--ro-bind',str(root/'model.sock'),'/control/model-proxy.sock','--ro-bind',str(root/'query.txt'),'/control/query.txt','--ro-bind',str(DOMAIN/'sandbox_client.py'),'/control/client.py','--ro-bind',str(DOMAIN/'context_runtime.py'),'/control/context_runtime.py','--bind',str(exchange),'/control/context','--proc','/proc','--dev','/dev','--','/runtime/.venv/bin/python','/control/client.py','--context-only']
                    completed=subprocess.run(cmd,env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp','LANG':'C.UTF-8','PYTHONPATH':'/runtime','HERMES_HOME':'/tmp/hermes-home','TERMINAL_CWD':'/workspace'},capture_output=True,text=True,timeout=120)
                    if completed.returncode and ('No permissions to create a new namespace' in completed.stderr or 'Creating new namespace failed' in completed.stderr): self.skipTest('네임스페이스 불가')
                    self.assertEqual(completed.returncode,0,completed.stderr[-3000:])
                    result=json.loads((exchange/'result.json').read_text())
                    self.assertEqual(result['state'],'compressed');self.assertEqual(result['tokens_after'],40000);self.assertLessEqual(result['tokens_after'],result['threshold']);self.assertEqual(BudgetModel.summaries,2)
                    self.assertEqual(result['messages'][-2:],[dict(m,_compaction_tail=True) for m in messages[-2:]])
            finally: server.shutdown();server.server_close();thread.join(timeout=5)
