"""상태 자동 갱신은 삭제된 작업 추적만 해제하고 실제 오류를 보존한다."""
import unittest
from unittest.mock import Mock, patch
from tools.management.common.generation_status_lookup import read_existing_generation_status


class GenerationStatusLookupTests(unittest.TestCase):
    def test_malformed_history_never_marks_job_deleted(self):
        for current_history_response in (None, {}, {'records':{}}, {'records':''}, {'records':None}, {'records':[None]}, {'records':[{}]}, {'records':[{'id':42}]}, {'records':[{'id':' '}]}, {'records':[{'id':'existing'},{}]}):
            with self.subTest(response=current_history_response):
                current_status_error = ValueError('상태 조회 실패')
                current_command_mock = Mock(side_effect=[current_status_error,current_history_response])
                with self.assertRaisesRegex(ValueError,'이력 조회 응답') as current_raised_error:
                    read_existing_generation_status(current_command_mock,'existing')
                self.assertIs(current_raised_error.exception.__cause__,current_status_error)

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

    def test_qwen_variants_use_shared_history_refresh(self):
        from tools.management.ui.gradio import qwen_2511_app
        for current_mode_options in ({}, {'qwen21_mode_enabled': True}, {'qwen21_mode_enabled': True, 'circular_mode_enabled': True}, {'expression_mode_enabled': True}):
            with self.subTest(options=current_mode_options):
                current_interface_blocks = qwen_2511_app.build_qwen_2511_interface('http://127.0.0.1:9988', **current_mode_options)
                current_refresh_binding = next(current_binding for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__ == 'refresh_combined_history')
                with patch.object(qwen_2511_app, 'execute_management_command', side_effect=[ValueError('missing'), {'records': []}]):
                    current_output_values = current_refresh_binding.fn('removed', 'removed', True, {})
                self.assertIn('삭제', current_output_values[4])
                self.assertEqual(current_output_values[5], '')
                self.assertFalse(current_output_values[6]['visible'])
                self.assertEqual(current_output_values[7], {})
                current_status_record = {'status': 'running', 'estimate': {'remaining': 12}, 'metrics': {'gpu_observations': {'GPU-test': {'process_current_mib': 120, 'process_peak_mib': 7123, 'scope': '작업자'}}}}
                with patch.object(qwen_2511_app, 'execute_management_command', return_value=current_status_record):
                    current_output_values = current_refresh_binding.fn('existing', 'existing', False, {})
                self.assertIn('약 12초', current_output_values[4])
                self.assertIn('관측 피크 7123 MiB', current_output_values[4])

    def test_tile_history_and_stage_refresh_handle_deleted_job(self):
        from tools.management.ui.gradio import floor_tile_app, seamless_tile_app
        from tools.management.domains.tile.floor_generation import load_floor_configuration
        with patch.object(floor_tile_app, 'execute_floor_gateway', return_value=load_floor_configuration()) as current_gateway_mock:
            current_floor_interface = floor_tile_app.build_floor_interface('http://127.0.0.1:9988')
            current_floor_callback = next(current_binding.fn for current_binding in current_floor_interface.fns.values() if current_binding.fn and current_binding.fn.__name__ == 'refresh_combined_history')
            current_gateway_mock.side_effect = [ValueError('missing'), {'records': []}]
            current_output_values = current_floor_callback('removed', 'removed', True, {})
        self.assertIn('삭제', current_output_values[4])
        self.assertFalse(current_output_values[6]['visible'])
        current_seamless_interface = seamless_tile_app.build_seamless_interface('http://127.0.0.1:9988')
        current_refresh_binding = next(current_binding for current_binding in current_seamless_interface.fns.values() if current_binding.fn and current_binding.fn.__name__ == 'refresh_seamless_status')
        self.assertEqual(len(current_refresh_binding.outputs), 3)
        with patch.object(seamless_tile_app, 'execute_management_command', side_effect=[ValueError('missing'), {'records': []}]):
            current_output_values = current_refresh_binding.fn('removed')
        self.assertIn('삭제', current_output_values[0])
        self.assertFalse(current_output_values[1])
        self.assertFalse(current_output_values[2]['interactive'])
        with patch.object(seamless_tile_app, 'execute_management_command', return_value={'status': 'paused'}):
            current_output_values = current_refresh_binding.fn('existing')
        self.assertTrue(current_output_values[1])
        self.assertFalse(current_output_values[2]['interactive'])

    def test_direct_qwen_entrypoints_initialize_repository_imports(self):
        import os
        from pathlib import Path
        import subprocess
        import sys
        current_repository_root=Path(__file__).resolve().parents[3]
        current_process_environment=dict(os.environ)
        current_process_environment.pop('PYTHONPATH',None)
        for current_script_name in ('qwen_2511_app.py',):
            with self.subTest(script=current_script_name):
                current_process_result=subprocess.run([sys.executable,str(current_repository_root/'tools/management/ui/gradio'/current_script_name),'--help'],cwd='/tmp',env=current_process_environment,capture_output=True,text=True,timeout=15)
                self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
                self.assertIn('--review-port',current_process_result.stdout)
