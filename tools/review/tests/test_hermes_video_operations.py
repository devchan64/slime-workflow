"""DWPose·Wan 서비스별 접수, 결과 경로, 중지 경계 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import video_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesVideoOperationsTests(unittest.TestCase):
    def test_services_delegate_independently_and_reject_prepare(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(video_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(video_operations,'validate_hermes_video_request') as current_validate_mock, patch.object(video_operations,'call_hermes_video_service',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_service_name in enumerate(video_operations.HERMES_VIDEO_SERVICES):
                current_request_id='video_request_'+str(current_index_value)
                current_request_value={'action':'generate'}
                self.assertFalse(video_operations.submit_hermes_video_request(current_request_id,current_service_name,current_request_value)['duplicate'])
                self.assertTrue(video_operations.submit_hermes_video_request(current_request_id,current_service_name,current_request_value)['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,4)
            self.assertEqual(current_validate_mock.call_count,4)
            with self.assertRaises(ValueError):
                video_operations.read_hermes_video_status('video_request_0','wan22-vace')
            with self.assertRaises(ValueError):
                video_operations.list_hermes_video_receipts('arbitrary-service')
        with self.assertRaises(ValueError):
            video_operations.validate_hermes_video_request('wan22-fun-control',{'action':'prepare'})

    def test_video_paths_are_same_service_job_and_attempt(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_good_path='/wan22-vace/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/preview.mp4'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('video_request_123','wan22-vace',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(video_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(video_operations,'call_hermes_video_service',return_value={'status':'completed','video':current_good_path,'log':'private'}) as current_gateway_mock:
                current_result_value=video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-ffffffff','status':'completed','video':current_good_path}
                with self.assertRaises(ValueError):
                    video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','video':current_good_path}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['video'],current_good_path)
                self.assertEqual(current_result_value['job']['video'],current_good_path)
                self.assertEqual(current_result_value['job']['result_status'],'partial')
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'status':'completed','video':current_good_path,'image':current_good_path.replace('preview.mp4','output-000.png'),'download':current_good_path.replace('preview.mp4','frames.zip')}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['result_status'],'available')
                current_gateway_mock.return_value={'status':'completed','result_error':'private filesystem detail','video':current_good_path}
                current_result_value=video_operations.read_hermes_video_status('video_request_123','wan22-vace')
                self.assertEqual(current_result_value['job']['result_status'],'unavailable')
                self.assertIsNone(current_result_value['job']['video'])
                self.assertNotIn('private',str(current_result_value))
                current_gateway_mock.return_value={'status':'completed','video':current_good_path,'image':current_good_path.replace('a'*32,'b'*32).replace('preview.mp4','output-000.png')}
                self.assertEqual(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['result_status'],'unavailable')
                current_gateway_mock.return_value={'status':'completed','video':'https://evil.invalid/video.mp4'}
                self.assertIsNone(video_operations.read_hermes_video_status('video_request_123','wan22-vace')['job']['video'])
                with self.assertRaises(ValueError):
                    video_operations.cancel_hermes_video_request('video_request_123','wan22-vace','2026-11-18_00-00-00-ffffffff')

    def test_unknown_video_response_is_not_resent(self):
        with TemporaryDirectory() as current_root_name, patch.object(video_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(video_operations,'validate_hermes_video_request'), patch.object(video_operations,'call_hermes_video_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                video_operations.submit_hermes_video_request('video_unknown_123','dwpose',{'action':'generate'})
            self.assertEqual(video_operations.read_hermes_video_status('video_unknown_123','dwpose')['receipt']['state'],'unknown')
            self.assertTrue(video_operations.submit_hermes_video_request('video_unknown_123','dwpose',{'action':'generate'})['duplicate'])
            current_gateway_mock.assert_called_once()
