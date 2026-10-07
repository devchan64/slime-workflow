"""커스텀 모션 입력의 서비스 검증과 GUI 전달 계약."""
import unittest
from unittest.mock import patch
from tools.review.domains.momask import momask_jobs
from tools.review.ui.gradio import momask_app

class CustomMotionTests(unittest.TestCase):
    def test_custom_rejects_empty_before_start(self):
        for invalid_prompt_text in (None, '', '  ', 42, 'a'*4001):
            with self.assertRaises(ValueError):
                momask_jobs.start_generation_job('custom',['down_left'],custom_prompt_text=invalid_prompt_text)

    def test_fixed_rejects_override(self):
        with self.assertRaises(ValueError):
            momask_jobs.start_generation_job('standing',['down_left'],custom_prompt_text='Different motion')

    def test_custom_input_roundtrip(self):
        custom_prompt_text='A person raises both arms slowly.'
        with patch.object(momask_app,'execute_motion_command',return_value={'id':'sample'}) as command_call_mock:
            momask_app.start_motion_generation('custom',['down_left'],True,'',custom_prompt_text)
            self.assertEqual(command_call_mock.call_args.args[1]['prompt'],custom_prompt_text)
        saved_status_record={'request':{'action':'custom','directions':['down_left'],'face':True,'prompt':custom_prompt_text},'prompt':custom_prompt_text,'prompt_word_count':7}
        with patch.object(momask_app,'execute_motion_command',return_value=saved_status_record):
            restored_input_values=momask_app.restore_saved_motion_inputs('sample')
            self.assertEqual(restored_input_values[4]['value'],custom_prompt_text)
            self.assertTrue(restored_input_values[4]['interactive'])

    def test_frame_count_validation_and_restore(self):
        for invalid_frame_count in (0, 7, 9, 12.5, True, '24'):
            with self.assertRaises(ValueError):
                momask_jobs.start_generation_job('standing',['down_left'],requested_frame_count=invalid_frame_count)
        self.assertEqual(momask_jobs.resolve_motion_frame_count('standing',24),24)
        with patch.object(momask_app,'execute_motion_command',return_value={'id':'sample'}) as current_command_mock:
            momask_app.start_motion_generation('standing',['down_left'],True,'',None,24)
            self.assertEqual(current_command_mock.call_args.args[1]['frames'],24)
        current_saved_status={'request':{'action':'standing','directions':['down_left'],'face':True,'frames':24},'prompt':None,'prompt_word_count':None}
        with patch.object(momask_app,'execute_motion_command',return_value=current_saved_status):
            self.assertEqual(momask_app.restore_saved_motion_inputs('sample')[-1],24)
