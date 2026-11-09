"""RGB V2V의 영상 보존·입력 거절·공용 서비스 연결을 검증한다."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from generators.wan_v2v.contracts import validate_v2v_request, read_v2v_frames
from tools.review.domains.wan_v2v.generation import WanVideoEditingManager
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command


class WanVideoEditingTests(unittest.TestCase):
    def setUp(self):
        self.current_test_directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_test_directory.cleanup)
        self.current_video_path=Path(self.current_test_directory.name)/'test.mp4'
        current_video_writer=cv2.VideoWriter(str(self.current_video_path),cv2.VideoWriter_fourcc(*'mp4v'),16,(832,480))
        for current_frame_index in range(9):
            current_video_writer.write(np.full((480,832,3),current_frame_index*20,dtype=np.uint8))
        current_video_writer.release()
        self.current_request_record=dict(action='generate',input_video=base64.b64encode(self.current_video_path.read_bytes()).decode(),prompt='A person punches quickly.',negative_prompt='',denoising_strength=.3,frames=9,steps=20,seed=42,width=832,height=480)

    def test_video_frame_order_and_rate_preserved(self):
        current_frame_images,current_frame_rate=read_v2v_frames(self.current_video_path,9)
        self.assertEqual(current_frame_rate,16)
        self.assertEqual(len(current_frame_images),9)
        self.assertGreater(np.asarray(current_frame_images[-1]).mean(),np.asarray(current_frame_images[0]).mean())
        self.assertEqual(validate_v2v_request(self.current_request_record)['images'],[])
        with self.assertRaisesRegex(ValueError,'길이 부족'):
            validate_v2v_request(dict(self.current_request_record,frames=13))

    def test_strict_payload_rejections(self):
        for current_changed_fields in ({'images':[]},{'denoising_strength':float('nan')},{'denoising_strength':1},{'denoising_strength':0},{'denoising_strength':True},{'frames':8},{'steps':20.0},{'input_video':'bad!'}):
            with self.subTest(current_changed_fields=current_changed_fields),self.assertRaises(ValueError):
                validate_v2v_request(dict(self.current_request_record,**current_changed_fields))

    def test_video_snapshot_and_ui_restore(self):
        from tools.review.ui.gradio.wan_v2v_app import restore_v2v_inputs
        current_storage_path=Path(self.current_test_directory.name)
        current_job_path=current_storage_path/'test-job';current_job_path.mkdir()
        current_saved_request=WanVideoEditingManager().save_generation_attachments(current_job_path,validate_v2v_request(self.current_request_record))
        self.assertNotIn('input_video',current_saved_request)
        self.assertEqual(current_saved_request['input_video_sha256'],hashlib.sha256(self.current_video_path.read_bytes()).hexdigest())
        with patch('tools.review.ui.gradio.wan_v2v_app.V2V_JOB_STORAGE',current_storage_path):
            current_restored_values=restore_v2v_inputs({'id':'test-job','request':current_saved_request})
        self.assertEqual(current_restored_values[3:7],(.3,9,20,42))

    def test_gateway_and_composed_ui(self):
        for current_command_name in ('generate','status','history','history-delete','history-reset','prioritize','resume','cancel','model-status'):
            self.assertIn(current_command_name,MANAGEMENT_SERVICE_COMMANDS['wan22-v2v'])
        from tools.review.ui.gradio.wan_v2v_app import build_v2v_interface
        from tools.review.ui.gradio.management_menu_app import compose_management_interface
        current_interface_blocks=compose_management_interface(build_v2v_interface('http://127.0.0.1:8770'),8770)
        self.assertGreater(len(current_interface_blocks.blocks),20)

    def test_worker_passes_rgb_to_input_video_not_control(self):
        import sys
        import types
        from unittest.mock import MagicMock
        from PIL import Image
        from generators.wan_v2v.worker import execute_v2v_inference
        current_pipeline_mock=MagicMock()
        current_pipeline_mock.return_value=[Image.new('RGB',(832,480)) for current_frame_index in range(9)]
        current_module_mock=types.ModuleType('diffsynth.pipelines.wan_video')
        current_module_mock.WanVideoPipeline=MagicMock()
        current_module_mock.WanVideoPipeline.from_pretrained.return_value=current_pipeline_mock
        current_module_mock.ModelConfig=MagicMock()
        current_job_path=Path(self.current_test_directory.name)/'job';current_job_path.mkdir()
        current_attempt_path=current_job_path/'attempt';current_attempt_path.mkdir()
        current_saved_request=WanVideoEditingManager().save_generation_attachments(current_job_path,validate_v2v_request(self.current_request_record))
        with patch.dict(sys.modules,{'diffsynth.pipelines.wan_video':current_module_mock}),patch('torch.cuda.mem_get_info',return_value=(8*1024**3,8*1024**3)),patch('generators.wan_v2v.worker.save_video_outputs',return_value=[]):
            current_result_record=execute_v2v_inference(current_job_path,current_attempt_path,current_saved_request,MagicMock())
        current_call_values=current_pipeline_mock.call_args.kwargs
        self.assertEqual(len(current_call_values['input_video']),9)
        self.assertEqual(current_call_values['denoising_strength'],.3)
        self.assertNotIn('control_video',current_call_values)
        self.assertNotIn('reference_image',current_call_values)
        self.assertEqual(current_result_record['fps'],16)
        self.assertEqual(current_call_values['switch_DiT_boundary'],.875)
