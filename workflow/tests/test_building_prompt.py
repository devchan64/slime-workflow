"""건물 페이지의 필수 참조·단어 제한 및 공용 UI 연결 검증."""
import unittest
from workflow.domains.image.building_prompt import load_building_base_prompt, check_building_input_readiness


class BuildingPromptContractTests(unittest.TestCase):
    def test_building_service_isolation(self):
        from workflow.domains.image.building_generation import BuildingGenerationManager
        from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from workflow.domains.image.three_reference_generation import validate_three_reference_job_path
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_building_manager = BuildingGenerationManager()
        current_general_manager = QwenPlainGenerationManager()
        self.assertNotEqual(current_building_manager.job_storage_root, current_general_manager.job_storage_root)
        self.assertNotEqual(current_building_manager.history_storage_path(), current_general_manager.history_storage_path())
        self.assertEqual(validate_three_reference_job_path(current_building_manager.job_storage_root), current_building_manager.job_storage_root)
        self.assertIn('prioritize', MANAGEMENT_SERVICE_COMMANDS['building-generator'])
        self.assertIn('history-delete', MANAGEMENT_SERVICE_COMMANDS['building-generator'])

    def test_asset_generator_storage_isolation(self):
        from workflow.domains.image.billboard_generation import BillboardGuideGenerationManager
        from workflow.domains.image.prop_generation import PropGenerationManager
        from workflow.domains.image.vegetation_generation import VegetationGenerationManager
        from workflow.domains.image.building_generation import BuildingGenerationManager
        from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from workflow.domains.image.three_reference_generation import validate_three_reference_job_path
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_managers = [BillboardGuideGenerationManager(), PropGenerationManager(), VegetationGenerationManager(), BuildingGenerationManager(), QwenPlainGenerationManager()]
        self.assertEqual(len({current_service_manager.job_storage_root for current_service_manager in current_service_managers}), 5)
        self.assertEqual(len({current_service_manager.history_storage_path() for current_service_manager in current_service_managers}), 5)
        for current_service_manager in current_service_managers:
            self.assertEqual(validate_three_reference_job_path(current_service_manager.job_storage_root), current_service_manager.job_storage_root)
        for current_service_name in ('billboard-generator','prop-generator', 'vegetation-generator'):
            current_expected_commands = set(MANAGEMENT_SERVICE_COMMANDS['qwen-21'])
            if current_service_name == 'prop-generator':
                current_expected_commands.add('prepare')
            self.assertEqual(set(MANAGEMENT_SERVICE_COMMANDS[current_service_name]), current_expected_commands)

    def test_layout_and_word_limit(self):
        current_prompt_text = load_building_base_prompt()
        self.assertFalse(check_building_input_readiness(current_prompt_text, False, False, None))
        self.assertTrue(check_building_input_readiness(current_prompt_text, False, False, object()))
        self.assertFalse(check_building_input_readiness('building ' * 100, False, False, object()))
        self.assertFalse(check_building_input_readiness('building ' * 99, True, True, object()))

    def test_building_option_word_limit(self):
        self.assertTrue(check_building_input_readiness('', False, False, object(), True))
        self.assertFalse(check_building_input_readiness('', False, False, object(), False))
        self.assertTrue(check_building_input_readiness('wooden guild hall', False, False, object(), True))
        self.assertFalse(check_building_input_readiness('wooden guild hall ' * 40, True, False, object(), True))

    def test_flux_profiles_preserve_required_and_optional_references(self):
        import base64
        from io import BytesIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from PIL import Image
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        image=BytesIO();Image.new('RGB',(16,16),'white').save(image,format='PNG')
        encoded=base64.b64encode(image.getvalue()).decode()
        with TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                for service,minimum in (('flux-building',1),('flux-prop',0),('flux-vegetation',0)):
                    with self.subTest(service=service):
                        response=client.get('/management/assistant/flux-defaults/'+service)
                        self.assertEqual(response.status_code,200)
                        profile=response.json();self.assertEqual(profile['minimum'],minimum)
                        payload={'action':'generate','prompt':profile['prompt'] or 'wooden house','width':profile['width'],'height':profile['height'],'steps':16,'seed':42,'images':[]}
                        manager=FluxImageGenerationManager(service)
                        if minimum:
                            with self.assertRaises(ValueError):manager.validate_generation_request(payload)
                        else:
                            self.assertTrue(profile['prompt'])
                            self.assertEqual(manager.validate_generation_request(payload)['profile'],service)
                        payload['images']=[encoded]
                        self.assertEqual(manager.validate_generation_request(payload)['profile'],service)
