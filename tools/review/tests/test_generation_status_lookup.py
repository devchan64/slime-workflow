"""상태 자동 갱신은 삭제된 작업 추적만 해제하고 실제 오류를 보존한다."""
import unittest
from unittest.mock import Mock, patch
from tools.review.common.generation_status_lookup import read_existing_generation_status


class GenerationStatusLookupTests(unittest.TestCase):
    def test_success_does_not_read_history(self):
        current_status_record = {'status':'running'}
        current_command_mock = Mock(return_value=current_status_record)
        self.assertIs(read_existing_generation_status(current_command_mock,'existing'),current_status_record)
        current_command_mock.assert_called_once_with('status',{'id':'existing'})

    def test_missing_job_and_service_errors_remain_distinct(self):
        current_command_mock = Mock(side_effect=[ValueError('missing'),{'records':[]}])
        self.assertIsNone(read_existing_generation_status(current_command_mock,'removed'))
        for current_failure_responses in ([ValueError('corrupt'),{'records':[{'id':'existing'}]}], [ValueError('status failed'),RuntimeError('gateway unavailable')]):
            with self.subTest(responses=current_failure_responses):
                with self.assertRaises((ValueError,RuntimeError)):
                    read_existing_generation_status(Mock(side_effect=current_failure_responses),'existing')

    def test_video_callbacks_clear_deleted_job_and_preserve_existing_errors(self):
        from tools.review.ui.gradio import phantom_app, vace_timeline_app
        for current_module_value,current_builder_name,current_callback_name,current_command_name in (
            (phantom_app,'build_phantom_interface','refresh_phantom_result','execute_phantom_command'),
            (vace_timeline_app,'build_timeline_interface','refresh_timeline_result','execute_timeline_command'),
        ):
            with self.subTest(module=current_module_value.__name__):
                current_interface_blocks = getattr(current_module_value,current_builder_name)('http://127.0.0.1:9988')
                current_refresh_binding = next(current_binding for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__==current_callback_name)
                self.assertEqual(len(current_refresh_binding.outputs),5)
                self.assertEqual(current_refresh_binding.outputs[-1].label,'생성 ID')
                with patch.object(current_module_value,current_command_name,side_effect=[ValueError('missing'),{'records':[]}]):
                    current_output_values = current_refresh_binding.fn('removed',True,'old.mp4')
                self.assertEqual(len(current_output_values),5)
                self.assertIn('삭제',current_output_values[0])
                self.assertNotIn('old.mp4',current_output_values[1])
                self.assertEqual(current_output_values[2:],('','',''))
                with patch.object(current_module_value,current_command_name,side_effect=[ValueError('corrupt'),{'records':[{'id':'existing'}]}]):
                    with self.assertRaisesRegex(ValueError,'corrupt'):
                        current_refresh_binding.fn('existing',True,'old.mp4')
                with patch.object(current_module_value,current_command_name,return_value={'status':'running','video':''}):
                    current_output_values=current_refresh_binding.fn('existing',False,'')
                self.assertEqual(len(current_output_values),5)
                self.assertEqual(current_output_values[-1],{'__type__':'update'})

    def test_qwen_variants_clear_deleted_preview_and_keep_telemetry(self):
        from tools.review.ui.gradio import qwen_2511_app, qwen_2512_app
        current_interface_cases=[(qwen_2512_app,qwen_2512_app.build_qwen_2512_interface,{},'refresh_generation_status')]
        current_interface_cases += [(qwen_2511_app,qwen_2511_app.build_qwen_2511_interface,current_mode_options,'refresh_status') for current_mode_options in ({},{'qwen21_mode_enabled':True},{'qwen21_mode_enabled':True,'circular_mode_enabled':True},{'qwen21_mode_enabled':True,'pose_transfer_enabled':True},{'qwen21_mode_enabled':True,'outfit_transfer_enabled':True},{'expression_mode_enabled':True})]
        for current_module_value,current_builder_callback,current_mode_options,current_callback_name in current_interface_cases:
            with self.subTest(module=current_module_value.__name__,options=current_mode_options):
                current_interface_blocks=current_builder_callback('http://127.0.0.1:9988',**current_mode_options)
                current_refresh_binding=next(current_binding for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__==current_callback_name)
                self.assertEqual(len(current_refresh_binding.outputs),4)
                with patch.object(current_module_value,'execute_management_command',side_effect=[ValueError('missing'),{'records':[]}]):
                    current_output_values=current_refresh_binding.fn('removed',True)
                self.assertIn('삭제',current_output_values[0])
                self.assertEqual(current_output_values[1],'')
                self.assertEqual(current_output_values[2]['value'],[])
                self.assertFalse(current_output_values[2]['visible'])
                self.assertEqual(current_output_values[3],'')
                current_status_record={'status':'running','estimate':{'remaining':12},'metrics':{'gpu_observations':{'GPU-test':{'process_current_mib':120,'process_peak_mib':7123,'scope':'작업자'}}}}
                with patch.object(current_module_value,'execute_management_command',return_value=current_status_record):
                    current_output_values=current_refresh_binding.fn('existing',False)
                self.assertIn('약 12초',current_output_values[0])
                self.assertIn('관측 피크 7123 MiB',current_output_values[0])
                self.assertEqual(current_output_values[-1],{'__type__':'update'})
