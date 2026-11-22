import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from workflow.common.history_summaries import handle_history_summaries_request, read_history_summary, video_image_attempt


class HistorySummariesTests(unittest.TestCase):
    def test_audio_summary_endpoint_exposes_only_confirmed_output(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);identifier='2026-11-17_08-17-15-14925ca2';job=root/identifier;job.mkdir();attempt='a'*32
            (job/'request.json').write_text(json.dumps({'prompt':'private','duration_seconds':12.5,'seed':7}))
            (job/'status.json').write_text('{"status":"completed"}');(job/'result.json').write_text(json.dumps({'attempt':attempt}))
            audio=job/'attempts'/attempt/'music.wav';audio.parent.mkdir(parents=True);audio.write_bytes(b'RIFF')
            payload=json.dumps({'service':'music-heartmula','ids':[identifier]}).encode();statuses=[]
            handler=SimpleNamespace(path='/management/history-summaries',server=SimpleNamespace(server_port=8770),headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(payload))},rfile=io.BytesIO(payload),wfile=io.BytesIO(),send_response=statuses.append,send_header=lambda *args:None,end_headers=lambda:None)
            routes={'/music-heartmula':(root,lambda id:root/id)}
            handle_history_summaries_request(handler,routes)
            summary=json.loads(handler.wfile.getvalue())['summaries'][identifier]
            self.assertEqual(summary,{'seed':7,'duration_seconds':12.5,'audio_available':True})
            repository=Path(__file__).resolve().parents[2]
            script="""import {historyInputSummary} from './gui/historyInputSummary.mjs';
              const values=historyInputSummary(JSON.parse(process.argv[1]));
              if(!values.includes('길이 12.5초') || !values.includes('WAV 오디오 결과'))throw Error(JSON.stringify(values));"""
            result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(summary)],cwd=repository,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            audio.unlink();audio.symlink_to(job/'request.json');handler.rfile=io.BytesIO(payload);handler.wfile=io.BytesIO()
            handle_history_summaries_request(handler,routes)
            self.assertFalse(json.loads(handler.wfile.getvalue())['summaries'][identifier]['audio_available'])

    def test_video_preview_uses_only_valid_saved_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); attempt='a'*32; folder=root/'attempts'/attempt; folder.mkdir(parents=True)
            (root/'result.json').write_text(json.dumps({'attempt':attempt}))
            (folder/'output-000.png').write_bytes(b'png')
            self.assertEqual(video_image_attempt(root),attempt)
            (folder/'output-000.png').unlink(); (folder/'output-000.png').symlink_to(root/'result.json')
            self.assertIsNone(video_image_attempt(root))
            (root/'result.json').write_text(json.dumps({'attempt':'../outside'}))
            self.assertIsNone(video_image_attempt(root))

    def test_running_preview_follows_current_attempt_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, current = 'a' * 32, 'b' * 32
            for attempt in (old, current):
                folder = root / 'attempts' / attempt
                folder.mkdir(parents=True)
                (folder / 'output-000.png').write_bytes(b'png')
            (root / 'result.json').write_text(json.dumps({'attempt': old}))
            status = root / 'status.json'
            status.write_text('{"status":"running"}')
            self.assertIsNone(video_image_attempt(root))
            pointer = root / 'current-attempt.json'
            pointer.write_text(json.dumps({'id': current}))
            self.assertEqual(video_image_attempt(root), current)
            os.utime(pointer, ns=(1, 1))
            self.assertIsNone(video_image_attempt(root))
            status.write_text('{"status":"queued"}')
            self.assertIsNone(video_image_attempt(root))

    def test_rejects_oversized_and_malformed_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'request.json').write_bytes(b' ' * 1048577)
            with self.assertRaises(ValueError): read_history_summary(root)
            (root/'request.json').write_text('[]')
            with self.assertRaises(ValueError): read_history_summary(root)

    def test_bounded_whitelist_and_invalid_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); identifier='2026-11-17_08-17-15-14925ca2'; job=root/identifier; job.mkdir()
            (job/'status.json').write_text('{}')
            (job/'request.json').write_text(json.dumps({'tag':'예시','width':512,'height':512,'seed':0,'prompt':'비공개','frames':True}))
            payload=json.dumps({'service':'flux-expression','ids':[identifier]}).encode(); statuses=[]
            handler=SimpleNamespace(path='/management/history-summaries',server=SimpleNamespace(server_port=8770),headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(payload))},rfile=io.BytesIO(payload),wfile=io.BytesIO(),send_response=statuses.append,send_header=lambda *args:None,end_headers=lambda:None)
            routes={'/flux-expression-generator':(root,lambda id:root/id)}
            self.assertTrue(handle_history_summaries_request(handler,routes))
            self.assertEqual(statuses[-1],200)
            self.assertEqual(json.loads(handler.wfile.getvalue())['summaries'][identifier],{'tag':'예시','width':512,'height':512,'seed':0,'image_available':False})
            (job/'result.png').write_bytes(b'png')
            handler.rfile=io.BytesIO(payload); handler.wfile=io.BytesIO()
            handle_history_summaries_request(handler,routes)
            self.assertTrue(json.loads(handler.wfile.getvalue())['summaries'][identifier]['image_available'])
            (job/'request.json').unlink(); (job/'request.json').symlink_to(root/'outside.json'); (root/'outside.json').write_text('{}')
            handler.rfile=io.BytesIO(payload); handler.wfile=io.BytesIO()
            handle_history_summaries_request(handler,routes)
            self.assertEqual(json.loads(handler.wfile.getvalue())['summaries'],{})
            handler.rfile=io.BytesIO(payload); handler.wfile=io.BytesIO(); handler.headers['Origin']='https://example.com'
            handle_history_summaries_request(handler,routes)
            self.assertEqual(statuses[-1],400)
