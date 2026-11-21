import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore

def sample_request():
    return {'prompt':'walk','negative_prompt':'','images':['image'],'pose_video':'video', 'frames':21, 'steps':20, 'seed':42, 'flow_shift':5, 'guidance_scale':6, 'switch_ratio':0.5}


class VideoFormTests(unittest.TestCase):
    def test_seed_request_selects_only_unambiguous_source(self):
        from workflow.domains.hermes_agent.service import seed_form_proposal
        job='2026-11-21_10-21-48-00e8c029'
        self.assertEqual(seed_form_proposal('다른 시드로 생성해보자',{job}),{'job_id':job,'seed':None})
        self.assertEqual(seed_form_proposal('시드 123으로 생성', {job})['seed'],123)
        self.assertIn('reason',seed_form_proposal('다른 시드로 생성',set()))
        self.assertIn('reason',seed_form_proposal('다른 시드로 생성',{job,'2026-11-21_09-06-11-3446aabc'}))
        self.assertIn('reason',seed_form_proposal('시드 -1로 생성',{job}))
        self.assertIsNone(seed_form_proposal('생성 이력 조회',{job}))

    def test_save_retry_and_reopen_are_bound_to_session_and_content(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session, form = 'a'*32, 'b'*32
            store.create_session_record(session)
            request = sample_request()
            self.assertFalse(store.save_video_form(session, form, request, None)['duplicate'])
            self.assertTrue(store.save_video_form(session, form, request, None)['duplicate'])
            self.assertEqual(len(store.read_session_record(session)['messages']), 1)
            self.assertEqual(store.read_video_form(session, form)['request'], request)
            with self.assertRaises(ValueError): store.save_video_form(session, form, {**request,'prompt':'changed'}, None)
            store.create_session_record('c'*32)
            with self.assertRaises(ValueError): store.read_video_form('c'*32, form)
            store._form_path(session,form).write_text('{}')
            with self.assertRaises(ValueError): store.read_video_form(session,form)

    def test_submission_retry_and_uncertain_receipt_do_not_submit_twice(self):
        with tempfile.TemporaryDirectory() as root:
            manager = HermesServiceManager(hermes_session_root=Path(root)/'sessions')
            store = HermesSessionStore(Path(root)/'sessions')
            session, form = 'a'*32, 'b'*32
            store.create_session_record(session)
            store.save_video_form(session, form, sample_request(), None)
            delegation = HermesDelegationStore(Path(root)/'delegations')
            def execute_once(request_id, service, request):
                return delegation.execute_service_delegation_once(request_id, service, request, submit, lambda _:None)
            payload={'session_id':session,'form_id':form}
            with patch('workflow.domains.hermes_agent.video_operations.submit_hermes_video_request',side_effect=execute_once), \
                 patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=delegation):
                calls=[]
                def submit(_):
                    calls.append(1)
                    raise OSError('response lost')
                with self.assertRaises(OSError): manager.execute_hermes_command('hermes-video-form-submit',payload)
                self.assertEqual(manager.execute_hermes_command('hermes-video-form-status',payload)['state'],'unknown')
                self.assertEqual(manager.execute_hermes_command('hermes-video-form-submit',payload)['state'],'unknown')
                self.assertEqual(len(calls),1)

    def test_accepted_receipt_is_recoverable_after_repeat_submission(self):
        with tempfile.TemporaryDirectory() as root:
            manager = HermesServiceManager(hermes_session_root=Path(root)/'sessions')
            store = HermesSessionStore(Path(root)/'sessions')
            session, form = 'a'*32, 'c'*32
            store.create_session_record(session)
            store.save_video_form(session, form, sample_request(), None)
            delegation = HermesDelegationStore(Path(root)/'delegations')
            calls=[]
            def submit(_):
                calls.append(1)
                return {'id':'2026-11-21_10-21-48-00e8c029'}
            def execute_once(request_id, service, request):
                return delegation.execute_service_delegation_once(request_id, service, request, submit, lambda _:None)
            payload={'session_id':session,'form_id':form}
            with patch('workflow.domains.hermes_agent.video_operations.submit_hermes_video_request',side_effect=execute_once), \
                 patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=delegation):
                first=manager.execute_hermes_command('hermes-video-form-submit',payload)
                again=manager.execute_hermes_command('hermes-video-form-submit',payload)
                receipt=manager.execute_hermes_command('hermes-video-form-status',payload)
                self.assertEqual(first['job_id'],receipt['job_id'])
                self.assertTrue(again['duplicate'])
                self.assertEqual(len(calls),1)
