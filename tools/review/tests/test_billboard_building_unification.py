"""건물 호환 명령과 공용 빌보드 UI의 통합 계약."""
import unittest
import base64
import io
from types import SimpleNamespace
from unittest.mock import Mock
from PIL import Image

from tools.review.common.management_runtime import build_building_compatibility_handler
from tools.review.common.management_asgi import QWEN_INTERFACE_OPTIONS
from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface


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

    def test_one_interface_contains_both_guides(self):
        self.assertEqual(QWEN_INTERFACE_OPTIONS['building-generator'], QWEN_INTERFACE_OPTIONS['billboard-generator'])
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', **QWEN_INTERFACE_OPTIONS['billboard-generator'])
        current_component_records = current_interface_blocks.config['components']
        current_component_labels = [current_record.get('props', {}).get('label') for current_record in current_component_records]
        self.assertNotIn('건물 구도 프리셋', current_component_labels)
        self.assertIn('가이드 프리셋', current_component_labels)
        self.assertNotIn('건물 높이 · 건물 프리셋에만 적용', current_component_labels)
        self.assertIn('건물 기본 프롬프트 추가', current_component_labels)
        self.assertEqual(sum(current_record.get('props', {}).get('value') == '대기열에 추가' for current_record in current_component_records), 1)

    def test_unified_guide_applies_matching_prompt_and_reference(self):
        from tools.review.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES
        from tools.review.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', **QWEN_INTERFACE_OPTIONS['billboard-generator'])
        current_callback_value = next(current_function.fn for current_function in current_interface_blocks.fns.values() if current_function.fn and current_function.fn.__name__ == 'apply_billboard_guide_inputs')
        for current_profile_name in BILLBOARD_LAYOUT_PROFILES:
            current_image_value, current_prompt_text, current_building_enabled = current_callback_value(current_profile_name, 'stone house')
            self.assertTrue(current_image_value.size)
            self.assertFalse(current_building_enabled)
            self.assertIn('stone house', current_prompt_text)
        for current_profile_name in BUILDING_LAYOUT_PRESET_NAMES:
            for current_height_value in (80, 140, 200):
                current_image_value, current_prompt_text, current_building_enabled = current_callback_value('building:' + current_profile_name + ':' + str(current_height_value), 'stone house')
                self.assertTrue(current_image_value.size)
                self.assertTrue(current_building_enabled)
                if current_profile_name.split('-')[0] in ('4x4', '4x5', '4x6'):
                    self.assertIn('entrance spans two adjacent guide tiles', current_prompt_text)
                else:
                    self.assertEqual(current_prompt_text, 'stone house')

    def test_unified_service_requires_a_reference(self):
        from tools.review.domains.image.billboard_generation import BillboardGuideGenerationManager
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
