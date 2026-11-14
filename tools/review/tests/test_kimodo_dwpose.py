"""관절 길이 보정의 투영·시간 일관성과 처리된 영상 입력 계약."""
import unittest
import tempfile
from pathlib import Path
from collections import namedtuple
import numpy as np
from generators.kimodo.dwpose_export import adjust_detected_pose_frames
from generators.wan_fun.video_input import validate_processed_pose_video

class KimodoDwposeTests(unittest.TestCase):
    def test_migraphx_pose_outputs_use_correct_axes(self):
        from types import SimpleNamespace
        from generators.kimodo.dwpose_runtime import MigraphxPoseInferenceSession
        current_x_values = np.zeros((1, 133, 576))
        current_y_values = np.zeros((1, 133, 768))
        current_session = SimpleNamespace(run=lambda *args: [current_y_values, current_x_values])
        current_input_values = {'input': np.zeros((1, 3, 384, 288))}
        current_outputs = MigraphxPoseInferenceSession(current_session).run(None, current_input_values)
        self.assertIs(current_outputs[0], current_x_values)
        self.assertIs(current_outputs[1], current_y_values)
        current_session.run = lambda *args: [current_x_values, current_x_values]
        with self.assertRaisesRegex(ValueError, '출력 크기'):
            MigraphxPoseInferenceSession(current_session).run(None, current_input_values)

    def test_migraphx_pose_splits_multiple_people_into_fixed_batches(self):
        from types import SimpleNamespace
        from generators.kimodo.dwpose_runtime import MigraphxPoseInferenceSession
        current_batch_sizes = []
        def run_fixture_batch(current_output_names, current_input_values):
            current_batch = current_input_values['input']
            current_batch_sizes.append(current_batch.shape[0])
            current_marker = current_batch[:, 0, 0, 0]
            return [np.broadcast_to(current_marker[:, None, None], (1, 133, 768)),
                    np.broadcast_to(current_marker[:, None, None], (1, 133, 576))]
        current_session = SimpleNamespace(run=run_fixture_batch)
        current_input_batch = np.arange(6).reshape(6, 1, 1, 1)
        current_outputs = MigraphxPoseInferenceSession(current_session).run(None, {'input': current_input_batch})
        self.assertEqual(current_batch_sizes, [1] * 6)
        self.assertEqual(current_outputs[0].shape, (6, 133, 576))
        np.testing.assert_array_equal(current_outputs[0][:, 0, 0], np.arange(6))

    def test_scaled_pose_keeps_original_pelvis_vertical_motion(self):
        current_point_type = namedtuple('Point','x y score id',defaults=[1.0,0])
        current_body_type = namedtuple('Body','keypoints')
        current_pose_type = namedtuple('Pose','body left_hand right_hand face')
        current_frame_records = []
        for current_vertical_offset in (0,60,-30):
            current_body_points = [current_point_type(200,100+current_vertical_offset) for current_joint_index in range(18)]
            current_body_points[8] = current_point_type(180,200+current_vertical_offset)
            current_body_points[11] = current_point_type(220,220+current_vertical_offset)
            current_frame_records.append([current_pose_type(current_body_type(current_body_points),None,None,None)])
        current_measurement_record = {}
        current_output_frames = adjust_detected_pose_frames(current_frame_records,(480,832),{},85,None,current_measurement_record)
        for current_frame_index,current_vertical_offset in enumerate((0,60,-30)):
            current_output_points = current_output_frames[current_frame_index][0].body.keypoints
            self.assertAlmostEqual((current_output_points[8].y+current_output_points[11].y)/2,240+.85*(210+current_vertical_offset-240))
            self.assertAlmostEqual((current_output_points[8].x+current_output_points[11].x)/2,416+.85*(200-416))
            self.assertAlmostEqual(current_output_points[0].y,240+.85*(100+current_vertical_offset-240))
        self.assertLess(current_measurement_record['pelvis_y_anchor']['maximum_error'],1e-8)
        current_frame_records[0][0].body.keypoints[8] = None
        with self.assertRaisesRegex(ValueError,'골반 Y'):
            adjust_detected_pose_frames(current_frame_records,(480,832),{},85)

    def test_kimodo_dwpose_exports_every_source_frame_at_30fps(self):
        import json
        from unittest.mock import patch
        from generators.kimodo.dwpose_export import export_kimodo_dwpose
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_job_root=Path(current_temporary_root)/'job'
            current_attempt_root=current_job_root/'attempt'
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'request.json').write_text(json.dumps({'frames':40,'directions':['front']}))
            (current_attempt_root/'soma-render-front.mp4').write_bytes(b'fixture')
            current_calls=[]
            def prepare_fixture_pose(current_job_directory,current_output_directory,current_pose_request,current_pose_transform=None,current_output_fps=16):
                current_calls.append((current_pose_request['frames'],current_output_fps))
                (current_output_directory/'pose.mp4').write_bytes(b'fixture')
            with patch('generators.kimodo.dwpose_export.prepare_fun_pose_frames',side_effect=prepare_fixture_pose):
                export_kimodo_dwpose(current_job_root,current_attempt_root)
            current_export_record=json.loads((current_attempt_root/'dwpose-export.json').read_text())
            self.assertEqual(current_calls,[(40,30)])
            self.assertEqual(current_export_record['fps'],30)
            self.assertEqual((current_attempt_root/'dwpose-front.mp4').read_bytes(),b'fixture')

    def test_projection_calibration_corrects_detector_bias_without_flattening_motion(self):
        import json
        from generators.kimodo.dwpose_export import calculate_projected_segment_gains
        from generators.kimodo.soma_pose import SOMA_BODY_JOINT_NAMES
        current_point_type = namedtuple('Point','x y score id',defaults=[1.0,0])
        current_body_type = namedtuple('Body','keypoints')
        current_pose_type = namedtuple('Pose','body left_hand right_hand face')
        current_joints = [current_name for current_name in SOMA_BODY_JOINT_NAMES if current_name]
        current_positions = np.zeros((3,len(current_joints),3))
        current_coordinates = {2:(-30,100),5:(30,100),3:(-50,150),6:(50,150),4:(-70,200),7:(70,200),8:(-20,200),11:(20,200),9:(-20,270),12:(20,270),10:(-20,340),13:(20,340)}
        for current_index,current_position in current_coordinates.items():
            current_positions[:,current_joints.index(SOMA_BODY_JOINT_NAMES[current_index]),:2] = current_position
        current_points = [current_point_type(200,100) for current_index in range(18)]
        for current_index,(current_x,current_y) in current_coordinates.items():
            current_points[current_index] = current_point_type(200+current_x*.8, current_y)
        current_frames = [[current_pose_type(current_body_type(current_points),None,None,None)]]
        current_ratios = {'ratios':{'shoulder_width':.6,'hip_width':.4,'upper_arm':np.hypot(20,50)/100,'forearm':np.hypot(20,50)/100,'thigh':.7,'shin':.7}}
        with tempfile.TemporaryDirectory() as current_directory:
            current_root = Path(current_directory)
            (current_root/'skeleton.json').write_text(json.dumps({'joint_names':current_joints}))
            np.savez(current_root/'motion.npz',posed_joints=current_positions)
            current_gains = calculate_projected_segment_gains(current_root,current_ratios,current_frames,'front')
        self.assertAlmostEqual(current_gains['shoulder_width'],1.25)
        self.assertAlmostEqual(current_gains['hip_width'],1.25)
        self.assertAlmostEqual(current_gains['thigh'],1.0)

    def test_body_axis_moves_shoulder_line_and_preserves_face_and_hip(self):
        current_point_type = namedtuple('Point','x y score id',defaults=[1.0,0])
        current_body_type = namedtuple('Body','keypoints')
        current_pose_type = namedtuple('Pose','body left_hand right_hand face')
        current_points=[current_point_type(200,100) for current_index in range(18)]
        for current_index,current_position in {0:(200,70),1:(200,100),2:(170,100),5:(230,100),8:(180,200),11:(220,200)}.items():
            current_points[current_index]=current_point_type(*current_position)
        current_frames=[[current_pose_type(current_body_type(current_points),None,None,[current_points[0]])]]
        current_gains=dict(shoulder_width=1,hip_width=1,upper_arm=1,forearm=1,thigh=1,shin=1)
        current_measurements={}
        current_result=adjust_detected_pose_frames(current_frames,(480,832),current_gains,100,{'body_axis':{'nose_shoulder_to_torso':.6}},current_measurements)[0][0]
        self.assertAlmostEqual(current_measurements['torso_gain'],.8125)
        self.assertAlmostEqual(current_result.body.keypoints[1].y,118.75)
        self.assertEqual(current_result.body.keypoints[0].y,70)
        self.assertEqual(current_result.face[0].y,70)
        self.assertAlmostEqual((current_result.body.keypoints[8].y+current_result.body.keypoints[11].y)/2,200)

    def test_body_axis_uses_visible_frames_when_nose_is_occluded(self):
        current_point_type=namedtuple('Point','x y score id',defaults=[1.0,0])
        current_body_type=namedtuple('Body','keypoints')
        current_pose_type=namedtuple('Pose','body left_hand right_hand face')
        current_points=[current_point_type(200,100) for current_index in range(18)]
        for current_index,current_position in {0:(200,70),1:(200,100),2:(170,100),5:(230,100),8:(180,200),11:(220,200)}.items():
            current_points[current_index]=current_point_type(*current_position)
        current_occluded_points=list(current_points)
        current_occluded_points[0]=None
        current_frames=[[current_pose_type(current_body_type(current_points),None,None,None)],[current_pose_type(current_body_type(current_occluded_points),None,None,None)]]
        current_gains=dict(shoulder_width=1,hip_width=1,upper_arm=1,forearm=1,thigh=1,shin=1)
        current_measurements={}
        current_result=adjust_detected_pose_frames(current_frames,(480,832),current_gains,100,{'body_axis':{'nose_shoulder_to_torso':.6}},current_measurements)
        self.assertEqual(current_measurements['valid_frames'],1)
        self.assertEqual(current_measurements['total_frames'],2)
        self.assertIsNone(current_result[1][0].body.keypoints[0])
        self.assertAlmostEqual(current_result[1][0].body.keypoints[1].y,118.75)

    def test_constant_gain_preserves_projected_shortening_and_wrist_attachment(self):
        current_point_type = namedtuple('Point','x y score id',defaults=[1.0,0])
        current_body_type = namedtuple('Body','keypoints')
        current_pose_type = namedtuple('Pose','body left_hand right_hand face')
        current_frame_records = []
        for current_arm_length in (40,20):
            current_points = [current_point_type(100,100) for current_joint_index in range(18)]
            current_points[2]=current_point_type(120,100)
            current_points[3]=current_point_type(120+current_arm_length,100)
            current_points[4]=current_point_type(140+current_arm_length,100)
            current_frame_records.append([current_pose_type(current_body_type(current_points),None,[current_points[4]],None)])
        current_gains = dict(shoulder_width=1,hip_width=1,upper_arm=2,forearm=1,thigh=1,shin=1)
        current_results = adjust_detected_pose_frames(current_frame_records,(480,832),current_gains,100)
        current_lengths = [current_frame[0].body.keypoints[3].x-current_frame[0].body.keypoints[2].x for current_frame in current_results]
        self.assertEqual(current_lengths,[80,40])
        for current_frame in current_results:
            self.assertEqual(current_frame[0].right_hand[0].x,current_frame[0].body.keypoints[4].x)

    def test_pose_video_rejects_invalid_container(self):
        with self.assertRaises(ValueError):
            validate_processed_pose_video('',21)

    def test_processed_video_attachment_decode_and_restore(self):
        import cv2
        import base64
        from unittest.mock import patch
        from PIL import Image
        from tools.review.domains.wan_fun.generation import FunControlGenerationManager
        from tools.review.ui.gradio.wan_fun_app import build_fun_payload,restore_fun_inputs
        from generators.wan_fun.video_input import decode_processed_pose_video
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_job_root = Path(current_temporary_root)/'test'
            current_job_root.mkdir()
            current_video_path = current_job_root/'source.mp4'
            current_video_writer = cv2.VideoWriter(str(current_video_path),cv2.VideoWriter_fourcc(*'mp4v'),16,(832,480))
            for current_frame_index in range(5):
                current_video_writer.write(np.zeros((480,832,3),dtype=np.uint8))
            current_video_writer.release()
            current_reference_path = current_job_root/'reference-1.png'
            Image.new('RGB',(832,480),'white').save(current_reference_path)
            current_payload_record = build_fun_payload(str(current_reference_path),str(current_video_path),None,'pose','walking','',5,42,20,5,6,.5,'pose-video')
            self.assertIn('pose_video',current_payload_record)
            self.assertNotIn('driving_video',current_payload_record)
            current_saved_record = FunControlGenerationManager.save_generation_attachments(None,current_job_root,current_payload_record)
            current_saved_record['references']=['reference-1.png']
            current_attempt_root = current_job_root/'attempt'
            current_attempt_root.mkdir()
            self.assertEqual(len(decode_processed_pose_video(current_job_root,current_attempt_root,current_saved_record)),5)
            with patch('tools.review.ui.gradio.wan_fun_app.FUN_JOB_STORAGE',Path(current_temporary_root)):
                current_restored_values = restore_fun_inputs({'id':'test','request':current_saved_record})
            self.assertEqual(current_restored_values[12],'pose-video')
            self.assertEqual(current_restored_values[1],str(current_job_root/'pose-input.mp4'))
