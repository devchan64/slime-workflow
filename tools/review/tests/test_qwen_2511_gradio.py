"""Qwen 2511 Gradio 입력·이력 복원 계약을 검증한다."""
import unittest

from tools.review.ui.gradio import qwen_2511_app


class Qwen2511GradioTests(unittest.TestCase):
    def test_reference_request_trims_history_tag(self):
        request_payload_value=qwen_2511_app.build_reference_request('마을 입구',' 돌온재 ',[],512,768,4,10107)
        self.assertEqual(request_payload_value['tag'],'돌온재')

    def test_restore_reference_inputs_uses_saved_settings_without_files(self):
        restored_input_values=qwen_2511_app.restore_reference_inputs({'request':{'prompt':'마을 입구','tag':'돌온재','width':512,'height':768,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('마을 입구','돌온재',512,768,30,42))
        self.assertIn('참조 이미지',restored_input_values[-1])
