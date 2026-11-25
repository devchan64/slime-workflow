"""양도 이력의 첫 조회 상태를 표시한다."""
import os
import json
import hashlib
import re
from pathlib import Path
import subprocess
import tempfile
import unittest


class HandoffHistoryUiTests(unittest.TestCase):
    def test_isolated_store_history_matches_ui_contract(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            payload = {'prompt':'isolated'}
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            session = 'a'*32
            store.approve('request_123', session, 'flux-image', hashlib.sha256(encoded).hexdigest(),
                          target_request=payload, resident_id='resident_123', confirmed=True)
            records = store.list_session_records(session)
            self.assertEqual(len(records),1)
            self.assertNotIn('target_request', records[0])
            script = """import assert from 'node:assert/strict';
              import {readHandoffHistoryResult} from './gui/handoffHistoryResult.mjs';
              let raw='';for await(const part of process.stdin)raw+=part;
              const result=JSON.parse(raw);assert.equal(readHandoffHistoryResult(result,result.session_id,0,0).length,1);
              assert.throws(()=>readHandoffHistoryResult(result,result.session_id,0,1),/변경/);"""
            subprocess.run(['node','--input-type=module','-e',script],
                           input=json.dumps({'session_id':session,'handoffs':records}),cwd=root,
                           text=True,check=True,capture_output=True)

    def test_initial_loading_is_not_empty_history(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'history.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'GpuHandoffHistory.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const React=require('react'),server=require('react-dom/server');
              const Page=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Page,{session:'session'})));"""
            html = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True,
                                           env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('GPU 양도 이력을 불러오는 중', html)
        self.assertIn('aria-disabled="true"', html)
        loading_id = re.search(r'<p id="([^"]+)" role="status">GPU 양도 이력을 불러오는 중', html)
        self.assertIsNotNone(loading_id)
        self.assertIn(f'aria-describedby="{loading_id.group(1)}"', html)
        self.assertNotIn('양도 기록이 없습니다', html)


if __name__ == '__main__':
    unittest.main()
