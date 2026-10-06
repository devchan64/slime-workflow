"""Qwen 2512 Gradio 클라이언트의 게이트웨이 계약을 검증한다."""
import unittest
from unittest.mock import patch

from tools.review.ui.gradio import qwen_2512_app


class Qwen2512GradioTests(unittest.TestCase):
    def test_generation_request_uses_fixed_contract(self):
        self.assertEqual(
            qwen_2512_app.build_generation_request('  misty forest  ',' 돌온재 ',1024,768,4,251204),
            {'action':'generate','prompt':'misty forest','tag':'돌온재','width':1024,'height':768,'steps':4,'seed':251204},
        )

    def test_gateway_targets_qwen_2512_service(self):
        with patch.object(qwen_2512_app,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(qwen_2512_app.execute_image_gateway('generate',{'prompt':'test'}),{'id':'sample'})
            gateway_call_value.assert_called_once_with('qwen-2512','generate',{'prompt':'test'})

    def test_prompt_word_count_and_result_preview(self):
        self.assertEqual(qwen_2512_app.count_prompt_words('  short scene prompt '),3)
        self.assertEqual(qwen_2512_app.collect_generation_gallery('/image-generation/jobs/sample/result.png',server_base_address='http://localhost:8770'),[('http://localhost:8770/image-generation/jobs/sample/result.png','생성 원본')])

    def test_restore_generation_inputs_uses_historical_request(self):
        restored_input_values=qwen_2512_app.restore_generation_inputs({'request':{'prompt':'misty forest','tag':'돌온재','width':768,'height':1024,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('misty forest','돌온재',768,1024,30,42))
        self.assertEqual(restored_input_values[6],'최종 프롬프트: **2단어**')
