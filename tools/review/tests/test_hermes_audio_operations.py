"""음악·효과음 위임의 서비스 분리, 결과 경로, 중지 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import audio_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesAudioOperationsTests(unittest.TestCase):
    def test_services_validate_and_reuse_independent_receipts(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_requests_value={'music-heartmula':{'prompt':'piano','lyrics':'[Verse]\nHello','duration_seconds':10,'seed':7},'sfx-dasheng-audiogen':{'prompt':'water splash','seed':42}}
        with TemporaryDirectory() as current_root_name, patch.object(audio_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_service_name in enumerate(current_requests_value):
                current_request_id='audio_request_'+str(current_index_value)
                self.assertFalse(audio_operations.submit_hermes_audio_request(current_request_id,current_service_name,current_requests_value[current_service_name])['duplicate'])
                self.assertTrue(audio_operations.submit_hermes_audio_request(current_request_id,current_service_name,current_requests_value[current_service_name])['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,2)
            with self.assertRaises(ValueError):
                audio_operations.read_hermes_audio_status('audio_request_0','sfx-dasheng-audiogen')
            with self.assertRaises(ValueError):
                audio_operations.validate_hermes_audio_request('music-heartmula',{'action':'prepare'})
            with self.assertRaises(ValueError):
                audio_operations.validate_hermes_audio_service('music-magenta')

    def test_audio_paths_are_same_service_job_and_attempt(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_good_path='/music-heartmula/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('audio_request_123','music-heartmula',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(audio_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(audio_operations,'call_hermes_audio_service',return_value={'id':current_job_identifier,'status':'completed','audio':current_good_path,'log':'private'}) as current_gateway_mock:
                current_result_value=audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')
                self.assertEqual(current_result_value['job']['audio'],current_good_path)
                self.assertEqual(current_result_value['job']['result_status'],'available')
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','audio':'https://evil.invalid/audio.wav'}
                current_invalid_result=audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')['job']
                self.assertIsNone(current_invalid_result['audio'])
                self.assertEqual(current_invalid_result['result_status'],'unavailable')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'running'}
                self.assertEqual(audio_operations.read_hermes_audio_status('audio_request_123','music-heartmula')['job']['result_status'],'not_ready')
                with self.assertRaises(ValueError):
                    audio_operations.cancel_hermes_audio_request('audio_request_123','music-heartmula','2026-11-18_00-00-00-ffffffff')

    def test_lost_audio_response_is_not_resent(self):
        with TemporaryDirectory() as current_root_name, patch.object(audio_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(audio_operations,'call_hermes_audio_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                audio_operations.submit_hermes_audio_request('audio_unknown_123','sfx-dasheng-audiogen',{'prompt':'water','seed':42})
            self.assertEqual(audio_operations.read_hermes_audio_status('audio_unknown_123','sfx-dasheng-audiogen')['receipt']['state'],'unknown')
            self.assertTrue(audio_operations.submit_hermes_audio_request('audio_unknown_123','sfx-dasheng-audiogen',{'prompt':'water','seed':42})['duplicate'])
            current_gateway_mock.assert_called_once()

    def test_source_history_rejects_incomplete_or_mismatched_pages(self):
        from tools.review.domains.hermes_agent.audio_operations import sanitize_hermes_source_history
        current_request_value={'offset':1,'limit':1,'snapshot':'a'*64}
        current_record_value={'id':'legacy-id','recorded_status':'completed','status_source':'index'}
        current_result_value={'records':[current_record_value],'total':3,'offset':1,'next_offset':2,'snapshot':'a'*64,'unavailable_count':0}
        self.assertEqual(sanitize_hermes_source_history('music-heartmula',current_request_value,current_result_value)['records'],[current_record_value])
        for current_bad_result in ({**current_result_value,'records':[]},{**current_result_value,'next_offset':None},{**current_result_value,'snapshot':'b'*64},{**current_result_value,'next_offset':True}):
            with self.subTest(result=current_bad_result),self.assertRaises(ValueError):
                sanitize_hermes_source_history('music-heartmula',current_request_value,current_bad_result)

    def test_retired_audio_history_does_not_enable_delegation(self):
        current_response_value={'records':[],'total':0,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        with patch.object(audio_operations,'execute_management_command',return_value=current_response_value) as current_gateway_mock:
            self.assertEqual(audio_operations.read_hermes_audio_source_history('music-magenta',{})['records'],[])
            self.assertEqual(current_gateway_mock.call_args.args[:3],('music-magenta','history-observe',{}))
        with self.assertRaises(ValueError):
            audio_operations.submit_hermes_audio_request('request_123','music-magenta',{})
