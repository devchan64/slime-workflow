"""번역 위임의 중복, 상태, 중지 경계 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import translation_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesTranslationOperationsTests(unittest.TestCase):
    def test_translation_evidence_preserves_content_and_rejects_invalid_response(self):
        current_candidate_value={'path':'lore/tree.md','heading':'나무','text':'숲의 나무 근거','matched_terms':['나무'],'extra':'제외'}
        with patch.object(translation_operations,'call_hermes_translation_service',return_value={'candidates':[current_candidate_value]}) as current_gateway_mock:
            current_result_value=translation_operations.search_hermes_translation_evidence('나무')
            self.assertEqual(current_result_value['candidates'][0]['text'],'숲의 나무 근거')
            self.assertNotIn('extra',current_result_value['candidates'][0])
            self.assertIn('승인된 번역어',current_result_value['note'])
            current_gateway_mock.assert_called_once_with('translation-rag',{'text':'나무'})
        for current_bad_value in ('', ' '*3, 'a'*6001, None):
            with self.subTest(current_bad_value=current_bad_value), self.assertRaises(ValueError):
                translation_operations.search_hermes_translation_evidence(current_bad_value)
        with patch.object(translation_operations,'call_hermes_translation_service',return_value={'candidates':[{'path':'x'}]}), self.assertRaises(ValueError):
            translation_operations.search_hermes_translation_evidence('나무')

    def test_translation_evidence_crosses_gateway_dispatch_without_gpu(self):
        from tools.review.common.management_gateway import execute_management_command
        from tools.review.domains.hermes_agent.service import HermesServiceManager
        current_candidate_value={'path':'lore/tree.md','heading':'나무','text':'숲의 나무 근거','matched_terms':['나무']}
        with TemporaryDirectory() as current_root_name, patch.object(translation_operations,'call_hermes_translation_service',return_value={'candidates':[current_candidate_value]}) as current_gateway_mock:
            current_root_path=Path(current_root_name)
            current_manager_value=HermesServiceManager(current_root_path/'jobs',current_root_path/'sessions')
            import threading
            from http.server import ThreadingHTTPServer
            from tools.review.common.management_gateway import ManagementCommandGateway
            from tools.review.gateway_server import create_gateway_request_handler
            current_dispatch_value=ManagementCommandGateway({'hermes-agent':current_manager_value.handle_hermes_request})
            current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_dispatch_value.handle))
            current_server_value.emit_gateway_trace=lambda *current_arguments:None
            current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
            current_thread_value.start()
            try:
                current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
                current_response_value=execute_management_command('hermes-agent','hermes-translation-evidence',{'text':'나무'},current_gateway_origin)
                self.assertEqual(current_response_value['candidates'],[current_candidate_value])
                current_gateway_mock.assert_called_once_with('translation-rag',{'text':'나무'})
            finally:
                current_server_value.shutdown()
                current_server_value.server_close()
                current_thread_value.join(timeout=5)

    def test_translation_resume_receipt_duplicate_and_unknown(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from tools.review.domains.hermes_agent import translation_resume_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='a'*64
        with TemporaryDirectory() as current_directory_name,patch.object(translation_resume_operations,'TRANSLATION_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(translation_resume_operations,'call_hermes_translation_service') as current_service_mock:
            current_service_mock.return_value={'id':current_job_identifier,'service':'prompt-translation','status':'failed','expected_resume_fingerprint':current_fingerprint_value}
            self.assertEqual(translation_resume_operations.preview_hermes_translation_resume(current_job_identifier)['status'],'failed')
            current_service_mock.return_value={'id':current_job_identifier,'status':'queued'}
            self.assertEqual(translation_resume_operations.submit_hermes_translation_resume_once('translation_resume_123',current_job_identifier,current_fingerprint_value)['state'],'accepted')
            self.assertTrue(translation_resume_operations.submit_hermes_translation_resume_once('translation_resume_123',current_job_identifier,current_fingerprint_value)['duplicate'])
            with self.assertRaises(ValueError):translation_resume_operations.submit_hermes_translation_resume_once('translation_resume_123',current_job_identifier,'b'*64)
            current_service_mock.side_effect=OSError('response lost')
            with self.assertRaises(OSError):translation_resume_operations.submit_hermes_translation_resume_once('translation_resume_lost',current_job_identifier,'b'*64)
            self.assertEqual(translation_resume_operations.read_hermes_translation_resume_receipt('translation_resume_lost')['state'],'unknown')
            self.assertTrue(translation_resume_operations.submit_hermes_translation_resume_once('translation_resume_lost',current_job_identifier,'b'*64)['duplicate'])
            self.assertEqual(current_service_mock.call_count,3)


    def test_submit_duplicate_status_and_matching_cancel(self):
        current_request_value={'text':'나무','target_language':'en','glossary':[]}
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_job_value={'id':current_job_identifier,'request':{'text':'private'},'status':{'status':'completed','path':'private'},'result':{'text':'tree','files':{'private':'secret'},'term_checks':[{'source':'나무','target':'tree','status':'matched','source_ref':'private'}],'quality_checks':[{'source':'의미','target':'검토 미완료: /private/path','status':'review'}]}}
        def execute_translation_command(current_command_name,current_payload_value):
            if current_command_name=='translation-submit':return {'id':current_job_identifier,'status':'queued'}
            if current_command_name=='translation-status':return current_job_value
            if current_command_name=='translation-cancel':return {'status':'running','cancel_requested':True}
            raise AssertionError(current_command_name)
        with TemporaryDirectory() as current_root_name, patch.object(translation_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(translation_operations,'validate_hermes_translation_request') as current_validator_mock, patch.object(translation_operations,'call_hermes_translation_service',side_effect=execute_translation_command) as current_gateway_mock:
            self.assertFalse(translation_operations.submit_hermes_translation_request('translation_123',current_request_value)['duplicate'])
            self.assertTrue(translation_operations.submit_hermes_translation_request('translation_123',current_request_value)['duplicate'])
            current_validator_mock.assert_called_once()
            current_result_value=translation_operations.read_hermes_translation_status('translation_123')
            self.assertEqual(current_result_value['job']['id'],current_job_identifier)
            self.assertEqual(current_result_value['job']['result']['text'],'tree')
            self.assertNotIn('private',str(current_result_value))
            self.assertEqual(current_result_value['job']['result']['quality_checks'][0]['target'],'검토 미완료')
            with self.assertRaises(ValueError):
                translation_operations.cancel_hermes_translation_request('translation_123','2026-11-18_00-00-00-ffffffff')
            self.assertTrue(translation_operations.cancel_hermes_translation_request('translation_123',current_job_identifier)['cancel_requested'])
            self.assertEqual([item.args[0] for item in current_gateway_mock.call_args_list],['translation-submit','translation-status','translation-cancel'])

    def test_lost_response_is_not_resent(self):
        with TemporaryDirectory() as current_root_name, patch.object(translation_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(translation_operations,'validate_hermes_translation_request'), patch.object(translation_operations,'call_hermes_translation_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                translation_operations.submit_hermes_translation_request('translation_456',{'text':'나무','target_language':'en'})
            self.assertEqual(translation_operations.read_hermes_translation_status('translation_456')['receipt']['state'],'unknown')
            self.assertTrue(translation_operations.submit_hermes_translation_request('translation_456',{'text':'나무','target_language':'en'})['duplicate'])
            current_gateway_mock.assert_called_once()
