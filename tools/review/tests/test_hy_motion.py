"""HY-Motion GUI·CLI·작업 저장소 및 원본 미리보기 계약."""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo
from unittest.mock import patch

import numpy as np
from PIL import Image
from generators.hy_motion.contracts import load_generation_defaults, validate_generation_request, build_prompt_provenance, UniqueConfigLoader
from generators.hy_motion.preview import render_motion_previews, validate_motion_output
from generators.hy_motion.gif_export import export_motion_gifs
from tools.review.common.management_gateway import execute_gateway_arguments, ManagementCommandGateway
from tools.review.domains.hy_motion import jobs
from tools.review.domains.hy_motion.service import handle_hymotion_request


class HyMotionContractTests(unittest.TestCase):
    def setUp(self):
        self.current_temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temporary_root.cleanup)
        self.current_storage_root = Path(self.current_temporary_root.name)
        for current_attribute_name, current_directory_name in [('GENERATION_STORAGE_ROOT', 'jobs'), ('GENERATION_HISTORY_ROOT', 'history')]:
            current_patch_value = patch.object(jobs, current_attribute_name, self.current_storage_root / current_directory_name)
            current_patch_value.start()
            self.addCleanup(current_patch_value.stop)
        self.current_request_record = {'prompt': 'A person walks forward.', 'duration_seconds': 3, 'seed': 10107, 'directions': ['down_left'], 'tag': '검증'}

    def create_test_generation(self):
        with patch.object(jobs, 'launch_gpu_process'):
            return jobs.start_generation_job(self.current_request_record)['id']

    def test_reject_invalid_request_fields(self):
        for current_field_name, current_invalid_value in [('seed', True), ('seed', -1), ('duration_seconds', float('nan')), ('duration_seconds', 12.01), ('directions', ['down_left', 'down_left']), ('directions', 'down_left'), ('prompt', ' '), ('prompt', 'word ' * 30), ('model', 'arbitrary')]:
            with self.subTest(field=current_field_name), self.assertRaises(ValueError):
                validate_generation_request({**self.current_request_record, current_field_name: current_invalid_value})

    def test_selected_history_delete_preserves_files(self):
        current_job_identifier = self.create_test_generation()
        current_job_directory = jobs.resolve_generation_directory(current_job_identifier)
        with self.assertRaises(ValueError):
            jobs.execute_hymotion_command('history-delete', {'id': current_job_identifier})
        (current_job_directory / 'status.json').write_text(json.dumps({'status': 'failed'}))
        current_delete_result = jobs.execute_hymotion_command('history-delete', {'id': current_job_identifier})
        self.assertTrue(current_delete_result['files_preserved'])
        self.assertTrue((current_job_directory / 'request.json').exists())
        self.assertFalse((jobs.GENERATION_HISTORY_ROOT / (current_job_identifier + '.json')).exists())

    def test_prompt_and_config_validation(self):
        self.assertEqual(validate_generation_request({**self.current_request_record, 'duration_seconds': 12})['duration_seconds'], 12)
        import yaml
        with self.assertRaisesRegex(ValueError, '중복'):
            yaml.load('seed: 1\nseed: 2', Loader=UniqueConfigLoader)
        self.assertEqual(load_generation_defaults()['model_variant'], 'HY-Motion-1.0-Lite')
        self.assertEqual(load_generation_defaults()['directions'], ['down_left'])
        self.assertEqual(build_prompt_provenance('one  two\nthree')['word_count'], 3)

    def test_motion_presets_validate_and_only_restore_inputs(self):
        from generators.hy_motion.contracts import load_motion_presets, MOTION_PRESETS_PATH
        from tools.review.ui.gradio.hy_motion_app import apply_motion_preset
        current_preset_records = load_motion_presets()
        self.assertEqual(set(current_preset_records), {'standing', 'walking'})
        with patch('tools.review.ui.gradio.hy_motion_app.execute_motion_command') as current_command_mock:
            self.assertEqual(apply_motion_preset('standing'), (current_preset_records['standing']['prompt'], 4))
            current_command_mock.assert_not_called()
        with self.assertRaises(ValueError):
            apply_motion_preset('unknown')
        current_invalid_path = self.current_storage_root / 'invalid-presets.yaml'
        current_invalid_path.write_text(MOTION_PRESETS_PATH.read_text() + '\nunknown_field: true\n')
        with patch('generators.hy_motion.contracts.MOTION_PRESETS_PATH', current_invalid_path), self.assertRaises(ValueError):
            load_motion_presets()

    def test_shared_record_and_history_reset_preserve_files(self):
        current_job_identifier = self.create_test_generation()
        current_job_directory = jobs.resolve_generation_directory(current_job_identifier)
        self.assertEqual(json.loads((current_job_directory / 'request.json').read_text()), self.current_request_record)
        self.assertEqual(jobs.list_generation_history()['records'][0]['id'], current_job_identifier)
        with self.assertRaisesRegex(ValueError, '실행'):
            jobs.execute_hymotion_command('history-reset', {})
        (current_job_directory / 'status.json').write_text(json.dumps({'status': 'completed'}))
        jobs.execute_hymotion_command('history-reset', {})
        self.assertEqual(jobs.list_generation_history()['records'], [])
        self.assertTrue((current_job_directory / 'request.json').exists())
        self.assertEqual(jobs.read_generation_status(current_job_identifier)['request'], self.current_request_record)

    def test_cancel_and_resume_use_shared_gpu_queue(self):
        current_job_identifier = self.create_test_generation()
        current_job_directory = jobs.resolve_generation_directory(current_job_identifier)
        with patch.object(jobs, 'cancel_gpu_generation', return_value={'cancel_requested': True}) as current_cancel_mock:
            jobs.execute_hymotion_command('cancel', {'id': current_job_identifier})
            current_cancel_mock.assert_called_once_with(current_job_directory)
        with patch.object(jobs, 'resume_gpu_generation', return_value={'id': current_job_directory.name, 'status': 'queued'}) as current_resume_mock:
            self.assertEqual(jobs.execute_hymotion_command('resume', {'id': current_job_identifier})['id'], current_job_identifier)
            current_resume_mock.assert_called_once_with(current_job_directory)
        with self.assertRaises(ValueError):
            jobs.resolve_generation_directory('../../outside')

    def test_gateway_http_generate_and_unknown_field_rejection(self):
        for current_payload_record, current_expected_status in [(self.current_request_record, 200), ({**self.current_request_record, 'model': 'other'}, 400)]:
            current_body_bytes = json.dumps({'service': 'hy-motion', 'command': 'generate', 'payload': current_payload_record}).encode()
            current_response_codes = []
            current_handler_value = SimpleNamespace(path='/management/command', command='POST', server=SimpleNamespace(server_port=8771), headers={'Host': '127.0.0.1:8771', 'Origin': 'http://127.0.0.1:8771', 'Content-Type': 'application/json', 'Content-Length': str(len(current_body_bytes))}, rfile=io.BytesIO(current_body_bytes), wfile=io.BytesIO(), send_response=current_response_codes.append, send_header=lambda *current_header_values: None, end_headers=lambda: None)
            with patch.object(jobs, 'launch_gpu_process'):
                ManagementCommandGateway({'hy-motion': handle_hymotion_request}).handle(current_handler_value)
            self.assertEqual(current_response_codes, [current_expected_status])

    def test_cli_uses_same_payload(self):
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={'id': 'queued-id'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('hy-motion', ['generate', '--prompt', self.current_request_record['prompt'], '--duration-seconds', '3', '--seed', '10107', '--directions', 'down_left', '--tag', '검증', '--detach'])
        self.assertEqual(current_command_mock.call_args.args[:3], ('hy-motion', 'generate', self.current_request_record))

    def test_gateway_read_envelope_has_no_http_body(self):
        for current_payload_record, current_expected_status in [({}, 200), ({'unexpected': True}, 400)]:
            current_body_bytes = json.dumps({'service': 'hy-motion', 'command': 'history', 'payload': current_payload_record}).encode()
            current_response_codes = []
            current_handler_value = SimpleNamespace(path='/management/command', command='POST', server=SimpleNamespace(server_port=8771), headers={'Host': '127.0.0.1:8771', 'Origin': 'http://127.0.0.1:8771', 'Content-Type': 'application/json', 'Content-Length': str(len(current_body_bytes))}, rfile=io.BytesIO(current_body_bytes), wfile=io.BytesIO(), send_response=current_response_codes.append, send_header=lambda *current_header_values: None, end_headers=lambda: None)
            ManagementCommandGateway({'hy-motion': handle_hymotion_request}).handle(current_handler_value)
            self.assertEqual(current_response_codes, [current_expected_status])

    def test_fixed_camera_preserves_motion_displacement(self):
        current_joint_frames = np.zeros((30, 22, 3), dtype=np.float32)
        current_joint_frames[:, :, 0] = np.arange(30)[:, None] * .05
        current_joint_frames[:, :, 1] = np.arange(22)[None, :] * .03
        current_original_frames = current_joint_frames.copy()
        current_preview_record = render_motion_previews(current_joint_frames, self.current_request_record, load_generation_defaults(), self.current_storage_root, lambda *current_progress_values: None)
        np.testing.assert_array_equal(current_joint_frames, current_original_frames)
        self.assertEqual(current_preview_record['frames'], 8)
        current_first_image = np.asarray(Image.open(self.current_storage_root / 'down_left/frame-0001.png'))
        current_final_image = np.asarray(Image.open(self.current_storage_root / 'down_left/frame-0008.png'))
        self.assertFalse(np.array_equal(current_first_image, current_final_image))

    def test_output_schema_rejects_wrong_shape(self):
        with self.assertRaisesRegex(ValueError, '필드'):
            validate_motion_output({'keypoints3d': np.zeros((30, 22, 3))}, 30)

    def test_variable_gif_frame_timing(self):
        from generators.hy_motion.gif_export import calculate_frame_durations
        for current_source_frames in (30, 120):
            current_source_indices = list(range(1, current_source_frames + 1, 8))
            current_durations = calculate_frame_durations({'frames': len(current_source_indices), 'preview_fps': 3.75, 'source_indices': current_source_indices, 'source_frames': current_source_frames, 'source_fps': 30})
            self.assertEqual(sum(current_durations), current_source_frames * 1000 // 30)
            self.assertTrue(all(current_duration > 0 and current_duration % 10 == 0 for current_duration in current_durations))
        self.assertEqual(current_durations[-1], 270)
        for current_bad_rate in (0, -1, float('nan'), float('inf'), True, 31):
            with self.assertRaises(ValueError):
                calculate_frame_durations({'frames': 1, 'preview_fps': current_bad_rate})

    def test_gif_export_preserves_duration_and_direction_layout(self):
        for current_direction_name in ('down_left', 'up_right'):
            current_direction_path = self.current_storage_root / current_direction_name
            current_direction_path.mkdir()
            for current_frame_index in range(1, 9):
                current_image_value = Image.new('RGB', (32, 32), (245, 245, 245))
                current_image_value.putpixel((current_frame_index, 12), (38, 71, 94))
                current_image_value.save(current_direction_path / f'frame-{current_frame_index:04d}.png')
        current_preview_record = {'frames': 8, 'preview_fps': 8, 'directions': ['down_left', 'up_right']}
        current_gif_records = export_motion_gifs(current_preview_record, self.current_storage_root, lambda *current_progress_values: None)
        self.assertEqual([current_gif_record['path'] for current_gif_record in current_gif_records], ['overview.gif'])
        self.assertFalse((self.current_storage_root / 'down_left.gif').exists())
        self.assertFalse((self.current_storage_root / 'up_right.gif').exists())
        for current_gif_record in current_gif_records:
            with Image.open(self.current_storage_root / current_gif_record['path']) as current_gif_image:
                self.assertEqual(current_gif_image.n_frames, 8)
                self.assertEqual(current_gif_image.info['loop'], 0)
                current_total_duration = 0
                for current_frame_index in range(current_gif_image.n_frames):
                    current_gif_image.seek(current_frame_index)
                    current_total_duration += current_gif_image.info['duration']
                self.assertEqual(current_total_duration, 1000)
        with Image.open(self.current_storage_root / 'overview.gif') as current_gif_image:
            self.assertEqual(current_gif_image.size, (64, 56))
        with self.assertRaises(FileExistsError):
            export_motion_gifs(current_preview_record, self.current_storage_root, lambda *current_progress_values: None)

    def test_gif_export_rejects_missing_frames_and_bad_rate(self):
        with self.assertRaises(ValueError):
            export_motion_gifs({'frames': 8, 'preview_fps': 0, 'directions': ['down_left']}, self.current_storage_root, lambda *current_progress_values: None)
        with self.assertRaises(FileNotFoundError):
            export_motion_gifs({'frames': 8, 'preview_fps': 8, 'directions': ['down_left']}, self.current_storage_root, lambda *current_progress_values: None)

    def test_adaptive_gif_palette_preserves_mesh_shading(self):
        current_direction_path = self.current_storage_root / 'down_left'
        current_direction_path.mkdir()
        current_gradient_values = np.broadcast_to(np.arange(32, dtype=np.uint8)[None, :, None] * 8, (32, 32, 3)).copy()
        Image.fromarray(current_gradient_values).save(current_direction_path / 'frame-0001.png')
        export_motion_gifs({'frames': 1, 'preview_fps': 8, 'directions': ['down_left']}, self.current_storage_root, lambda *current_progress_values: None, current_palette_mode='adaptive')
        self.assertFalse((self.current_storage_root / 'down_left.gif').exists())
        with Image.open(self.current_storage_root / 'overview.gif') as current_gif_image:
            self.assertGreater(len(current_gif_image.convert('RGB').getcolors()), 20)

    def test_eta_uses_matching_completed_samples(self):
        current_finished_identifier = self.create_test_generation()
        current_finished_directory = jobs.resolve_generation_directory(current_finished_identifier)
        (current_finished_directory / 'status.json').write_text(json.dumps({'status': 'completed'}))
        (current_finished_directory / 'result.json').write_text(json.dumps({'kind': 'motion', 'elapsed_seconds': 30}))
        current_running_identifier = self.create_test_generation()
        current_running_directory = jobs.resolve_generation_directory(current_running_identifier)
        (current_running_directory / 'status.json').write_text(json.dumps({'status': 'running', 'started_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}))
        current_estimate_record = jobs.read_generation_status(current_running_identifier)['eta']
        self.assertGreater(current_estimate_record['remaining'], 20)
        self.assertIn('1개 완료', current_estimate_record['basis'])

    def test_eta_prefers_current_render_observations(self):
        import os
        import time
        current_job_identifier = self.create_test_generation()
        current_job_directory = jobs.resolve_generation_directory(current_job_identifier)
        current_render_directory = current_job_directory / 'attempts/test/anny'
        (current_render_directory / 'down_left').mkdir(parents=True)
        (current_render_directory / 'stage-request.json').write_text(json.dumps({'request': {'start_frame': 1, 'end_frame': 30, 'frame_step': 1, 'directions': ['down_left']}, 'config': {'projections': ['orthographic', 'perspective']}}))
        current_clock_seconds = time.time()
        for current_frame_number in (1, 2, 3):
            current_frame_path = current_render_directory / 'down_left' / f'frame-{current_frame_number:04d}.png'
            current_frame_path.touch()
            current_frame_seconds = current_clock_seconds - (3 - current_frame_number) * 2
            os.utime(current_frame_path, (current_frame_seconds, current_frame_seconds))
        current_estimate_record = jobs.estimate_generation_completion(current_job_directory, self.current_request_record, {'status': 'running', 'attempt_path': 'attempts/test', 'progress': {'stage': 'render'}})
        self.assertEqual(current_estimate_record['sample_count'], 2)
        self.assertEqual(current_estimate_record['total_units'], 60)
        self.assertEqual(current_estimate_record['measured_progress'], 5)
        self.assertGreater(current_estimate_record['remaining'], 110)
        self.assertIn('패키징 시간 제외', current_estimate_record['scope'])

    def test_result_files_allow_only_registered_paths(self):
        current_job_identifier = self.create_test_generation()
        current_job_directory = jobs.resolve_generation_directory(current_job_identifier)
        current_attempt_directory = current_job_directory / 'attempts/test'
        current_attempt_directory.mkdir(parents=True)
        (current_attempt_directory / 'motion.npz').write_bytes(b'validated-output')
        (current_job_directory / 'result.json').write_text(json.dumps({'relative_path': 'attempts/test'}))
        current_response_codes = []
        current_handler_value = SimpleNamespace(path=f'/hy-motion-generator/jobs/{current_job_identifier}/result/motion.npz', command='GET', server=SimpleNamespace(server_port=8771), headers={'Host': '127.0.0.1:8771'}, rfile=io.BytesIO(), wfile=io.BytesIO(), send_response=current_response_codes.append, send_header=lambda *current_header_values: None, end_headers=lambda: None)
        handle_hymotion_request(current_handler_value)
        self.assertEqual(current_response_codes, [200])
        self.assertEqual(current_handler_value.wfile.getvalue(), b'validated-output')
        (current_job_directory / 'result.json').write_text(json.dumps({'relative_path': '../../outside'}))
        current_response_codes.clear()
        handle_hymotion_request(current_handler_value)
        self.assertEqual(current_response_codes, [400])

    def test_ui_restores_inputs_and_builds_original_result_urls(self):
        from tools.review.ui.gradio.hy_motion_app import restore_motion_inputs, render_motion_result, build_hymotion_interface
        self.assertEqual(restore_motion_inputs({'request': self.current_request_record})[0], self.current_request_record['prompt'])
        current_result_record = {'status': 'completed', 'result': {'kind': 'motion', 'frames': 2, 'directions': ['down_left'], 'source_indices': [1, 5]}}
        current_player_record = json.loads(render_motion_result('test-id', current_result_record, 'http://127.0.0.1:8770'))
        self.assertEqual(current_player_record['sourceFrames']['down_left'], [1, 5])
        self.assertTrue(current_player_record['downloads'][0]['url'].endswith('/result/motion.npz'))
        current_result_record['result']['gifs'] = [{'path': 'down_left.gif', 'label': 'down_left GIF'}, {'path': 'overview.gif', 'label': '전체 방향 비교 GIF'}]
        current_player_record = json.loads(render_motion_result('test-id', current_result_record, 'http://127.0.0.1:8770'))
        self.assertFalse(any(current_download_record['url'].endswith('/down_left.gif') for current_download_record in current_player_record['downloads']))
        self.assertEqual(current_player_record['downloads'][-1]['url'], 'http://127.0.0.1:8770/hy-motion-generator/jobs/test-id/result/overview.gif')
        current_interface_blocks = build_hymotion_interface('http://127.0.0.1:8770')
        self.assertGreater(len(current_interface_blocks.blocks), 30)
        self.assertFalse(any('기존 모션 ANNY 재출력' in str(getattr(current_component_value, 'label', '')) for current_component_value in current_interface_blocks.blocks.values()))
