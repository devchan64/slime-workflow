import tempfile
import unittest
import json
import socket
import threading
from pathlib import Path
from unittest.mock import Mock,patch

from workflow.domains.hermes_agent.gpu_handoff_operations import preview_handoff,approve_handoff
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore


class QuestionHandoffTests(unittest.TestCase):
    def test_bound_question_approval_schedules_gpu_handoff(self):
        from workflow.domains.hermes_agent.minimax_form_bridge import handle_form_connection
        session,form,job='a'*32,'b'*32,'2026-11-24_22-01-26-b482d868'
        resident='resident_123'
        request={'action':'generate','prompt':'a house','images':[],'width':512,'height':512,'steps':6,'seed':42}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);forms=MiniMaxFormStore(root/'minimax-forms.sqlite3');forms.create(session,form,'minimax-h3-image',job,request)
            store=GpuHandoffStore(root/'handoffs');sessions=Mock()
            inspector=lambda *_:{'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            reservations=lambda:{'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]}
            options={'session_store':sessions,'resident_inspector':inspector,'reservation_snapshot':reservations}
            def gateway(command,payload):
                if command=='hermes-minimax-form-read':return forms.read(payload['session_id'],payload['form_id'])
                if command=='hermes-minimax-form-submit':return {'state':'accepted','job_id':'2026-11-25_23-01-01-12345678'}
                if command=='hermes-gpu-handoff-preview':return preview_handoff(payload['session_id'],payload['resident_id'],payload['service'],payload['request'],**options)
                if command=='hermes-gpu-handoff-approve':return approve_handoff(**payload,store=store,resident_conflict_check=lambda _:None,**options)
                raise AssertionError(command)
            def exchange(prompt,payload):
                server,client=socket.socketpair();thread=threading.Thread(target=handle_form_connection,args=(server,session,prompt,gateway));thread.start()
                with client:
                    client.settimeout(2);client.sendall(json.dumps(payload).encode()+b'\n');value=json.loads(client.recv(4096))
                thread.join(2);self.assertFalse(thread.is_alive());return value
            approval=(f'질문 작업 {job}에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 1\n'
                      '1. 이 폼으로 생성할까요?\n답변: 승인')
            with patch('workflow.domains.hermes_agent.gpu_handoff_minimax_image.HermesSessionStore',return_value=Mock(session_storage_root=root)):
                result=exchange(approval,{'operation':'submit','form_id':form,'revision':1})
                self.assertEqual(result['state'],'accepted')
                self.assertEqual(result['job_id'],'2026-11-25_23-01-01-12345678')
                self.assertEqual(store.list_active_ids(),[])

    def test_review_binds_actual_form_revision_and_explicit_gpu_consent(self):
        session,form='a'*32,'b'*32
        request={'action':'generate','prompt':'a house','images':[],'width':512,'height':512,'steps':6,'seed':42}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);forms=MiniMaxFormStore(root/'minimax-forms.sqlite3')
            forms.create(session,form,'minimax-h3-image','2026-11-24_22-01-26-b482d868',request)
            sessions=Mock();resident=lambda *_:{'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            reservations=lambda:{'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]}
            options={'session_store':sessions,'resident_inspector':resident,'reservation_snapshot':reservations}
            target={'form_id':form,'revision':1,'request':request}
            with patch('workflow.domains.hermes_agent.gpu_handoff_minimax_image.HermesSessionStore',return_value=Mock(session_storage_root=root)):
                review=preview_handoff(session,'resident_123','minimax-h3-image',target,**options)
                store=GpuHandoffStore(root/'handoffs')
                with self.assertRaises(ValueError):
                    approve_handoff('request_123',session,'resident_123','minimax-h3-image',target,review['review_hash'],confirmed=False,store=store,**options)
                with self.assertRaises(ValueError):
                    approve_handoff('request_123',session,'resident_123','minimax-h3-image',{**target,'revision':2},review['review_hash'],confirmed=True,store=store,**options)
                forms.save(session,form,1,{**request,'seed':43})
                with self.assertRaises(ValueError):
                    approve_handoff('request_123',session,'resident_123','minimax-h3-image',target,review['review_hash'],confirmed=True,store=store,resident_conflict_check=lambda _:None,**options)
                self.assertIsNone(store.read('request_123'))
                updated={'form_id':form,'revision':2,'request':{**request,'seed':43}}
                fresh=preview_handoff(session,'resident_123','minimax-h3-image',updated,**options)
                result=approve_handoff('request_123',session,'resident_123','minimax-h3-image',updated,fresh['review_hash'],confirmed=True,store=store,resident_conflict_check=lambda _:None,**options)
                self.assertEqual(result['state'],'approved')
                self.assertEqual(store.read('request_123')['target_request'],updated)
