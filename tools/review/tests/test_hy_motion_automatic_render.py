"""HY-Motion 자동 리그·OpenPose 출력과 과거 이력 호환 계약."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from generators.hy_motion.automatic_render import generate_automatic_renders
from generators.hy_motion.openpose_export import write_projected_openpose
from generators.hy_motion.vnccs_contract import load_vnccs_config


class AutomaticRenderTests(unittest.TestCase):
    def test_wrist_rotation_guide_image(self):
        import numpy as np
        from generators.hy_motion.preview import render_motion_previews
        from generators.hy_motion.contracts import load_generation_defaults
        current_joint_frames = np.zeros((1, 22, 3))
        current_joint_frames[0, :, 1] = np.linspace(0, 1, 22)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_output_path = Path(current_directory_name)
            current_result_record = render_motion_previews(current_joint_frames, {'directions': ['down_left']}, load_generation_defaults(), current_output_path, lambda *current_log_values: None, np.eye(3)[None], np.tile(np.eye(3), (1, 2, 1, 1)))
            self.assertTrue(current_result_record['wrist_rotation_guide'])
            with Image.open(current_output_path / 'down_left/frame-0001-rotation.png') as current_guide_image:
                self.assertIn((40, 170, 70), {current_color_value for _, current_color_value in current_guide_image.getcolors(1000000)})

    def test_fixed_anny_pipeline_and_same_attempt(self):
        current_config_record = load_vnccs_config()
        self.assertEqual(current_config_record['rig_backend'], 'anny')
        self.assertTrue(current_config_record['skin_profile'].endswith('anny-adjacency-barrier.yaml'))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_path = Path(current_directory_name)
            (current_attempt_path / 'motion.npz').write_bytes(b'motion')
            current_request_record = {'duration_seconds': 4, 'directions': ['down_left'], 'prompt': 'A person walks.', 'seed': 1}
            with patch('generators.hy_motion.automatic_render.export_vnccs_package', return_value={'quality_warnings': []}) as current_export_mock:
                current_result_record = generate_automatic_renders(current_attempt_path, current_attempt_path, current_request_record, current_config_record, lambda *current_stage_values: None)
            self.assertTrue(current_result_record['automatic'])
            self.assertEqual(current_result_record['relative_path'], 'anny')
            self.assertEqual(current_export_mock.call_args.args[2]['end_frame'], 120)
            self.assertEqual(current_export_mock.call_args.args[2]['frame_step'], 1)
            self.assertEqual(current_export_mock.call_args.kwargs['current_source_record']['motion_path'], str(current_attempt_path / 'motion.npz'))

    def test_openpose_has_explicit_projection_provenance(self):
        current_keypoints_flat = [0.] * 54
        current_keypoints_flat[3:6] = [256., 128., 1.]
        current_keypoints_flat[6:9] = [200., 160., 1.]
        current_image_record = {'pose_keypoints_2d': current_keypoints_flat, 'source_frame': 3, 'projection': 'perspective', 'head_bone_keypoints_2d': [[256., 100., 1.], [256., 60., 1.]]}
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_image_path = Path(current_directory_name) / 'pose.png'
            write_projected_openpose(current_image_record, current_image_path, 512)
            with Image.open(current_image_path) as current_result_image:
                self.assertEqual(current_result_image.size, (512, 512))
                self.assertNotEqual(current_result_image.getpixel((256, 128)), (0, 0, 0))
                self.assertEqual(current_result_image.getpixel((256, 60)), (255, 0, 255))
            current_json_record = json.loads(current_image_path.with_suffix('.json').read_text())
            self.assertEqual(current_json_record['people'][0]['pose_keypoints_2d'][:3], [0, 0, 0])
            self.assertEqual(current_json_record['source_frame'], 3)
            for current_invalid_points in ([1.] * 53, [float('nan')] * 54, [999.] * 54):
                with self.assertRaises(ValueError):
                    write_projected_openpose({**current_image_record, 'pose_keypoints_2d': current_invalid_points}, current_image_path, 512)

    def test_automatic_player_uses_source_frames(self):
        from tools.review.ui.gradio.hy_motion_app import render_motion_result
        current_result_record = {'kind': 'motion', 'frames': 2, 'directions': ['down_left'], 'source_indices': [1, 4], 'rendering': {'downloads': ['vnccs-package.zip']}}
        current_player_record = json.loads(render_motion_result('test-id', {'status': 'completed', 'result': current_result_record}, ''))
        self.assertEqual(len(current_player_record['panels']), 5)
        self.assertFalse(any(current_download_record['url'].endswith('/provenance.json') for current_download_record in current_player_record['downloads']))
        self.assertTrue(any(current_download_record['url'].endswith('/motion.npz') for current_download_record in current_player_record['downloads']))
        self.assertTrue(current_player_record['frames']['down_left'][1][0].endswith('/down_left/frame-0002.png'))
        self.assertTrue(current_player_record['frames']['down_left'][1][4].endswith('/anny/perspective/down_left/frame-0004-openpose.png'))
        current_result_record['head_rotation_guide'] = True
        current_player_record = json.loads(render_motion_result('test-id', {'status': 'completed', 'result': current_result_record}, ''))
        self.assertEqual(len(current_player_record['panels']), 6)
        self.assertEqual(current_player_record['columns'], 3)
        self.assertTrue(current_player_record['frames']['down_left'][1][1].endswith('/down_left/frame-0002-rotation.png'))

    def test_makehuman_job_cannot_resume_as_anny(self):
        from generators.hy_motion.vnccs_export import export_vnccs_package
        with self.assertRaisesRegex(ValueError, 'MakeHuman'):
            export_vnccs_package(Path('/missing'), Path('/missing'), {}, {'rig_backend': 'makehuman'}, lambda *current_stage_values: None)
