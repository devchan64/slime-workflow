"""RGB 직접 입력의 보존·복원 및 혼합 입력 거절 검증."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from PIL import Image
from generators.wan_fun.contracts import validate_fun_request
from generators.wan_fun.video_input import decode_processed_pose_video
from tools.review.ui.gradio.wan_fun_app import build_fun_payload, restore_fun_inputs
from tools.review.domains.wan_fun.generation import FunControlGenerationManager

class FunRgbInputTests(unittest.TestCase):
    def test_rgb_round_trip(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_root = Path(current_temp_directory)/'job'
            current_job_root.mkdir()
            current_reference_path = current_job_root/'reference-1.png'
            Image.new('RGB',(832,480),'white').save(current_reference_path)
            current_video_path = current_job_root/'source.mp4'
            current_video_writer = cv2.VideoWriter(str(current_video_path),cv2.VideoWriter_fourcc(*'mp4v'),16,(832,480))
            for current_frame_index in range(5):
                current_video_writer.write(np.full((480,832,3),(30,80,180),dtype=np.uint8))
            current_video_writer.release()
            current_payload_record = build_fun_payload(str(current_reference_path),str(current_video_path),None,'pose','Preserve the motion.','',5,42,20,5,6,.5,'rgb-video')
            self.assertEqual(current_payload_record['control_type'],'rgb')
            self.assertNotIn('pose_video',current_payload_record)
            for current_invalid_fields in ({'input_mode':'controlled'},{'control_type':'pose'},{'pose_video':current_payload_record['rgb_video']}):
                with self.assertRaises(ValueError):
                    validate_fun_request({**current_payload_record,**current_invalid_fields})
            current_saved_record = FunControlGenerationManager.save_generation_attachments(None,current_job_root,current_payload_record)
            self.assertEqual((current_job_root/'rgb-input.mp4').read_bytes(),current_video_path.read_bytes())
            self.assertEqual(current_saved_record['control_preprocessor'],'none')
            current_attempt_root = current_job_root/'attempt'
            current_attempt_root.mkdir()
            current_frame_paths = decode_processed_pose_video(current_job_root,current_attempt_root,current_saved_record)
            self.assertEqual(len(current_frame_paths),5)
            self.assertGreater(Image.open(current_frame_paths[0]).getpixel((0,0))[0],150)
            current_saved_record['references']=['reference-1.png']
            with patch('tools.review.ui.gradio.wan_fun_app.FUN_JOB_STORAGE',Path(current_temp_directory)):
                current_restored_values = restore_fun_inputs({'id':'job','request':current_saved_record})
            self.assertEqual(current_restored_values[12],'rgb-video')
            self.assertTrue(current_restored_values[1].endswith('rgb-input.mp4'))
