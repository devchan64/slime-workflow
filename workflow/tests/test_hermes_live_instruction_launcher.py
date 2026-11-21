import json
import socket
import sys
import threading
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent import live_instruction_runtime


class Runtime:
    def submit(self, request_id, mode, text):
        return {'request_id':request_id, 'state':'accepted'}


class LauncherTests(unittest.TestCase):
    def test_control_socket_returns_receipt(self):
        with patch.dict(sys.modules, {'live_instruction_runtime':live_instruction_runtime}):
            from workflow.domains.hermes_agent.live_instruction_launcher import serve
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as root:
                listener=socket.socket(socket.AF_UNIX);path=str(Path(root)/'agent.sock')
                listener.bind(path);listener.listen(1)
                threading.Thread(target=serve,args=(Runtime(),listener),daemon=True).start()
                with socket.socket(socket.AF_UNIX) as client:
                    client.connect(path)
                    client.sendall(json.dumps({'request_id':'request_01','mode':'steer','text':'추가'}).encode()+b'\n')
                    self.assertEqual(json.loads(client.recv(4096))['state'],'accepted')
                listener.close()
