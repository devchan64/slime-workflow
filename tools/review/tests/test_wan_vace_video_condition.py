"""VACE 영상 전체 조건의 GUI·서비스·모델 입력 계약을 확인한다."""
import base64
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from generators.wan_vace.contracts import validate_vace_request
from generators.wan_vace.video_edit import build_video_condition_inputs
from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
from tools.review.ui.gradio.wan_vace_app import build_vace_payload, check_vace_readiness, select_vace_mode_inputs


class VaceWholeVideoConditionTests(unittest.TestCase):
    def test_gui_gateway_service_and_black_mask_contract(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_root = Path(current_temp_root)
            current_input_path = current_job_root / 'source.mp4'
            current_writer_object = cv2.VideoWriter(str(current_input_path), cv2.VideoWriter_fourcc(*'mp4v'), 16, (832, 480))
            self.assertTrue(current_writer_object.isOpened())
            for current_frame_number in range(5):
                current_writer_object.write(np.full((480,832,3), 40+current_frame_number*20, np.uint8))
            current_writer_object.release()
            current_reference_image = Image.new('RGB', (832,480), 'white')
            current_payload_record = build_vace_payload('video_condition',current_reference_image,'A character sits.','',5,42,2,12,5,1,str(current_input_path),None,None)
            self.assertEqual(validate_vace_request(current_payload_record)['mode'],'video_condition')
            self.assertTrue(check_vace_readiness(True,'video_condition','ref.png','walk',str(current_input_path)))
            self.assertFalse(check_vace_readiness(True,'video_condition','ref.png','walk',str(current_input_path),'mask.mp4'))
            current_selected_values=select_vace_mode_inputs(['video_condition',None,'x','',5,42,2,12,5,1,'source.mp4','stale-mask.mp4',None])
            self.assertIsNone(current_selected_values[11])
            current_saved_record = VaceVideoGenerationManager().save_generation_attachments(current_job_root, current_payload_record)
            current_condition_values = build_video_condition_inputs(current_job_root,current_saved_record)
            self.assertEqual(tuple(current_condition_values['video'].shape),(1,3,5,480,832))
            self.assertEqual(int(current_condition_values['mask_video'].count_nonzero()),0)
            self.assertGreater(float(current_condition_values['video'].mean()),0)
            current_saved_record['edit_video_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'해시 불일치'):
                build_video_condition_inputs(current_job_root,current_saved_record)
            current_invalid_record={**current_payload_record,'mode':'video_edit','edit_mask':base64.b64encode(current_input_path.read_bytes()).decode()}
            with self.assertRaisesRegex(ValueError,'보존 영역과 편집 영역'):
                validate_vace_request(current_invalid_record)


if __name__ == '__main__':
    unittest.main()
