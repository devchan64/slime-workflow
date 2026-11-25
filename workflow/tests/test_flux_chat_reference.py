import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.domains.hermes_agent import flux_chat_submission as chat


class ChatReferenceTests(unittest.TestCase):
    def test_previous_user_path_must_match_proposal_and_supports_host_path(self):
        path='baseline/player/default/480p/default-body-front-right-480p-v1.png'
        detail={'request':{'context':{'messages':[{'role':'user','content':f'{chat.WORKFLOW_ROOT}/{path}를 참조해줘'}]}}}
        self.assertEqual(chat.proposal_reference_paths({'text':'프롬프트는 한글로 작성한다'},detail,f'참조: /workspace/{path}'),[path])
        with self.assertRaisesRegex(ValueError,'일치하지 않습니다'):
            chat.proposal_reference_paths({'text':'프롬프트 수정'},detail,'참조: /workspace/baseline/other.png')
        self.assertEqual(chat.proposal_reference_paths({'text':'/workspace/baseline/a.png'},detail,''),['baseline/a.png'])
        with self.assertRaises(ValueError): chat._reference_paths('/workspace/baseline/../secret.png')

    def test_missing_required_reference_stops_before_gpu_or_submission(self):
        session='a'*32;job='2026-11-25_21-50-21-802b8a89'
        session_store=Mock();session_store.read_session_record.return_value={'messages':[{'job_id':job,'text':'프롬프트를 한글로'}]}
        manager=Mock();manager.hermes_session_root=None
        manager.read_context_job.return_value={'final_response':'HERMES_IMAGE_PROPOSAL','request':{'context':{'messages':[]}}}
        proposal={'service':'minimax-h3-image','prompt':'참조 이미지와 동일한 캐릭터','width':832,'height':480,'seed':42}
        def command(name,payload):
            if name=='hermes-flux-proposal':return {'proposal':proposal}
            if name=='hermes-minimax-form-list':return {'forms':[]}
            if name=='hermes-minimax-form-create':return {'request':payload['request'],'revision':1}
            raise AssertionError('unexpected command '+name)
        manager.execute_hermes_command.side_effect=command
        with tempfile.TemporaryDirectory() as directory, patch.object(chat,'HermesSessionStore',return_value=session_store), \
             patch.object(chat,'HermesDelegationStore') as receipts, patch.object(chat,'GpuHandoffStore') as handoffs:
            manager.resolve_hermes_job_path.return_value=Path(directory)
            receipts.return_value.read_service_delegation.return_value={'state':'not_found'}
            handoffs.return_value.read.return_value=None
            with self.assertRaisesRegex(ValueError,'참조 PNG를 첨부'):
                chat.submit_chat_flux(manager,session,'생성해')
        self.assertTrue(chat.requires_reference('reference image with sword'))
        self.assertFalse(chat.requires_reference('참조 이미지 없이 생성'))
        self.assertFalse(chat.requires_reference('without reference image'))

    def test_reference_is_resolved_from_snapshot_and_saved_before_review(self):
        session='a'*32;job='2026-11-25_21-50-21-802b8a89';path='baseline/player/default/480p/body.png'
        session_store=Mock();session_store.read_session_record.return_value={'messages':[{'job_id':job,'text':'프롬프트는 한글로'}]}
        manager=Mock();manager.hermes_session_root=None
        manager.read_context_job.return_value={'final_response':f'HERMES_IMAGE_PROPOSAL\n참조: /workspace/{path}',
            'request':{'context':{'messages':[{'role':'user','content':f'{chat.WORKFLOW_ROOT}/{path}를 참조'}]}}}
        proposal={'service':'minimax-h3-image','prompt':'참조 이미지와 동일','width':832,'height':480,'seed':42}
        saved={'request':{'action':'generate','prompt':proposal['prompt'],'images':[],'width':832,'height':480,'steps':6,'seed':42},'revision':1,'state':'editing'}
        def command(name,payload):
            if name=='hermes-flux-proposal':return {'proposal':proposal}
            if name=='hermes-minimax-form-list':return {'forms':[{'form_id':form_id}]}
            if name=='hermes-minimax-form-read':return saved
            if name=='hermes-minimax-form-save':
                saved.update(request=payload['request'],revision=2);return saved
            if name=='hermes-resident-status':return {'resident':{'state':'ready'},'resident_id':'resident_123'}
            if name=='hermes-gpu-handoff-preview':return {'review_hash':'b'*64}
            raise AssertionError('unexpected command '+name)
        from workflow.domains.hermes_agent.flux_reports import proposal_request_id
        import hashlib
        rid=proposal_request_id(session,job,'minimax-h3-image');form_id=hashlib.sha256(('minimax-form:'+rid).encode()).hexdigest()[:32]
        manager.execute_hermes_command.side_effect=command
        with tempfile.TemporaryDirectory() as directory, patch.object(chat,'HermesSessionStore',return_value=session_store), \
             patch.object(chat,'HermesDelegationStore') as receipts, patch.object(chat,'GpuHandoffStore') as handoffs, \
             patch.object(chat.subprocess,'check_output',return_value=b'\x89PNG\r\n\x1a\nexample') as read:
            root=Path(directory);(root/'workspace').mkdir();(root/'baseline.json').write_text(json.dumps({'baseline_commit':'c'*40}))
            manager.resolve_hermes_job_path.return_value=root
            receipts.return_value.read_service_delegation.return_value={'state':'not_found'};handoffs.return_value.read.return_value=None
            self.assertEqual(chat.submit_chat_flux(manager,session,'생성해')['state'],'awaiting_consent')
            self.assertEqual(read.call_args.args[0][-1],'c'*40+':'+path)
            self.assertEqual(len(saved['request']['images']),1)
            self.assertIn('참조 1장',session_store.append_result_notice.call_args.args[2])
