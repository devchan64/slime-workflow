"""Qwen 2512 Gradio 클라이언트의 게이트웨이 계약을 검증한다."""
import unittest
from unittest.mock import patch

from tools.review.ui.gradio import qwen_2512_app


class Qwen2512GradioTests(unittest.TestCase):
    def test_generation_request_uses_fixed_contract(self):
        self.assertEqual(
            qwen_2512_app.build_generation_request('  misty forest  ',1024,768,4,251204),
            {'action':'generate','prompt':'misty forest','width':1024,'height':768,'steps':4,'seed':251204},
        )

    def test_gateway_targets_qwen_2512_service(self):
        with patch.object(qwen_2512_app,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(qwen_2512_app.execute_image_gateway('generate',{'prompt':'test'}),{'id':'sample'})
            gateway_call_value.assert_called_once_with('qwen-2512','generate',{'prompt':'test'})

    def test_prompt_word_count_and_result_preview(self):
        self.assertEqual(qwen_2512_app.count_prompt_words('  short scene prompt '),3)
        self.assertIn('/image-generation/jobs/sample/result.png',qwen_2512_app.create_result_preview_html('/image-generation/jobs/sample/result.png'))
