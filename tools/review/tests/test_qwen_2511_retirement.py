"""Qwen Image Edit 2511 생성·재개 진입점 폐기 계약."""
import unittest
from tools.review.common.management_gateway import resolve_management_command
from tools.review.domains.image.image_generation import ImageGenerationManager


class Qwen2511RetirementTests(unittest.TestCase):
    def test_gateway_rejects_retired_service(self):
        for current_command_name in ('generate', 'resume', 'history', 'status'):
            with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('qwen-2511', current_command_name, {})

    def test_legacy_service_rejects_generation_and_resume_runtime(self):
        current_manager_value = ImageGenerationManager(three_reference_mode=True)
        with self.assertRaisesRegex(ValueError, '폐기'):
            current_manager_value.validate_generation_request({'action': 'generate'})
        with self.assertRaisesRegex(ValueError, '폐기'):
            current_manager_value.validate_generation_runtime({})


if __name__ == '__main__':
    unittest.main()
