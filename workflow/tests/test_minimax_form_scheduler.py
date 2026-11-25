import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.domains.hermes_agent.minimax_form_scheduler import advance_form_marker


class MiniMaxFormSchedulerTests(unittest.TestCase):
    def test_completed_video_proposal_prepares_reference_awaiting_form(self):
        from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
        from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, job = 'a'*32, '2026-11-24_22-01-26-b482d868'
            sessions = HermesSessionStore(root/'sessions')
            sessions.create_session_record(session)
            sessions.append_session_request(session, 'original_request', '첫 이미지로 영상 만들어줘')
            sessions.attach_session_job(session, 'original_request', job)
            marker = root/job/'minimax-form-pending.json'
            marker.parent.mkdir()
            marker.write_text(json.dumps({'session_id':session,'job_id':job}))
            proposal = {'service':'wan22-i2v','mode':'first_frame','prompt':'walk','explicit_service':False}
            detail = {'status':{'status':'completed'}, 'final_response_truncated':False,
                      'request':{'prompt':'첫 이미지로 영상 만들어줘','minimax_preferred':True},
                      'final_response':'HERMES_VIDEO_PROPOSAL\n'+json.dumps(proposal)+'\nEND_HERMES_VIDEO_PROPOSAL'}
            forms, receipts = MiniMaxFormStore(root/'forms.sqlite3'), HermesDelegationStore(root/'receipts')
            generate = Mock()
            def dispatch(command, payload):
                if command == 'hermes-detail': return detail
                return execute_minimax_form_command(command, payload, sessions=sessions, read_job=lambda _:detail,
                    dispatch=generate, forms=forms, receipts=receipts)
            self.assertEqual(advance_form_marker(marker, dispatch), 'prepared')
            rows = forms.list(session)
            self.assertEqual(len(rows), 1)
            form = forms.read(session, rows[0]['form_id'])
            self.assertEqual((form['service'],form['state'],form['request']['images']), ('minimax-h3-i2v','editing',[]))
            generate.assert_not_called()

    def test_completed_image_proposal_prepares_same_form_after_recovery(self):
        from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
        from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, job = 'a'*32, '2026-11-24_22-01-26-b482d868'
            sessions = HermesSessionStore(root/'sessions')
            sessions.create_session_record(session)
            sessions.append_session_request(session, 'original_request', 'MiniMax 이미지 생성')
            sessions.attach_session_job(session, 'original_request', job)
            marker = root/job/'minimax-form-pending.json'
            marker.parent.mkdir()
            detail = {'status':{'status':'completed'}, 'final_response_truncated':False,
                      'request':{'prompt':'MiniMax 이미지 생성','minimax_preferred':True,'image_selection_version':1},
                      'final_response':'HERMES_FLUX_PROPOSAL\n'+json.dumps({'service':'flux-image','prompt':'red roof','width':512,'height':512,'seed':42,'explicit_service':True})+'\nEND_HERMES_FLUX_PROPOSAL'}
            forms = MiniMaxFormStore(root/'forms.sqlite3')
            receipts = HermesDelegationStore(root/'receipts')
            calls = []
            def dispatch(command, payload):
                calls.append(command)
                if command == 'hermes-detail': return detail
                return execute_minimax_form_command(command, payload, sessions=sessions, read_job=lambda _:detail,
                    dispatch=Mock(), forms=forms, receipts=receipts)
            for _ in range(2):
                marker.write_text(json.dumps({'session_id':session,'job_id':job}))
                self.assertEqual(advance_form_marker(marker, dispatch), 'prepared')
            rows = forms.list(session)
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]['source_job_id'], rows[0]['state']), (job, 'editing'))
            self.assertEqual(forms.read(session, rows[0]['form_id'])['request']['width'], 512)
            self.assertNotIn('generate', calls)

    def test_retries_interrupted_prepare_and_never_submits_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            job = '2026-11-24_22-01-26-b482d868'
            path = Path(directory) / job / 'minimax-form-pending.json'
            path.parent.mkdir()
            path.write_text(json.dumps({'session_id':'a'*32,'job_id':job}))
            detail = {'status':{'status':'running'}, 'request':{}, 'final_response':None}
            def dispatch(command, payload):
                if command == 'hermes-detail': return detail
                self.assertEqual(command, 'hermes-minimax-form-prepare')
                raise OSError('일시 연결 실패')
            self.assertEqual(advance_form_marker(path, dispatch), 'waiting')
            self.assertTrue(path.exists())
            detail.update(status={'status':'completed'}, final_response='HERMES_FLUX_PROPOSAL', final_response_truncated=False)
            with patch('workflow.domains.hermes_agent.minimax_form_scheduler.parse_hermes_image_proposal', return_value={}), \
                 patch('workflow.domains.hermes_agent.minimax_form_scheduler.select_image_proposal', return_value={'service':'minimax-h3-image'}):
                with self.assertRaises(OSError): advance_form_marker(path, dispatch)
                self.assertTrue(path.exists())
                calls = []
                def retry(command, payload):
                    calls.append(command)
                    return detail if command == 'hermes-detail' else {'form_id':'b'*32}
                self.assertEqual(advance_form_marker(path, retry), 'prepared')
                self.assertEqual(calls, ['hermes-detail', 'hermes-minimax-form-prepare'])
                self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
