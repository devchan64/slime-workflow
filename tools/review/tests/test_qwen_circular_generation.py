"""순환 생성기의 게이트웨이·설정 분리 검증."""
import unittest
from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request
from generators.image.qwen_21_circular import CIRCULAR_DEFAULT_PROMPT, CIRCULAR_VAE_CONFIGURATION
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS

class CircularGenerationTests(unittest.TestCase):
    def test_circular_request_isolation(self):
        current_input_record = {'action':'generate','prompt':CIRCULAR_DEFAULT_PROMPT,'images':[], 'tag':'', 'width':768,'height':768,'steps':40,'seed':10107}
        current_service_manager = QwenCircularGenerationManager()
        current_output_record = current_service_manager.validate_generation_request(current_input_record)
        self.assertEqual(current_output_record['circular_vae'], CIRCULAR_VAE_CONFIGURATION)
        self.assertEqual(current_output_record['prompt'], CIRCULAR_DEFAULT_PROMPT)
        self.assertNotIn('circular_vae', validate_qwen_plain_request(current_input_record))
        self.assertEqual(current_service_manager.route_prefix_value, MANAGEMENT_SERVICE_ROUTES['qwen-21-circular'])
        self.assertIn('resume', MANAGEMENT_SERVICE_COMMANDS['qwen-21-circular'])
        self.assertEqual(current_service_manager.job_storage_root.name, 'qwen-image-21-circular')

    def test_history_renderer_contract_and_partial_results(self):
        from tools.review.ui.gradio.qwen_2511_app import render_circular_comparison
        completed_result_html = render_circular_comparison('example-id', {
            'image':'/jobs/example-id/result.png',
            'baseline':'/jobs/example-id/baseline.png',
            'baseline-preview':'/jobs/example-id/baseline-preview.png',
        }, 'http://localhost:8770')
        for expected_image_name in ('result.png','tiled-preview.png','baseline.png','baseline-preview.png'):
            self.assertIn(expected_image_name, completed_result_html)
        partial_result_html = render_circular_comparison('example-id', {
            'status':'failed', 'baseline':'/jobs/example-id/baseline.png',
        }, 'http://localhost:8770')
        self.assertIn('/baseline.png', partial_result_html)
        self.assertNotIn('/baseline-preview.png', partial_result_html)
        self.assertNotIn('/tiled-preview.png', partial_result_html)
        self.assertIn('저장된 결과', render_circular_comparison('example-id', {}, 'http://localhost:8770'))
