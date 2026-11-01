"""부분 편집 입력 보존과 마스크 조건을 검증한다."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np
from unittest.mock import patch
from generators.wan_vace.video_edit import save_edit_inputs, build_edit_conditions


@unittest.skipUnless(importlib.util.find_spec('torch'), '추론 환경의 torch 필요')
class VaceVideoEditTest(unittest.TestCase):
    def test_official_pose_control_is_not_erased_by_edit_mask(self):
        import base64
        import torch
        from generators.wan_vace.official_runtime import build_pose_conditions
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_job_root = Path(current_temp_name)
            current_saved_record = save_edit_inputs(current_job_root, {'frames':5,'pose_video':base64.b64encode(b'pose').decode()}, ('pose_video',))
            with patch('generators.wan_vace.video_edit.decode_edit_video',return_value=np.full((5,480,832,3),128,np.uint8)):
                current_condition_record = build_pose_conditions(current_job_root,current_saved_record)
            self.assertEqual(tuple(current_condition_record['control_video'].shape),(1,3,5,480,832))
            self.assertTrue(torch.all(current_condition_record['mask_video']==1))
            self.assertTrue(torch.all(current_condition_record['video']==0))
            self.assertAlmostEqual(float(current_condition_record['control_video'][0,0,0,0,0]),128/255,places=6)
            (current_job_root/'pose-video.mp4').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'해시'):
                build_pose_conditions(current_job_root,current_saved_record)

    def test_edit_mask_removes_source_identity(self):
        import base64
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_job_root = Path(current_temp_name)
            current_request_record = save_edit_inputs(current_job_root, {'frames': 5, 'edit_video': base64.b64encode(b'video').decode(), 'edit_mask': base64.b64encode(b'mask').decode()})
            current_source_frames = np.full((5,480,832,3), 200, np.uint8)
            current_mask_frames = np.zeros_like(current_source_frames)
            current_mask_frames[:,65:145,355:465] = 255
            with patch('generators.wan_vace.video_edit.decode_edit_video', side_effect=[current_source_frames,current_mask_frames]):
                current_condition_record = build_edit_conditions(current_job_root,current_request_record,None)
            self.assertAlmostEqual(float(current_condition_record['control_video'][0,100,400,0]), .5)
            self.assertAlmostEqual(float(current_condition_record['control_video'][0,200,400,0]), 200/255, places=6)
            self.assertEqual(float(current_condition_record['control_masks'][0,100,400]), 1)
            (current_job_root/'edit-video.mp4').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'해시'):
                build_edit_conditions(current_job_root,current_request_record,None)


class VacePoseInputTest(unittest.TestCase):
    def test_pose_gui_contract_and_attachment(self):
        import base64
        import cv2
        from PIL import Image
        from tools.review.ui.gradio.wan_vace_app import build_vace_payload, check_vace_readiness
        from generators.wan_vace.contracts import validate_vace_request
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_job_root = Path(current_temp_name)
            current_video_path = current_job_root/'input.mp4'
            current_video_writer = cv2.VideoWriter(str(current_video_path), cv2.VideoWriter_fourcc(*'mp4v'), 16, (832,480))
            for current_frame_index in range(5):
                current_video_writer.write(np.zeros((480,832,3),np.uint8))
            current_video_writer.release()
            current_request_record = build_vace_payload('pose',Image.new('RGB',(832,480)),'A character walks.','',5,42,20,12,5,1,None,None,str(current_video_path))
            self.assertEqual(current_request_record['mode'],'pose')
            self.assertNotIn('edit_mask',current_request_record)
            validate_vace_request(current_request_record)
            with self.assertRaises(ValueError):
                validate_vace_request({**current_request_record,'frames':9})
            with self.assertRaises(ValueError):
                validate_vace_request({**current_request_record,'edit_mask':'unused'})
            current_saved_record = save_edit_inputs(current_job_root,current_request_record,('pose_video',))
            self.assertNotIn('pose_video',current_saved_record)
            self.assertEqual((current_job_root/'pose-video.mp4').read_bytes(),current_video_path.read_bytes())
            self.assertTrue(check_vace_readiness(True,'pose','ref','walk',None,None,'pose.mp4'))
            self.assertFalse(check_vace_readiness(True,'pose','ref','walk',None,None,None))
