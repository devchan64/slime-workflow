"""Animate-2 서비스와 구형 폐기 계약을 구분한다."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from generators.wan_animate2.contracts import validate_animate_request
from tools.management.domains.wan_animate2.generation import AnimateTwoGenerationManager
from tools.management.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS


class AnimateTwoContractTests(unittest.TestCase):
    def test_flex_head_splitting_is_restricted_to_known_mask(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import torch
        import generators.wan_animate2.attention_layout as layout
        class SimulatedRocmTensor(torch.Tensor):
            @property
            def is_cuda(self):
                return True
        class CurrentTransformerModel:
            def create_mask(self):
                def attention_mask_logic(current_batch,current_head,current_query,current_key):
                    return current_query >= 0
                return attention_mask_logic
        current_dispatch_calls=[]
        def original_dispatch(current_query,current_key,current_value,**current_keywords):
            current_dispatch_calls.append(current_query.shape[2])
            return current_query+current_key.mean(dim=1,keepdim=True)+current_value.mean(dim=1,keepdim=True)
        current_module=SimpleNamespace(WanAnimate2Transformer3DModel=CurrentTransformerModel,dispatch_attention_fn=original_dispatch)
        current_torch_module=SimpleNamespace(version=SimpleNamespace(hip='test'),cuda=SimpleNamespace(mem_get_info=lambda device:(4*1024**3,0)),cat=torch.cat)
        layout.install_animate_reference_layout(current_module,current_torch_module)
        current_query=torch.rand((1,16,8,4)).as_subclass(SimulatedRocmTensor)
        current_key=torch.rand((1,24,8,4)).as_subclass(SimulatedRocmTensor)
        current_value=torch.rand((1,24,8,4)).as_subclass(SimulatedRocmTensor)
        current_mask=SimpleNamespace(mask_mod=CurrentTransformerModel().create_mask())
        with patch.object(layout,'ANIMATE_ATTENTION_MINIMUM_TOKENS',8):
            current_result=current_module.dispatch_attention_fn(current_query,current_key,current_value,attn_mask=current_mask,backend='flex',parallel_config=None)
            self.assertEqual(current_dispatch_calls,[4,4])
            self.assertTrue(torch.equal(current_result,current_query+current_key.mean(dim=1,keepdim=True)+current_value.mean(dim=1,keepdim=True)))
            current_dispatch_calls.clear()
            current_mask.mask_mod=lambda current_batch,current_head,current_query,current_key: current_head == 0
            current_module.dispatch_attention_fn(current_query,current_key,current_value,attn_mask=current_mask,backend='flex',parallel_config=None)
            self.assertEqual(current_dispatch_calls,[8])

    def test_reference_attention_layout_preserves_values_and_memory_guard(self):
        import torch
        from generators.wan_animate2.attention_layout import prepare_animate_attention_layout
        current_query_tensor=torch.arange(240,dtype=torch.float32).reshape(1,10,3,8)
        current_tensor_values=(current_query_tensor,current_query_tensor+1,current_query_tensor+2)
        current_result_values,current_changed_flag=prepare_animate_attention_layout(*current_tensor_values,3*1024**3,current_minimum_tokens=8)
        self.assertTrue(current_changed_flag)
        for current_before_tensor,current_after_tensor in zip(current_tensor_values,current_result_values):
            self.assertTrue(torch.equal(current_before_tensor,current_after_tensor))
            self.assertTrue(current_after_tensor.transpose(1,2).is_contiguous())
        current_skipped_values,current_changed_flag=prepare_animate_attention_layout(*current_tensor_values,0,current_minimum_tokens=8)
        self.assertFalse(current_changed_flag)
        self.assertIs(current_skipped_values[0],current_query_tensor)
        self.assertFalse(prepare_animate_attention_layout(*current_tensor_values,3*1024**3,current_minimum_tokens=100)[1])

    def test_animate_allocator_overrides_conflicting_legacy_settings(self):
        from generators.wan_animate2.worker import configure_animate_memory_allocator
        current_environment_values={'PYTORCH_ALLOC_CONF':'expandable_segments:True','PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True','OTHER':'keep'}
        configure_animate_memory_allocator(current_environment_values)
        self.assertEqual(current_environment_values,{'PYTORCH_ALLOC_CONF':'expandable_segments:False','OTHER':'keep'})

    def test_nonfinite_scheduler_and_video_output_fail_before_conversion(self):
        import numpy as np
        import torch
        from generators.wan_animate2.worker import check_animate_finite_tensor, guard_animate_vae_encoding, validate_animate_output_frames
        check_animate_finite_tensor(torch.tensor([0.5]), torch, '검사')
        with self.assertRaisesRegex(ValueError, 'NaN'):
            check_animate_finite_tensor(torch.tensor([float('nan')]), torch, '예측값')
        with self.assertRaisesRegex(ValueError, '무한대'):
            validate_animate_output_frames(np.array([0.0,float('inf')]), np)
        current_guarded_encoder=guard_animate_vae_encoding(lambda value: value,torch)
        self.assertTrue(torch.equal(current_guarded_encoder(torch.tensor([1.0])),torch.tensor([1.0])))
        with self.assertRaisesRegex(ValueError, 'VAE 인코딩 출력'):
            current_guarded_encoder(torch.tensor([float('nan')]))
        current_valid_frames=np.zeros((2,2,2,3),dtype=np.uint8)
        self.assertIs(validate_animate_output_frames(current_valid_frames,np),current_valid_frames)

    def test_vae_math_attention_is_scoped_and_restores_after_failure(self):
        import torch
        from generators.wan_animate2.worker import install_animate_vae_math_attention

        class ExampleVaeModel:
            def encode(self, current_should_fail=False):
                self.asserted_flags = (torch.backends.cuda.math_sdp_enabled(), torch.backends.cuda.flash_sdp_enabled())
                if current_should_fail:
                    raise RuntimeError('expected')
                return 'encoded'

            def decode(self):
                return (torch.backends.cuda.math_sdp_enabled(), torch.backends.cuda.flash_sdp_enabled())

        current_vae_model = ExampleVaeModel()
        current_original_flags = (torch.backends.cuda.math_sdp_enabled(), torch.backends.cuda.flash_sdp_enabled())
        install_animate_vae_math_attention(current_vae_model)
        self.assertEqual(current_vae_model.encode(), 'encoded')
        self.assertEqual(current_vae_model.asserted_flags, (True, False))
        self.assertEqual(current_vae_model.decode(), (True, False))
        with self.assertRaisesRegex(RuntimeError, 'expected'):
            current_vae_model.encode(True)
        self.assertEqual((torch.backends.cuda.math_sdp_enabled(), torch.backends.cuda.flash_sdp_enabled()), current_original_flags)

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
            current_request_record=dict(action='generate',images=[base64.b64encode(current_image_buffer.getvalue()).decode()],driving_video=base64.b64encode(current_video_path.read_bytes()).decode(),prompt='A male character.',frames=13,steps=40,seed=42,width=832,height=480)
            self.assertEqual(validate_animate_request(current_request_record)['frames'],13)
            from generators.wan_animate2.contracts import ANIMATE_MAXIMUM_SEED_VALUE
            self.assertEqual(validate_animate_request(dict(current_request_record,seed=ANIMATE_MAXIMUM_SEED_VALUE))['seed'],ANIMATE_MAXIMUM_SEED_VALUE)
            with self.assertRaisesRegex(ValueError,'seed'):
                validate_animate_request(dict(current_request_record,seed=ANIMATE_MAXIMUM_SEED_VALUE+1))
            with self.assertRaisesRegex(ValueError,'길이 부족'):
                validate_animate_request(dict(current_request_record,frames=17))
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
        from tools.management.ui.gradio.wan_animate2_app import build_animate_interface
        current_ui_blocks=build_animate_interface('http://127.0.0.1:8770')
        self.assertGreater(len(current_ui_blocks.blocks),20)
