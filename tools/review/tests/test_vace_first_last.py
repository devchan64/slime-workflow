"""FL2V의 양끝 보존·입력 복원·독립 서비스 계약 검증."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.vace.first_last import validate_first_last_request
from generators.vace.timeline import assemble_timeline_inputs
from tools.review.ui.gradio.vace_first_last_app import build_first_last_payload, build_first_last_interface, restore_first_last_inputs, execute_first_last_command


class VaceFirstLastTests(unittest.TestCase):
    def test_endpoints_preserved_and_middle_generated(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            current_first_path = current_directory_path / 'first.png'
            current_last_path = current_directory_path / 'last.png'
            Image.new('RGB', (832, 480), 'red').save(current_first_path)
            Image.new('RGB', (832, 480), 'blue').save(current_last_path)
            for current_frame_count in (5, 81, 161):
                current_payload_record = build_first_last_payload(str(current_first_path), str(current_last_path), '걷는다', '', current_frame_count, 42, 50, 3, 5, 1, '#FFFFFF')
                current_saved_record = validate_first_last_request(current_payload_record)
                current_saved_record['references'] = ['first.png', 'last.png']
                current_video_frames, current_mask_frames = assemble_timeline_inputs(current_directory_path, current_saved_record)
                self.assertEqual(len(current_video_frames), current_frame_count)
                self.assertEqual(current_video_frames[0].getpixel((0, 0)), (255, 0, 0))
                self.assertEqual(current_video_frames[-1].getpixel((0, 0)), (0, 0, 255))
                self.assertEqual(current_mask_frames[0].getextrema(), ((0, 0),) * 3)
                self.assertEqual(current_mask_frames[-1].getextrema(), ((0, 0),) * 3)
                self.assertTrue(all(current_mask_image.getextrema() == ((255, 255),) * 3 for current_mask_image in current_mask_frames[1:-1]))

    def test_invalid_endpoints_rejected(self):
        for current_frame_entries in ([], [{'frame': 0, 'editable': False}], [{'frame': 0, 'editable': False}, {'frame': 3, 'editable': False}], [{'frame': 0, 'editable': False}, {'frame': 4, 'editable': True}]):
            with self.assertRaises(ValueError):
                validate_first_last_request({'frames': 5, 'frame_entries': current_frame_entries})
        with self.assertRaises(ValueError):
            validate_first_last_request({'frames': 1})
        with self.assertRaises(ValueError):
            build_first_last_payload('first.png', None, '걷는다', '', 81, 42, 50, 3, 5, 1, '#FFFFFF')

    def test_restore_roundtrip_and_reject_foreign_layout(self):
        current_saved_inputs = (['first.png', 'last.png'], [[1, False], [81, False]], '걷는다', '', 81, 42, '832×480', 50, 3, 5, 1, None, '#FFFFFF', ['first.png', 'last.png'], 'id')
        with patch('tools.review.ui.gradio.vace_first_last_app.restore_timeline_inputs', return_value=current_saved_inputs):
            current_restored_values = restore_first_last_inputs({'id': 'id'})
            self.assertEqual(current_restored_values, ('first.png', 'last.png', '걷는다', '', 81, 42, 50, 3, 5, 1, '#FFFFFF', 'id'))
        with patch('tools.review.ui.gradio.vace_first_last_app.restore_timeline_inputs', return_value=(current_saved_inputs[0], [[1, False]], *current_saved_inputs[2:])):
            with self.assertRaises(Exception):
                restore_first_last_inputs({'id': 'id'})

    def test_service_and_interface_contract(self):
        from tools.review.domains.vace.first_last_generation import VaceFirstLastGenerationManager
        from tools.review.domains.vace.first_frame_generation import VaceFirstFrameGenerationManager
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        current_service_manager = VaceFirstLastGenerationManager()
        self.assertNotEqual(current_service_manager.job_storage_root, VaceFirstFrameGenerationManager().job_storage_root)
        self.assertEqual(current_service_manager.select_generation_runner(), 'generators/vace/first_last_worker.py')
        self.assertIn('prioritize', MANAGEMENT_SERVICE_COMMANDS['wan21-vace-fl2v'])
        with patch('tools.review.ui.gradio.vace_first_last_app.execute_remote_management_command') as current_gateway_mock:
            execute_first_last_command('history', {})
            current_gateway_mock.assert_called_once_with('wan21-vace-fl2v', 'history', {})
        current_interface_blocks = build_first_last_interface('http://127.0.0.1:8770')
        current_component_props = [current_component['props'] for current_component in current_interface_blocks.config['components']]
        self.assertEqual(sum(current_component.get('label', '').endswith('프레임 이미지 · 필수 1장') for current_component in current_component_props), 2)
        self.assertIn('확인 후 대기열에 추가', [current_component.get('value') for current_component in current_component_props])

    def test_confirmation_cancel_and_single_mock_submission(self):
        with patch('tools.review.ui.gradio.vace_first_last_app.execute_remote_management_command', return_value={'id': 'mock-job'}) as current_gateway_mock, patch('tools.review.ui.gradio.vace_first_last_app.build_first_last_payload', return_value={'frames': 81}) as current_payload_mock:
            current_interface_blocks = build_first_last_interface('http://127.0.0.1:8770')
            current_function_lookup = {}
            for current_function in current_interface_blocks.fns.values():
                current_function_lookup.setdefault(current_function.name, current_function.fn)
            current_input_values = ('first.png', 'last.png', '걷는다', '', 81, 42, 50, 3, 5, 1, '#FFFFFF')
            current_pending_values, current_group_update, _ = current_function_lookup['prepare_generation_confirmation'](*current_input_values)
            self.assertTrue(current_group_update['visible'])
            current_gateway_mock.assert_not_called()
            current_cancel_result = current_function_lookup['cancel_generation_confirmation'](current_pending_values, 'first.png', 'last.png', '걷는다')
            self.assertFalse(current_cancel_result[1]['visible'])
            with self.assertRaises(Exception):
                list(current_function_lookup['execute_confirmed_generation'](current_pending_values))
            current_gateway_mock.assert_not_called()
            current_pending_values, _, _ = current_function_lookup['prepare_generation_confirmation'](*current_input_values)
            self.assertEqual(list(current_function_lookup['execute_confirmed_generation'](current_pending_values))[0][0], 'mock-job')
            current_gateway_mock.assert_called_once_with('wan21-vace-fl2v', 'generate', {'frames': 81})
            current_payload_mock.assert_called_once_with(*current_input_values)
            with self.assertRaises(Exception):
                list(current_function_lookup['execute_confirmed_generation'](current_pending_values))
