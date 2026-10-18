"""F2V는 첫 프레임 보존 조건과 공용 대기열 계약을 사용한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.vace.timeline import validate_timeline_request, assemble_timeline_inputs
from tools.review.ui.gradio.vace_first_frame_app import build_first_frame_payload, build_first_frame_interface, restore_first_frame_inputs


class VaceFirstFrameTests(unittest.TestCase):
    def test_first_frame_mask_and_payload(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            current_image_path = current_directory_path / 'arbitrary-name.png'
            Image.new('RGB', (832, 480), 'red').save(current_image_path)
            current_payload_record = build_first_frame_payload(str(current_image_path), '걷는다', '', 5, 42, 50, 3, 5, 1, '#FFFFFF')
            current_saved_record = validate_timeline_request(current_payload_record)
            self.assertEqual(current_saved_record['frame_entries'], [{'frame': 0, 'editable': False}])
            self.assertEqual(current_saved_record.get('identity_reference_count', 0), 0)
            current_saved_record['references'] = ['arbitrary-name.png']
            current_video_frames, current_mask_frames = assemble_timeline_inputs(current_directory_path, current_saved_record)
            self.assertEqual(current_video_frames[0].getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(current_mask_frames[0].getextrema(), ((0, 0),) * 3)
            self.assertTrue(all(current_mask_image.getextrema() == ((255, 255),) * 3 for current_mask_image in current_mask_frames[1:]))

    def test_other_timeline_restore_rejected(self):
        current_saved_inputs = (['test.png'], [[1, True]], '걷는다', '', 81, 42, '832×480', 50, 3, 5, 1, None, '#FFFFFF', ['test.png'], 'id')
        with patch('tools.review.ui.gradio.vace_first_frame_app.restore_timeline_inputs', return_value=current_saved_inputs):
            with self.assertRaises(Exception):
                restore_first_frame_inputs({'id': 'id'})

    def test_interface_requires_confirmation(self):
        current_interface_blocks = build_first_frame_interface('http://127.0.0.1:8770')
        current_component_values = [current_component['props'].get('value') for current_component in current_interface_blocks.config['components']]
        self.assertIn('대기열에 추가', current_component_values)
        self.assertIn('확인 후 대기열에 추가', current_component_values)
        self.assertIn('추가하지 않기', current_component_values)

    def test_independent_service_storage_and_gateway(self):
        from tools.review.domains.vace.first_frame_generation import VaceFirstFrameGenerationManager
        from tools.review.domains.vace.timeline_generation import VaceTimelineGenerationManager
        from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS
        current_first_service = VaceFirstFrameGenerationManager()
        current_video_service = VaceTimelineGenerationManager()
        self.assertNotEqual(current_first_service.job_storage_root, current_video_service.job_storage_root)
        self.assertNotEqual(current_first_service.history_storage_path(), current_video_service.history_storage_path())
        self.assertEqual(current_first_service.select_generation_runner(), 'generators/vace/first_frame_worker.py')
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['wan21-vace-f2v'], '/wan21-vace-f2v')
        self.assertIn('prioritize', MANAGEMENT_SERVICE_COMMANDS['wan21-vace-f2v'])

    def test_gui_dispatches_only_to_first_frame_service(self):
        from tools.review.ui.gradio.vace_first_frame_app import execute_first_frame_command
        with patch('tools.review.ui.gradio.vace_first_frame_app.execute_remote_management_command') as current_gateway_mock:
            execute_first_frame_command('history', {})
            current_gateway_mock.assert_called_once_with('wan21-vace-f2v', 'history', {})

    def test_backend_rejects_editable_first_frame(self):
        from generators.vace.first_frame import validate_first_frame_request
        with self.assertRaisesRegex(ValueError, '보존'):
            validate_first_frame_request({'frame_entries': [{'frame': 0, 'editable': True}]})
