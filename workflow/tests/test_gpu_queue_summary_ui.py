"""GPU 대기열 요약의 첫 조회 상태를 렌더링한다."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch


class GpuQueueSummaryUiTests(unittest.TestCase):
    def test_gateway_response_matches_summary_contract_without_gpu_access(self):
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        from workflow.gateway_server import create_gateway_request_handler
        root = Path(__file__).resolve().parents[2]
        server = ThreadingHTTPServer(('127.0.0.1', 0), create_gateway_request_handler(lambda handler: False))
        server.emit_gateway_trace = lambda *args: None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch('workflow.common.gpu_status.read_gpu_status', return_value={'status':'unavailable'}) as gpu, \
                 patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs', return_value={'jobs':[{'id':'job-1','service':'kimodo'}]}) as queue:
                with urlopen(f'http://127.0.0.1:{server.server_port}/management/gpu-queue', timeout=5) as response:
                    data = json.load(response)
                gpu.assert_called_once_with()
                queue.assert_called_once_with(observation_limits=True)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
        script = """import assert from 'node:assert/strict';
          import {formatGpuQueueSummary} from './gui/gpuQueueSummary.mjs';
          let data=''; for await(const part of process.stdin)data+=part;
          assert.deepEqual(formatGpuQueueSummary(JSON.parse(data)),
            {text:'GPU 상태 확인 불가 · 대기 작업 1건',unavailable:true});"""
        subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(data),
                       cwd=root, check=True, capture_output=True, text=True)

    def test_initial_loading_keeps_refresh_control(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'gpu-summary.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'GpuQueueSummary.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const React=require('react'),server=require('react-dom/server');
              const Summary=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Summary)));"""
            html = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True,
                                           env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('GPU 대기열 조회 중', html)
        self.assertIn('aria-disabled="true"', html)
        self.assertIn('GPU 상태 조회 중', html)


if __name__ == '__main__':
    unittest.main()
