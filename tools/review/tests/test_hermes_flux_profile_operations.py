"""FLUX 프로필별 위임 경계와 결과 복구 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import flux_profile_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS


class HermesFluxProfileOperationsTests(unittest.TestCase):
    def test_every_profile_delegates_to_own_service_and_isolates_receipts(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(flux_profile_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch('tools.review.domains.image.flux_image_generation.FluxImageGenerationManager.validate_generation_request') as current_validate_mock, patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'id':current_job_identifier}) as current_gateway_mock:
            for current_index_value,current_profile_name in enumerate(FLUX_IMAGE_PROFILE_RECORDS):
                current_request_identifier='profile_request_'+str(current_index_value)
                current_request_value={'profile':current_profile_name}
                self.assertFalse(flux_profile_operations.submit_hermes_flux_profile(current_request_identifier,current_profile_name,current_request_value)['duplicate'])
                self.assertTrue(flux_profile_operations.submit_hermes_flux_profile(current_request_identifier,current_profile_name,current_request_value)['duplicate'])
                self.assertEqual(flux_profile_operations.list_hermes_flux_profile_receipts(current_profile_name)['records'][0]['request_id'],current_request_identifier)
            self.assertEqual(current_validate_mock.call_count,len(FLUX_IMAGE_PROFILE_RECORDS))
            self.assertEqual(current_gateway_mock.call_count,len(FLUX_IMAGE_PROFILE_RECORDS))
            with self.assertRaises(ValueError):
                flux_profile_operations.read_hermes_flux_profile_status('profile_request_0','flux-building')
            with self.assertRaises(ValueError):
                flux_profile_operations.list_hermes_flux_profile_receipts('arbitrary-service')

    def test_expression_uses_its_own_manager_and_service(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name, patch.object(flux_profile_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch('tools.review.domains.image.flux_expression_generation.FluxExpressionGenerationManager.validate_generation_request') as current_validate_mock, patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'id':current_job_identifier}) as current_gateway_mock:
            current_request_value={'prompt':'joy'}
            self.assertFalse(flux_profile_operations.submit_hermes_flux_profile('expression_request_123','flux-expression',current_request_value)['duplicate'])
            self.assertTrue(flux_profile_operations.submit_hermes_flux_profile('expression_request_123','flux-expression',current_request_value)['duplicate'])
            current_validate_mock.assert_called_once_with(current_request_value)
            current_gateway_mock.assert_called_once_with('flux-expression','generate',current_request_value)
            self.assertEqual(flux_profile_operations.list_hermes_flux_profile_receipts('flux-expression')['records'][0]['job_id'],current_job_identifier)
            with self.assertRaises(ValueError):
                flux_profile_operations.read_hermes_flux_profile_status('expression_request_123','flux-image')

    def test_completed_image_link_requires_exact_service_job_and_path(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_expected_path='/flux-building-generator/jobs/'+current_job_identifier+'/result.png'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('profile_request_123','flux-building',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(flux_profile_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(flux_profile_operations,'call_hermes_flux_profile') as current_gateway_mock:
                current_gateway_mock.return_value={'status':'completed','image':current_expected_path}
                current_result_value=flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']
                self.assertEqual(current_result_value['image'],current_expected_path)
                self.assertEqual(current_result_value['result_status'],'available')
                current_gateway_mock.return_value={'id':'2026-11-18_00-00-00-ffffffff','status':'completed','image':current_expected_path}
                with self.assertRaises(ValueError):
                    flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')
                current_gateway_mock.return_value={'id':current_job_identifier,'status':'completed','image':current_expected_path}
                self.assertEqual(flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']['image'],current_expected_path)
                with self.assertRaises(ValueError):
                    flux_profile_operations.inspect_hermes_flux_result('flux-image',current_job_identifier,{'id':'2026-11-18_00-00-00-ffffffff','status':'running'})
                for current_bad_path in ('https://example.com/result.png',current_expected_path+'?x=1',current_expected_path.replace('flux-building','flux-prop'),current_expected_path.replace(current_job_identifier,'2026-11-18_00-00-00-ffffffff')):
                    current_gateway_mock.return_value={'status':'completed','image':current_bad_path}
                    current_result_value=flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']
                    self.assertIsNone(current_result_value['image'])
                    self.assertEqual(current_result_value['result_status'],'unavailable')
                current_gateway_mock.return_value={'status':'running','image':current_expected_path}
                self.assertIsNone(flux_profile_operations.read_hermes_flux_profile_status('profile_request_123','flux-building')['job']['image'])

    def test_cancellation_requires_explicit_service_acknowledgement(self):
        from tools.review.domains.hermes_agent import audio_operations,video_operations,translation_operations
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=[(flux_profile_operations,'call_hermes_flux_profile','flux-building','cancel_hermes_flux_profile'),(audio_operations,'call_hermes_audio_service','music-heartmula','cancel_hermes_audio_request'),(video_operations,'call_hermes_video_service','wan22-vace','cancel_hermes_video_request'),(translation_operations,'call_hermes_translation_service','prompt-translation','cancel_hermes_translation_request')]
        for current_module_value,current_gateway_name,current_service_name,current_function_name in current_cases:
            with self.subTest(service=current_service_name),TemporaryDirectory() as current_root_name:
                current_store_value=HermesDelegationStore(Path(current_root_name))
                current_store_value.execute_service_delegation_once('cancel_request_123',current_service_name,{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
                current_arguments=('cancel_request_123',current_job_identifier) if current_service_name=='prompt-translation' else ('cancel_request_123',current_service_name,current_job_identifier)
                with patch.object(current_module_value,'HermesDelegationStore',return_value=current_store_value),patch.object(current_module_value,current_gateway_name) as current_gateway_mock:
                    for current_response_value in ({},{'cancel_requested':False},{'cancel_requested':'true'}):
                        current_gateway_mock.return_value=current_response_value
                        with self.assertRaises(ValueError):getattr(current_module_value,current_function_name)(*current_arguments)
                    current_gateway_mock.return_value={'status':'running','cancel_requested':True}
                    self.assertTrue(getattr(current_module_value,current_function_name)(*current_arguments)['cancel_requested'])

    def test_unknown_response_and_cancel_require_matching_service_and_job(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('profile_request_123','flux-building',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(flux_profile_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(flux_profile_operations,'call_hermes_flux_profile',return_value={'status':'running','cancel_requested':True}) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-building','2026-11-18_00-00-00-ffffffff')
                with self.assertRaises(ValueError):
                    flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-prop',current_job_identifier)
                current_gateway_mock.assert_not_called()
                self.assertTrue(flux_profile_operations.cancel_hermes_flux_profile('profile_request_123','flux-building',current_job_identifier)['cancel_requested'])
