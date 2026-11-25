import json
import socket
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.domains.hermes_agent.minimax_form_bridge import handle_form_connection


class MiniMaxFormBridgeTests(unittest.TestCase):
    def test_handoff_operation_requires_current_turn_consent(self):
        session,form,job='a'*32,'b'*32,'2026-11-25_22-30-44-0d6a944f'
        resident,review='resident_123','d'*64
        payload={'operation':'confirm-handoff','form_id':form,'revision':1,'resident_id':resident,'review_hash':review}
        prompt=(f'질문 작업 {job}에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 1\n'
                f'상주 모델 ID: {resident}\nGPU 양도 검토: {review}\n1. GPU 양도할까요?\n답변: GPU 양도에 동의')
        form_data={'session_id':session,'form_id':form,'revision':1,'state':'editing','service':'minimax-h3-image',
                   'source_job_id':job,'request':{'prompt':'집','images':[]}}
        def gateway(command,data):
            if command=='hermes-minimax-form-read':return form_data
            if command=='hermes-resident-status':return {'resident_id':resident,'resident':{'state':'ready'}}
            if command=='hermes-gpu-handoff-approve':return {'id':data['request_id'],'state':'approved','revision':1}
            raise AssertionError(command)
        dispatch=Mock(side_effect=gateway)
        def exchange(text):
            server,client=socket.socketpair()
            thread=threading.Thread(target=handle_form_connection,args=(server,session,text,dispatch));thread.start()
            with client:
                client.settimeout(2);client.sendall(json.dumps(payload).encode()+b'\n');result=json.loads(client.recv(4096))
            thread.join(2);self.assertFalse(thread.is_alive());return result
        self.assertEqual(exchange(prompt)['state'],'approved')
        before=dispatch.call_count
        self.assertIn('error',exchange(prompt.replace('답변: GPU 양도에 동의','답변: 거절')))
        self.assertEqual(dispatch.call_count,before)

    def test_submit_uses_pinned_form_and_duplicate_receipt(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
        from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore
        session, form = 'a'*32, 'b'*32
        source, generated = '2026-11-24_22-01-26-b482d868', '2026-11-24_22-23-17-2a551ada'
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory)/'forms.sqlite3')
            receipts = HermesDelegationStore(Path(directory)/'receipts')
            forms.create(session,form,'minimax-h3-image',source,{'prompt':'성당','seed':42})
            manager, generator, sessions = Mock(), Mock(return_value={'id':generated}), Mock()
            def gateway(command, payload):
                return execute_minimax_form_command(command,payload,sessions=sessions,read_job=Mock(),dispatch=generator,forms=forms,receipts=receipts)
            def submit():
                server, client = socket.socketpair()
                thread = threading.Thread(target=handle_form_connection,args=(server,session,'이 폼을 대기열에 접수해줘',gateway))
                thread.start()
                with client:
                    client.settimeout(2)
                    client.sendall(json.dumps({'operation':'submit','form_id':form,'revision':1}).encode()+b'\n')
                    result=json.loads(client.recv(4096))
                thread.join(2)
                self.assertFalse(thread.is_alive())
                return result
            with patch('workflow.domains.hermes_agent.minimax_form_commands.resolve_proposal',return_value=({},manager)), \
                 patch('workflow.domains.hermes_agent.minimax_submission.resolve_proposal',return_value=({},manager)):
                self.assertEqual(submit()['job_id'],generated)
                self.assertTrue(submit()['duplicate'])
            self.assertEqual(generator.call_count,1)
            self.assertEqual(forms.read(session,form)['state'],'accepted')
            self.assertEqual(generator.call_args.args[2]['prompt'],'성당')

    def test_request_is_bound_to_worker_session_and_user_turn(self):
        session, form = 'a'*32, 'b'*32
        dispatch = Mock(return_value={'form_id':form,'revision':2,'state':'editing'})
        def exchange(prompt, payload):
            server, client = socket.socketpair()
            thread = threading.Thread(target=handle_form_connection,args=(server,session,prompt,dispatch))
            thread.start()
            with client:
                client.settimeout(2)
                client.sendall(json.dumps(payload).encode()+b'\n')
                answer = json.loads(client.recv(4096))
            thread.join(2)
            self.assertFalse(thread.is_alive())
            return answer
        payload = {'form_id':form,'revision':1,'request':{'seed':42}}
        self.assertEqual(exchange('시드를 42로 변경해줘',payload)['revision'],2)
        self.assertEqual(dispatch.call_args.args[1]['session_id'],session)
        self.assertIn('error',exchange('결과를 보여줘',payload))
        self.assertIn('error',exchange('시드를 변경해줘',{**payload,'session_id':'c'*32}))
        self.assertEqual(dispatch.call_count,1)


if __name__ == '__main__': unittest.main()
