"""공용 대기열의 초기 조회 표시를 서버 렌더로 확인한다."""
from pathlib import Path
import os
import json
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class UnifiedQueueUiTests(unittest.TestCase):
    def test_observed_isolated_queue_matches_ui_validation(self):
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent.chat_queue_store import enqueue
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.unified_queue import observe_unified_queue
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = HermesSessionStore(root/'sessions')
            session = 'a'*32
            store.create_session_record(session)
            enqueue(store, session, 'request_123', 'isolated')
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', root/'missing-queue'):
                snapshot = observe_unified_queue(store, session)
            self.assertEqual(len(snapshot['entries']), 1)
            bundle = root/'queue.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'UnifiedQueueOverview.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const assert=require('node:assert/strict');
              const {validSnapshot}=require(process.argv[1]); let raw='';
              process.stdin.on('data',part=>raw+=part);process.stdin.on('end',()=>{
                const snapshot=JSON.parse(raw),session=snapshot.session_id;
                assert.equal(validSnapshot(snapshot,session),true);
                assert.equal(validSnapshot(snapshot,'b'.repeat(32)),false);
                assert.equal(validSnapshot({...snapshot,entries:[{...snapshot.entries[0],priority:'bad'}]},session),false);
              });"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, input=json.dumps(snapshot),
                           check=True, capture_output=True, text=True)

    def test_initial_read_is_not_rendered_as_empty_queue(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'queue.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'UnifiedQueueOverview.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const React=require('react'), server=require('react-dom/server');
              const Queue=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Queue,{session:'session-1',call:()=>{throw Error('render should not request');}})));"""
            html = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True,
                                           env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('작업 일정을 조회하고 있습니다.', html)
        self.assertIn('aria-disabled="true"', html)
        status = re.search(r'<p id="([^"]+)" role="status">작업 일정을 조회하고 있습니다\.</p>', html)
        self.assertIsNotNone(status)
        self.assertIn(f'aria-describedby="{status.group(1)}"', html)
        self.assertNotIn('대기 중인 요청이 없습니다', html)


if __name__ == '__main__':
    unittest.main()
