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

    def test_generation_rejects_invalid_numbers_without_coercion(self):
        for current_parameter_index in (2, 3, 4, 5):
            for current_invalid_value in (True, '512', 512.5, None):
                current_input_values = ['forest', '', 512, 512, 4, 42]
                current_input_values[current_parameter_index] = current_invalid_value
                with self.subTest(index=current_parameter_index, value=current_invalid_value):
                    with patch.object(qwen_2512_app, 'execute_image_gateway') as current_gateway_mock:
                        with self.assertRaises(ValueError):
                            qwen_2512_app.build_generation_request(*current_input_values)
                        current_gateway_mock.assert_not_called()

    def test_gateway_targets_qwen_2512_service(self):
        with patch.object(qwen_2512_app,'execute_management_command',return_value={'id':'sample'}) as gateway_call_value:
            self.assertEqual(qwen_2512_app.execute_image_gateway('generate',{'prompt':'test'}),{'id':'sample'})
            gateway_call_value.assert_called_once_with('qwen-2512','generate',{'prompt':'test'})

    def test_prompt_word_count_and_result_preview(self):
        self.assertEqual(qwen_2512_app.count_prompt_words('  short scene prompt '),3)
        self.assertEqual(qwen_2512_app.collect_generation_gallery('/image-generation/jobs/sample/result.png',server_base_address='http://localhost:8770'),[('http://localhost:8770/image-generation/jobs/sample/result.png','생성 원본')])

    def test_restore_generation_inputs_uses_historical_request(self):
        restored_input_values=qwen_2512_app.restore_generation_inputs({'request':{'prompt':'misty forest','tag':'돌온재','width':640,'height':960,'steps':30,'seed':42}})
        self.assertEqual(restored_input_values[:6],('misty forest','돌온재',640,960,30,42))
        self.assertEqual(restored_input_values[6],'최종 프롬프트: **2단어**')

    def test_restore_rejects_malformed_history_before_component_updates(self):
        malformed_history_records = [None, {'request': None}, {'request': {'prompt': 42}}, {'request': {'tag': []}}]
        malformed_history_records.extend({'request': {current_setting_name: current_invalid_value}}
            for current_setting_name in ('width', 'height', 'steps', 'seed')
            for current_invalid_value in (True, '42', None))
        for current_history_record in malformed_history_records:
            with self.subTest(record=current_history_record):
                with self.assertRaises(qwen_2512_app.gr.Error):
                    qwen_2512_app.restore_generation_inputs(current_history_record)

    def test_restore_rejects_settings_outside_service_contract(self):
        current_valid_request = {'prompt': 'misty forest', 'width': 768, 'height': 1024, 'steps': 30, 'seed': 42}
        for current_invalid_fields in ({'prompt': ''}, {'width': 255}, {'height': 513}, {'steps': 99}, {'seed': -1}, {'seed': 4294967296}):
            with self.subTest(fields=current_invalid_fields):
                with self.assertRaises(qwen_2512_app.gr.Error):
                    qwen_2512_app.restore_generation_inputs({'request': {**current_valid_request, **current_invalid_fields}})

    def test_status_lookup_failure_preserves_outputs_and_recovers(self):
        current_interface_blocks = qwen_2512_app.build_qwen_2512_interface('http://localhost')
        current_refresh_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values()
            if current_function.fn and current_function.fn.__name__ == 'refresh_generation_status')
        for current_error_type in (ValueError, RuntimeError, OSError):
            with self.subTest(error=current_error_type):
                with patch.object(qwen_2512_app, 'read_existing_generation_status', side_effect=current_error_type('격리 연결 오류')):
                    current_output_values = current_refresh_callback('saved-job', True)
                self.assertIn('상태 조회 실패', current_output_values[0])
                self.assertEqual(current_output_values[1:], (qwen_2512_app.gr.skip(),)*3)
        with patch.object(qwen_2512_app, 'read_existing_generation_status', return_value={'status':'completed','log':'복구 로그'}):
            current_output_values = current_refresh_callback('saved-job', True)
            self.assertIn('완료', current_output_values[0])
            self.assertEqual(current_output_values[1]['value'], '복구 로그')
        with patch.object(qwen_2512_app, 'read_existing_generation_status', return_value=None):
            current_output_values = current_refresh_callback('saved-job', True)
            self.assertIn('삭제되었습니다', current_output_values[0])
            self.assertEqual(current_output_values[3], '')
