"""VNCCS 출력의 입력·공용 명령·이력·다운로드 계약."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from generators.hy_motion.vnccs_contract import load_vnccs_config, validate_vnccs_request
from tools.review.tests import test_hy_motion
from tools.review.domains.hy_motion import jobs
from tools.review.common.management_gateway import execute_gateway_arguments, MANAGEMENT_SERVICE_COMMANDS


class VnccsInputContractTests(unittest.TestCase):
    def test_fixed_projection_configuration(self):
        import yaml
        current_config_record = load_vnccs_config()
        self.assertEqual(current_config_record['projections'], ['orthographic', 'perspective'])
        self.assertEqual(current_config_record['perspective_fov_degrees'], 30)
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_config_path = Path(current_temporary_directory) / 'config.yaml'
            for current_invalid_fields in ({'projections': ['perspective']}, {'perspective_fov_degrees': True}, {'perspective_fov_degrees': 45}):
                current_config_path.write_text(yaml.safe_dump({**current_config_record, **current_invalid_fields}))
                with patch('generators.hy_motion.vnccs_contract.VNCCS_EXPORT_CONFIG', current_config_path), self.assertRaises(ValueError):
                    load_vnccs_config()

    def test_pose_background_composition(self):
        from PIL import Image
        from generators.hy_motion.vnccs_export import write_pose_reference
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path = Path(current_temporary_directory) / 'pose.png'
            current_output_path = Path(current_temporary_directory) / 'pose-rgb.png'
            current_source_image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            current_source_image.putpixel((256, 256), (100, 120, 140, 255))
            current_source_image.putpixel((255, 256), (0, 0, 0, 128))
            current_source_image.save(current_source_path)
            write_pose_reference(current_source_path, current_output_path, 512)
            with Image.open(current_output_path) as current_output_image:
                self.assertEqual(current_output_image.mode, 'RGB')
                self.assertEqual(current_output_image.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(current_output_image.getpixel((256, 256)), (100, 120, 140))
                self.assertEqual(current_output_image.getpixel((255, 256)), (127, 127, 127))
            with self.assertRaises(ValueError):
                write_pose_reference(current_source_path, current_output_path, 256)
            Image.new('RGBA', (512, 512)).save(current_source_path)
            with self.assertRaises(ValueError):
                write_pose_reference(current_source_path, current_output_path, 512)

    def test_strict_export_inputs(self):
        self.assertEqual(load_vnccs_config()['resolution'], 512)
        self.assertEqual(validate_vnccs_request({'source_id': 'source'}, 300)['end_frame'], 300)
        for current_invalid_fields in ({'start_frame': True}, {'end_frame': 301}, {'start_frame': 5, 'end_frame': 4}, {'frame_step': 0}, {'directions': []}, {'directions': ['down_left'] * 2}, {'directions': ['other']}, {'model': 'other'}, {'source_id': ''}):
            with self.subTest(fields=current_invalid_fields), self.assertRaises(ValueError):
                validate_vnccs_request({'source_id': 'source', **current_invalid_fields}, 300)
        with self.assertRaises(ValueError):
            validate_vnccs_request({'source_id': 'source'}, 361)

    def test_gui_cli_export_contract(self):
        from tools.review.ui.gradio.hy_motion_app import start_vnccs_export
        current_payload_record = {'source_id': 'source', 'start_frame': 1, 'end_frame': 300, 'frame_step': 100, 'directions': ['down_left'], 'tag': 'VNCCS 포즈 출력'}
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'id': 'export'}) as current_gui_mock:
            self.assertEqual(start_vnccs_export('source', 1, 300, 100, ['down_left'])[0], 'export')
        self.assertEqual(current_gui_mock.call_args.args, ('export-vnccs', current_payload_record))
        for current_end_value in (None, 0):
            with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command', return_value={'id': 'export'}) as current_gui_mock:
                start_vnccs_export('source', 1, current_end_value, 1, ['down_left'])
                self.assertNotIn('end_frame', current_gui_mock.call_args.args[1])
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_payload_path = Path(current_temporary_directory) / 'request.json'
            current_payload_path.write_text(json.dumps(current_payload_record))
            with patch('tools.review.common.management_gateway.execute_management_command', return_value={'id': 'export'}) as current_cli_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments('hy-motion', ['export-vnccs', '--payload-file', str(current_payload_path), '--detach'])
        self.assertEqual(current_cli_mock.call_args.args[:3], ('hy-motion', 'export-vnccs', current_payload_record))
        self.assertIn('export-vnccs', MANAGEMENT_SERVICE_COMMANDS['hy-motion'])


class VnccsJobContractTests(unittest.TestCase):
    setUp = test_hy_motion.HyMotionContractTests.setUp
    create_test_generation = test_hy_motion.HyMotionContractTests.create_test_generation

    def test_export_new_record_preserves_source(self):
        current_source_identifier = self.create_test_generation()
        current_source_directory = jobs.resolve_generation_directory(current_source_identifier)
        with self.assertRaisesRegex(ValueError, '완료된'):
            jobs.execute_hymotion_command('export-vnccs', {'source_id': current_source_identifier})
        (current_source_directory / 'status.json').write_text(json.dumps({'status': 'completed'}))
        (current_source_directory / 'result.json').write_text(json.dumps({'kind': 'motion', 'source_frames': 300, 'relative_path': '.'}))
        (current_source_directory / 'motion.npz').write_bytes(b'original')
        with patch.object(jobs, 'launch_gpu_process'):
            current_export_record = jobs.execute_hymotion_command('export-vnccs', {'source_id': current_source_identifier})
        self.assertNotEqual(current_export_record['id'], current_source_identifier)
        current_export_directory = jobs.resolve_generation_directory(current_export_record['id'])
        self.assertEqual(json.loads((current_export_directory / 'export-source.json').read_text())['frames'], 300)
        self.assertEqual((current_source_directory / 'motion.npz').read_bytes(), b'original')
        self.assertIsNone(jobs.read_generation_status(current_export_record['id'])['eta']['remaining'])
        (current_export_directory / 'status.json').write_text(json.dumps({'status': 'completed'}))
        (current_export_directory / 'result.json').write_text(json.dumps({'kind': 'vnccs'}))
        self.assertTrue(next(current_history_record['playable'] for current_history_record in jobs.list_generation_history()['records'] if current_history_record['id'] == current_export_record['id']))

    def test_export_download_and_player_contract(self):
        from tools.review.domains.hy_motion.service import handle_hymotion_request
        from tools.review.ui.gradio.hy_motion_app import render_motion_result
        current_source_identifier = self.create_test_generation()
        current_source_directory = jobs.resolve_generation_directory(current_source_identifier)
        current_result_record = {'kind': 'vnccs', 'relative_path': '.', 'frames': 2, 'directions': ['down_left'], 'source_indices': [1, 151], 'downloads': ['vnccs-package.zip', 'vnccs-manifest.json', 'retarget-quality.json']}
        (current_source_directory / 'result.json').write_text(json.dumps(current_result_record))
        (current_source_directory / 'vnccs-package.zip').write_bytes(b'package')
        current_response_codes = []
        current_response_headers = []
        current_handler_value = SimpleNamespace(path='/hy-motion-generator/jobs/' + current_source_identifier + '/result/vnccs-package.zip', command='GET', server=SimpleNamespace(server_port=8771), headers={'Host': '127.0.0.1:8771'}, rfile=io.BytesIO(), wfile=io.BytesIO(), send_response=current_response_codes.append, send_header=lambda *current_header_values: current_response_headers.append(current_header_values), end_headers=lambda: None)
        self.assertTrue(handle_hymotion_request(current_handler_value))
        self.assertEqual(current_response_codes, [200])
        self.assertEqual(current_handler_value.wfile.getvalue(), b'package')
        self.assertIn(('Content-Type', 'application/zip'), current_response_headers)
        current_player_record = json.loads(render_motion_result(current_source_identifier, {'status': 'completed', 'result': current_result_record}, ''))
        self.assertEqual(current_player_record['sourceFrames']['down_left'], [1, 151])
        self.assertEqual(len(current_player_record['downloads']), 3)
        self.assertTrue(current_player_record['downloads'][0]['url'].endswith('/vnccs-package.zip'))
        self.assertEqual(len(current_player_record['frames']['down_left'][0]), 1)
        current_result_record['projections'] = ['orthographic', 'perspective']
        current_player_record = json.loads(render_motion_result(current_source_identifier, {'status': 'completed', 'result': current_result_record}, ''))
        self.assertEqual(len(current_player_record['panels']), 2)
        self.assertEqual(len(current_player_record['frames']['down_left']), 2)
        self.assertTrue(current_player_record['frames']['down_left'][0][1].endswith('/perspective/down_left/frame-0001.png'))
        current_perspective_directory = current_source_directory / 'perspective/down_left'
        current_perspective_directory.mkdir(parents=True)
        (current_perspective_directory / 'frame-0001.png').write_bytes(b'perspective')
        current_handler_value.path = '/hy-motion-generator/jobs/' + current_source_identifier + '/result/perspective/down_left/frame-0001.png'
        current_handler_value.wfile = io.BytesIO()
        current_response_codes.clear()
        self.assertTrue(handle_hymotion_request(current_handler_value))
        self.assertEqual(current_response_codes, [200])
        self.assertEqual(current_handler_value.wfile.getvalue(), b'perspective')
        current_handler_value.path = '/hy-motion-generator/jobs/' + current_source_identifier + '/result/vnccs-package.zip'
        (current_source_directory / 'vnccs-package.zip').unlink()
        (current_source_directory / 'vnccs-package.zip').symlink_to('/etc/hosts')
        current_response_codes.clear()
        handle_hymotion_request(current_handler_value)
        self.assertEqual(current_response_codes, [400])
