"""폐기된 Gradio heartbeat 경로가 재노출되지 않는지 확인한다."""
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from workflow.common.management_asgi import build_management_application


class ManagementHeartbeatBridgeTests(unittest.TestCase):
    def test_retired_heartbeat_websocket_is_rejected_for_all_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                for origin in ('http://localhost:8770','https://untrusted.example'):
                    with self.subTest(origin=origin),self.assertRaises(WebSocketDisconnect) as closed:
                        with client.websocket_connect('/management/frame/example/gradio_api/heartbeat-ws/session123',headers={'origin':origin}):
                            self.fail('폐기된 heartbeat를 열면 안 됩니다.')
                    self.assertEqual(closed.exception.code,1008)

    def test_current_live_refresh_interval(self):
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'live.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'LiveRefresh.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="const {LIVE_REFRESH_MS}=require(process.argv[1]);if(LIVE_REFRESH_MS!==30000)throw Error('refresh interval');"
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True)
