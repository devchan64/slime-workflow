import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore


class MiniMaxFormCommandsTests(unittest.TestCase):
    def test_question_approval_does_not_submit_a_form_edited_after_the_question(self):
        from workflow.domains.hermes_agent.minimax_form_action import submit_requested_form
        with tempfile.TemporaryDirectory() as directory:
            forms=MiniMaxFormStore(Path(directory)/'forms.sqlite3')
            session,form,job='a'*32,'b'*32,'2026-11-24_22-01-26-b482d868'
            forms.create(session,form,'minimax-h3-image',job,{'prompt':'원래 입력'})
            forms.save(session,form,1,{'prompt':'수정된 입력'})
            sessions,receipts,manager=Mock(),Mock(),Mock()
            receipts.read_service_delegation.return_value={'state':'not_found'}
            generation=Mock()
            def dispatch(command,payload):
                if command=='hermes-resident-status': return {'resident':{'state':'not_found'}}
                return execute_minimax_form_command(command,payload,sessions=sessions,read_job=Mock(),
                                                    dispatch=generation,forms=forms,receipts=receipts)
            answer=(f'질문 작업 {job}에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 1\n'
                    '1. 이 입력으로 생성할까요?\n답변: 승인')
            with patch('workflow.domains.hermes_agent.minimax_form_commands.resolve_proposal',return_value=({},manager)):
                with self.assertRaisesRegex(ValueError,'변경되었거나'):
                    submit_requested_form(session,answer,{'form_id':form,'revision':1},dispatch)
            self.assertEqual(forms.read(session,form)['state'],'editing')
            generation.assert_not_called()

    def test_indeterminate_or_rejected_legacy_receipt_is_not_editable(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory)/'forms.sqlite3')
            session, form, source = 'a'*32, 'b'*32, '2026-11-24_22-01-26-b482d868'
            forms.create(session,form,'minimax-h3-image',source,{'prompt':'입력'})
            receipts = Mock()
            for state in ('unknown','rejected'):
                receipts.read_service_delegation.return_value = {'state':state}
                args = dict(sessions=Mock(),read_job=Mock(),dispatch=Mock(),forms=forms,receipts=receipts)
                result = execute_minimax_form_command('hermes-minimax-form-read',{'session_id':session,'form_id':form},**args)
                self.assertEqual((result['state'],result['receipt_state']),('external_receipt',state))
                with self.assertRaises(ValueError):
                    execute_minimax_form_command('hermes-minimax-form-save',{'session_id':session,'form_id':form,'revision':1,'request':{'prompt':'수정'}},**args)

    def test_legacy_receipt_after_form_creation_is_not_shown_as_editable(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.flux_reports import proposal_request_id
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            forms, receipts = MiniMaxFormStore(root/'forms.sqlite3'), HermesDelegationStore(root/'receipts')
            session, form = 'a'*32, 'b'*32
            source, generated = '2026-11-24_22-01-26-b482d868', '2026-11-24_22-23-17-2a551ada'
            service = 'minimax-h3-image'
            forms.create(session,form,service,source,{'prompt':'원래 입력'})
            request_id = proposal_request_id(session,source,service)
            receipts.execute_service_delegation_once(request_id,service,{'prompt':'이전 경로 입력'},lambda _: {'id':generated},lambda _:None)
            def call(command, **payload):
                return execute_minimax_form_command('hermes-minimax-form-'+command, {'session_id':session,**payload},
                    sessions=Mock(),read_job=Mock(),dispatch=Mock(),forms=forms,receipts=receipts)
            self.assertEqual(call('list')['forms'][0]['state'],'external_receipt')
            self.assertEqual(call('read',form_id=form)['job_id'],generated)
            with self.assertRaises(ValueError): call('save',form_id=form,revision=1,request={'prompt':'수정'})
            with self.assertRaises(ValueError): call('submit',form_id=form,revision=1)
            self.assertEqual(forms.read(session,form)['state'],'editing')

    def test_video_proposal_requires_reference_before_pinning_or_dispatch(self):
        import base64
        import io
        import json
        from PIL import Image
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as directory:
            session, job = 'a'*32, '2026-11-24_22-01-26-b482d868'
            forms = MiniMaxFormStore(Path(directory)/'forms.sqlite3')
            receipts = HermesDelegationStore(Path(directory)/'receipts')
            sessions = Mock()
            sessions.read_session_record.return_value = {'messages':[{'job_id':job}]}
            proposal = {'service':'minimax-h3-i2v','mode':'first_frame','prompt':'천천히 걸어간다','explicit_service':True}
            detail = {'status':{'status':'completed'},'final_response_truncated':False,
                      'final_response':'HERMES_VIDEO_PROPOSAL\n'+json.dumps(proposal,ensure_ascii=False)+'\nEND_HERMES_VIDEO_PROPOSAL',
                      'request':{'prompt':'MiniMax 영상으로 걸어가게 해줘','minimax_preferred':True}}
            generated = '2026-11-24_22-23-17-2a551ada'
            dispatch = Mock(return_value={'id':generated})
            def call(operation, **payload):
                return execute_minimax_form_command('hermes-minimax-form-'+operation, {'session_id':session,**payload},
                    sessions=sessions,read_job=lambda _:detail,dispatch=dispatch,forms=forms,receipts=receipts)
            form = call('prepare',proposal_job_id=job,service='minimax-h3-i2v')
            with self.assertRaisesRegex(ValueError,'첫 프레임'):
                call('submit',form_id=form['form_id'],revision=1)
            self.assertEqual(forms.read(session,form['form_id'])['state'],'editing')
            dispatch.assert_not_called()
            image = io.BytesIO()
            Image.new('RGB',(832,480),'red').save(image,format='PNG')
            request = {**form['request'],'images':[base64.b64encode(image.getvalue()).decode()]}
            saved = call('save',form_id=form['form_id'],revision=1,request=request)
            edited = call('update',form_id=form['form_id'],revision=saved['revision'],request={'prompt':'천천히 달린다'})
            self.assertEqual(edited['request']['images'],request['images'])
            with self.assertRaises(ValueError):
                call('submit',form_id=form['form_id'],revision=saved['revision'])
            dispatch.assert_not_called()
            accepted = call('submit',form_id=form['form_id'],revision=edited['revision'])
            self.assertEqual(accepted['job_id'],generated)
            self.assertEqual(forms.read(session,form['form_id'])['state'],'accepted')
            self.assertEqual(dispatch.call_count,1)
            self.assertEqual(dispatch.call_args.args[2]['images'],request['images'])
            self.assertEqual(dispatch.call_args.args[2]['prompt'],'천천히 달린다')

    def test_partial_update_preserves_reference_and_rejects_stale_version(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            session, form = 'a'*32, 'b'*32
            job = '2026-11-24_22-01-26-b482d868'
            original = {'action':'generate','prompt':'집','images':['첨부'], 'width':832,'height':480,'frames':124,'steps':8,'seed':42}
            forms.create(session, form, 'minimax-h3-i2v', job, original)
            def update(revision, changes):
                return execute_minimax_form_command('hermes-minimax-form-update', {'session_id':session,'form_id':form,'revision':revision,'request':changes},
                    sessions=Mock(),read_job=Mock(),dispatch=Mock(),forms=forms)
            updated = update(1, {'prompt':'성당', 'seed':43})
            self.assertEqual(updated['request']['images'], ['첨부'])
            self.assertEqual((updated['request']['prompt'],updated['revision']), ('성당',2))
            with self.assertRaises(ValueError): update(1, {'prompt':'오래된 변경'})
            with self.assertRaises(ValueError): update(2, {'images':[]})
            with self.assertRaises(ValueError): update(2, {'width':512})
            self.assertEqual(forms.read(session,form)['revision'], 2)

    def test_prepare_is_idempotent_and_refuses_existing_legacy_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            sessions, receipts = Mock(), Mock()
            receipts.read_service_delegation.return_value = {'state':'not_found'}
            payload = {'session_id':'a'*32, 'proposal_job_id':'2026-11-24_22-01-26-b482d868', 'service':'minimax-h3-image'}
            proposal = {'prompt':'성당', 'width':512, 'height':512, 'seed':42}
            with patch('workflow.domains.hermes_agent.minimax_form_commands.resolve_proposal', return_value=(proposal, Mock())):
                def prepare(value):
                    return execute_minimax_form_command('hermes-minimax-form-prepare', value, sessions=sessions,
                        read_job=Mock(), dispatch=Mock(), forms=forms, receipts=receipts)
                first = prepare(payload)
                self.assertEqual(first['request']['width'], 512)
                self.assertEqual(prepare(payload)['form_id'], first['form_id'])
                receipts.read_service_delegation.return_value = {'state':'accepted'}
                with self.assertRaises(ValueError): prepare({**payload, 'proposal_job_id':'2026-11-24_22-01-26-aaaaaaaa'})
                from workflow.domains.hermes_agent.flux_reports import proposal_request_id
                import hashlib
                other = {**payload, 'proposal_job_id':'2026-11-24_22-01-26-aaaaaaaa'}
                form_id = hashlib.sha256(('minimax-form:' + proposal_request_id(other['session_id'],other['proposal_job_id'],other['service'])).encode()).hexdigest()[:32]
                with self.assertRaisesRegex(ValueError, '기존 접수'):
                    execute_minimax_form_command('hermes-minimax-form-create', {**other,'form_id':form_id,'request':{'prompt':'성당'}},
                        sessions=sessions,read_job=Mock(),dispatch=Mock(),forms=forms,receipts=receipts)

    def test_revision_is_pinned_before_dispatch_and_retry_uses_same_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            sessions = Mock()
            manager = Mock()
            receipts = Mock()
            receipts.read_service_delegation.return_value = {'state':'not_found'}
            session = 'a' * 32
            job = '2026-11-24_22-01-26-b482d868'
            from workflow.domains.hermes_agent.flux_reports import proposal_request_id
            import hashlib
            form = hashlib.sha256(('minimax-form:' + proposal_request_id(session,job,'minimax-h3-image')).encode()).hexdigest()[:32]
            def invoke(command, **payload):
                return execute_minimax_form_command('hermes-minimax-form-' + command,
                    {'session_id':session, 'form_id':form, **payload}, sessions=sessions,
                    read_job=Mock(), dispatch=Mock(), forms=forms, receipts=receipts)
            with patch('workflow.domains.hermes_agent.minimax_form_commands.resolve_proposal', return_value=({}, manager)), \
                 patch('workflow.domains.hermes_agent.minimax_form_commands.submit_from_proposal') as submit:
                with self.assertRaisesRegex(ValueError, '폼 ID'):
                    execute_minimax_form_command('hermes-minimax-form-create', {'session_id':session, 'form_id':'b'*32,
                        'proposal_job_id':job, 'service':'minimax-h3-image', 'request':{'prompt':'집'}},
                        sessions=sessions, read_job=Mock(), dispatch=Mock(), forms=forms, receipts=receipts)
                invoke('create', proposal_job_id=job, service='minimax-h3-image', request={'prompt':'집'})
                invoke('save', revision=1, request={'prompt':'성당'})
                submit.side_effect = OSError('접수 응답 유실')
                with self.assertRaises(OSError): invoke('submit', revision=2)
                self.assertEqual(invoke('read')['state'], 'submitting')
                self.assertEqual(invoke('read')['receipt_state'], 'not_found')
                with self.assertRaises(ValueError): invoke('save', revision=2, request={'prompt':'변경'})
                submit.side_effect = None
                submit.return_value = {'state':'accepted', 'job_id':job}
                invoke('submit', revision=2)
                self.assertEqual(submit.call_args.args[0]['request'], {'prompt':'성당'})
                self.assertEqual(invoke('read')['job_id'], job)

    def test_read_recovers_accepted_receipt_without_resubmission(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            session, form = 'a'*32, 'b'*32
            job = '2026-11-24_22-01-26-b482d868'
            from workflow.domains.hermes_agent.flux_reports import proposal_request_id
            request_id = proposal_request_id(session, job, 'minimax-h3-image')
            forms.create(session, form, 'minimax-h3-image', job, {'prompt':'성당'})
            forms.pin_submission(session, form, 1, request_id)
            # Reopen the persisted database as a new service instance would.
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            receipts = Mock()
            receipts.read_service_delegation.return_value = {'state':'accepted', 'job_id':job}
            dispatch = Mock()
            result = execute_minimax_form_command('hermes-minimax-form-read', {'session_id':session,'form_id':form},
                sessions=Mock(), read_job=Mock(), dispatch=dispatch, forms=forms, receipts=receipts)
            self.assertEqual((result['state'],result['job_id']), ('accepted',job))
            self.assertEqual(forms.read(session, form)['state'], 'accepted')
            dispatch.assert_not_called()

    def test_recovery_rejects_receipt_for_different_input(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.flux_reports import proposal_request_id
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            receipts = HermesDelegationStore(Path(directory) / 'receipts')
            session, form = 'a'*32, 'b'*32
            job = '2026-11-24_22-01-26-b482d868'
            service = 'minimax-h3-image'
            request_id = proposal_request_id(session, job, service)
            receipts.execute_service_delegation_once(request_id, service, {'prompt':'다른 입력'}, lambda _: {'id':job}, lambda _: None)
            forms.create(session, form, service, job, {'prompt':'성당'})
            forms.pin_submission(session, form, 1, request_id)
            with self.assertRaisesRegex(ValueError, '폼 입력'):
                execute_minimax_form_command('hermes-minimax-form-read', {'session_id':session,'form_id':form},
                    sessions=Mock(), read_job=Mock(), dispatch=Mock(), forms=forms, receipts=receipts)
            self.assertEqual(forms.read(session, form)['state'], 'submitting')


if __name__ == '__main__':
    unittest.main()
