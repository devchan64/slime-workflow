"""Animate-2 서비스와 구형 폐기 계약을 구분한다."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from generators.wan_animate2.contracts import validate_animate_request
from tools.review.domains.wan_animate2.generation import AnimateTwoGenerationManager
from tools.review.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS


class AnimateTwoContractTests(unittest.TestCase):
    def test_rgb_request_duration_and_dimensions(self):
        import cv2
        import numpy as np
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(832,480),'white').save(current_image_buffer,format='PNG')
        with tempfile.TemporaryDirectory() as current_test_directory:
            current_video_path=Path(current_test_directory)/'motion.mp4'
            current_video_writer=cv2.VideoWriter(str(current_video_path),cv2.VideoWriter_fourcc(*'mp4v'),30,(64,64))
            for current_frame_number in range(30):
                current_video_writer.write(np.full((64,64,3),current_frame_number,dtype=np.uint8))
            current_video_writer.release()
            current_request_record=dict(action='generate',images=[base64.b64encode(current_image_buffer.getvalue()).decode()],driving_video=base64.b64encode(current_video_path.read_bytes()).decode(),prompt='A male character.',frames=21,steps=40,seed=42,width=832,height=480)
            self.assertEqual(validate_animate_request(current_request_record)['frames'],21)
            with self.assertRaisesRegex(ValueError,'길이 부족'):
                validate_animate_request(dict(current_request_record,frames=29))
            with self.assertRaisesRegex(ValueError,'4n'):
                validate_animate_request(dict(current_request_record,frames=20))
            with self.assertRaisesRegex(ValueError,'width'):
                validate_animate_request(dict(current_request_record,width=640))

    def test_registered_shared_commands(self):
        for current_command_name in ('generate','status','history','history-delete','history-reset','prioritize','resume','cancel','model-status'):
            self.assertIn(current_command_name,MANAGEMENT_SERVICE_COMMANDS['wan22-animate2'])
        with self.assertRaisesRegex(ValueError,'폐기'):
            resolve_management_command('wan22-animate','generate',{})

    def test_unknown_pose_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError,'필드'):
            validate_animate_request({'pose_video':'abc'})

    def test_motion_saved_with_integrity_hash(self):
        import hashlib
        current_video_bytes=b'0000ftyp-test'
        with tempfile.TemporaryDirectory() as current_test_path:
            current_result_record=AnimateTwoGenerationManager().save_generation_attachments(Path(current_test_path),{'driving_video':base64.b64encode(current_video_bytes).decode(),'prompt':'test'})
            self.assertEqual((Path(current_test_path)/'driving.mp4').read_bytes(),current_video_bytes)
            self.assertEqual(current_result_record['driving_video_sha256'],hashlib.sha256(current_video_bytes).hexdigest())
            self.assertNotIn('driving_video',current_result_record)

    def test_ui_builds_without_model_loading(self):
        from tools.review.ui.gradio.wan_animate2_app import build_animate_interface
        current_ui_blocks=build_animate_interface('http://127.0.0.1:8770')
        self.assertGreater(len(current_ui_blocks.blocks),20)
