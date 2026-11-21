import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent import live_instruction_runtime


class FakeAgent:
    def __init__(self): self.calls=[]
    def _persist_session(self, messages): pass
    def steer(self, text, ticket=None): self.calls.append(text); return True
    def withdraw_steer(self, ticket): return True
    def run_conversation(self):
        self._persist_session([{'role':'user','content':self.calls[0]}])
        return {'messages':[{'role':'user','content':self.calls[0]}]}


class ManagedWorkerAdapterTests(unittest.TestCase):
    def test_managed_agent_receives_and_records_instruction(self):
        root=Path(__file__).resolve().parents[1]/'domains/hermes_agent'
        with patch.dict(sys.modules, {'live_instruction_runtime':live_instruction_runtime}):
            spec=importlib.util.spec_from_file_location('live_instruction_launcher',root/'live_instruction_launcher.py')
            launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
            with patch.dict(sys.modules, {'live_instruction_launcher':launcher}):
                spec=importlib.util.spec_from_file_location('worker_adapter_test',root/'live_instruction_worker_adapter.py')
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                with tempfile.TemporaryDirectory() as directory:
                    module.SOCKET=Path(directory)/'agent.sock';module.RECEIPT=Path(directory)/'settled.json'
                    agent=FakeAgent();module.install_on_agent(agent)
                    with socket.socket(socket.AF_UNIX) as client:
                        client.connect(str(module.SOCKET))
                        client.sendall(json.dumps({'request_id':'request_01','mode':'steer','text':'추가'}).encode()+b'\n')
                        self.assertEqual(json.loads(client.recv(4096))['state'],'accepted')
                    agent.run_conversation()
                    self.assertEqual(json.loads(module.RECEIPT.read_text())[0]['state'],'applied')
