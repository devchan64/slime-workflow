"""F2V 폐기 후 실행 차단과 FL2V 독립성 검증."""
import unittest
from tools.review.domains.vace.first_frame_generation import VaceFirstFrameGenerationManager
from tools.review.ui.gradio.vace_first_frame_app import build_first_frame_interface


class RetiredFirstFrameTests(unittest.TestCase):
    def test_generation_and_resume_rejected(self):
        current_service_manager = VaceFirstFrameGenerationManager()
        for current_callback_value, current_argument_value in ((current_service_manager.validate_generation_request, {}), (current_service_manager.validate_generation_resume, None), (current_service_manager.select_generation_runner, None)):
            with self.assertRaisesRegex(ValueError, '폐기'):
                current_callback_value(current_argument_value)

    def test_retired_page_has_no_generation_controls(self):
        current_interface_blocks = build_first_frame_interface('http://127.0.0.1:8770')
        self.assertFalse(any(current_component['type'] in ('button', 'image', 'textbox') for current_component in current_interface_blocks.config['components']))
        self.assertIn('폐기', str(current_interface_blocks.config))
