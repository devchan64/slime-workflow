"""번역 위임의 중복, 상태, 중지 경계 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import translation_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesTranslationOperationsTests(unittest.TestCase):
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
