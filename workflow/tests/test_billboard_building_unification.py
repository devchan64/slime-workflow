"""건물 호환 명령과 공용 빌보드 UI의 통합 계약."""
import unittest
import base64
import io
from types import SimpleNamespace
from unittest.mock import Mock
from PIL import Image

from workflow.common.management_runtime import build_building_compatibility_handler


class BillboardBuildingUnificationTests(unittest.TestCase):
    def test_compatibility_routes_to_same_service_and_restores_request(self):
        current_service_mock = SimpleNamespace(handle_image_request=Mock(return_value=True))
        current_handler_value = SimpleNamespace(path='/building-generator/history?page=2')
        def record_current_path(current_request_value):
            self.assertEqual(current_request_value.path, '/billboard-generator/history?page=2')
            return True
        current_service_mock.handle_image_request.side_effect = record_current_path
        self.assertTrue(build_building_compatibility_handler(current_service_mock)(current_handler_value))
        self.assertEqual(current_handler_value.path, '/building-generator/history?page=2')

    def test_compatibility_restores_path_when_service_fails(self):
        current_service_mock = SimpleNamespace(handle_image_request=Mock(side_effect=ValueError('검증 오류')))
        current_handler_value = SimpleNamespace(path='/building-generator/jobs')
        with self.assertRaisesRegex(ValueError, '검증 오류'):
            build_building_compatibility_handler(current_service_mock)(current_handler_value)
        self.assertEqual(current_handler_value.path, '/building-generator/jobs')

    def test_flux_profiles_have_distinct_menus_and_guides(self):
        from http.server import SimpleHTTPRequestHandler
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        from workflow.common.management_catalog import REACT_REVIEW_PATHS
        self.assertNotEqual(REACT_REVIEW_PATHS['flux-building-generator'],REACT_REVIEW_PATHS['flux-billboard-generator'])
        with TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                building=client.get('/management/assistant/flux-defaults/flux-building').json()
                billboard=client.get('/management/assistant/flux-defaults/flux-billboard').json()
                self.assertTrue(building['guides'])
                self.assertTrue(billboard['layouts'])
                self.assertNotIn('layouts',building)
                self.assertNotIn('guides',billboard)

    def test_flux_guides_supply_matching_prompt_and_reference(self):
        from http.server import SimpleHTTPRequestHandler
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        from workflow.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES
        from workflow.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES
        with TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                for profile in BILLBOARD_LAYOUT_PROFILES:
                    with self.subTest(profile=profile):
                        response=client.post('/management/assistant/flux-billboard-guide',json={'layout':profile,'subject':'stone house'})
                        self.assertEqual(response.status_code,200,response.text)
                        data=response.json();self.assertIn('stone house',data['prompt'])
                        with Image.open(io.BytesIO(base64.b64decode(data['image']))) as image:self.assertGreater(image.width,0)
                for profile in BUILDING_LAYOUT_PRESET_NAMES:
                    with self.subTest(profile=profile):
                        response=client.get('/management/assistant/flux-building-guide/'+profile)
                        self.assertEqual(response.status_code,200)
                        with Image.open(io.BytesIO(response.content)) as image:self.assertEqual(image.size,(1024,1024))

    def test_unified_service_requires_a_reference(self):
        from workflow.domains.image.billboard_generation import BillboardGuideGenerationManager
        current_request_record = {'action':'generate', 'prompt':'building', 'images':[], 'width':512, 'height':512, 'steps':40, 'seed':10107}
        current_service_value = BillboardGuideGenerationManager()
        with self.assertRaisesRegex(ValueError, '참조 이미지'):
            current_service_value.validate_generation_request(current_request_record)
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (16, 16), 'white').save(current_image_buffer, format='PNG')
        current_request_record['images'] = [base64.b64encode(current_image_buffer.getvalue()).decode()]
        self.assertEqual(len(current_service_value.validate_generation_request(current_request_record)['images']), 1)


if __name__ == '__main__':
    unittest.main()
