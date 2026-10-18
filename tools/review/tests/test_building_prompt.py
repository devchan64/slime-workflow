"""건물 페이지의 필수 참조·단어 제한 및 공용 UI 연결 검증."""
import unittest
from tools.review.domains.image.building_prompt import load_building_base_prompt, check_building_input_readiness


class BuildingPromptContractTests(unittest.TestCase):
    def test_building_service_isolation(self):
        from tools.review.domains.image.building_generation import BuildingGenerationManager
        from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from tools.review.domains.image.three_reference_generation import validate_three_reference_job_path
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_building_manager = BuildingGenerationManager()
        current_general_manager = QwenPlainGenerationManager()
        self.assertNotEqual(current_building_manager.job_storage_root, current_general_manager.job_storage_root)
        self.assertNotEqual(current_building_manager.history_storage_path(), current_general_manager.history_storage_path())
        self.assertEqual(validate_three_reference_job_path(current_building_manager.job_storage_root), current_building_manager.job_storage_root)
        self.assertIn('prioritize', MANAGEMENT_SERVICE_COMMANDS['building-generator'])
        self.assertIn('history-delete', MANAGEMENT_SERVICE_COMMANDS['building-generator'])

    def test_asset_generator_storage_isolation(self):
        from tools.review.domains.image.prop_generation import PropGenerationManager
        from tools.review.domains.image.vegetation_generation import VegetationGenerationManager
        from tools.review.domains.image.building_generation import BuildingGenerationManager
        from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from tools.review.domains.image.three_reference_generation import validate_three_reference_job_path
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_managers = [PropGenerationManager(), VegetationGenerationManager(), BuildingGenerationManager(), QwenPlainGenerationManager()]
        self.assertEqual(len({current_service_manager.job_storage_root for current_service_manager in current_service_managers}), 4)
        self.assertEqual(len({current_service_manager.history_storage_path() for current_service_manager in current_service_managers}), 4)
        for current_service_manager in current_service_managers:
            self.assertEqual(validate_three_reference_job_path(current_service_manager.job_storage_root), current_service_manager.job_storage_root)
        for current_service_name in ('prop-generator', 'vegetation-generator'):
            self.assertEqual(MANAGEMENT_SERVICE_COMMANDS[current_service_name], MANAGEMENT_SERVICE_COMMANDS['qwen-21'])

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
        self.assertFalse(check_building_input_readiness('wooden guild hall', True, False, object(), True))

    def test_building_interface_contract(self):
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, building_mode_enabled=True)
        current_component_records = current_interface_blocks.config['components']
        self.assertTrue(any(current_component_record['props'].get('label') == '레이아웃 이미지 · 필수 (투영·바닥·출입구)' for current_component_record in current_component_records))
        current_generate_button = next(current_component_record for current_component_record in current_component_records if current_component_record['props'].get('value') == '대기열에 추가')
        self.assertFalse(current_generate_button['props']['interactive'])
        with self.assertRaises(ValueError):
            build_qwen_2511_interface('http://127.0.0.1:8770', building_mode_enabled=True)

    def test_prop_page_uses_optional_references(self):
        from tools.review.domains.image.building_prompt import load_prop_base_prompt
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface, check_plain_prompt_readiness
        current_prompt_text = load_prop_base_prompt()
        self.assertTrue(check_plain_prompt_readiness(current_prompt_text, False, False))
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, prop_mode_enabled=True)
        current_component_records = current_interface_blocks.config['components']
        self.assertTrue(any(current_component_record['props'].get('label') == '기물 레이아웃·외형 참조 1 · 선택' for current_component_record in current_component_records))
        self.assertTrue(any(current_component_record['props'].get('value') == '기물 기본 프롬프트 복원' for current_component_record in current_component_records))
        with self.assertRaises(ValueError):
            build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, building_mode_enabled=True, prop_mode_enabled=True)

    def test_vegetation_page_contract(self):
        from tools.review.domains.image.building_prompt import load_vegetation_base_prompt
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface, check_plain_prompt_readiness
        current_prompt_text = load_vegetation_base_prompt()
        self.assertTrue(check_plain_prompt_readiness(current_prompt_text, False, False))
        self.assertFalse(check_plain_prompt_readiness(current_prompt_text + ' plant' * 100, False, False))
        current_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, vegetation_mode_enabled=True)
        current_component_records = current_interface_blocks.config['components']
        self.assertTrue(any(current_component_record['props'].get('label') == '식생 레이아웃·식물 참조 1 · 선택' for current_component_record in current_component_records))
        self.assertTrue(any(current_component_record['props'].get('value') == '식생 기본 프롬프트 복원' for current_component_record in current_component_records))
        with self.assertRaises(ValueError):
            build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, prop_mode_enabled=True, vegetation_mode_enabled=True)
