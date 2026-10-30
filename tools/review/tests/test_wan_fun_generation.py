"""Fun 입력과 공용 게이트웨이 경계 검증."""
import base64
import io
import tempfile
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
from PIL import Image
from generators.wan_fun.contracts import validate_fun_request, inspect_fun_assets
from tools.review.common.management_gateway import resolve_management_command

class FunGenerationContractTests(unittest.TestCase):
    def test_temporal_decode_override_preserves_shared_defaults(self):
        from generators.common.wan_video_memory import TiledWanVideoVae
        current_output_tensor = SimpleNamespace(ndim=4)
        current_vae_backend = SimpleNamespace(device=SimpleNamespace(type='cuda'), decode_tiled=Mock(return_value=current_output_tensor))
        current_vae_wrapper = TiledWanVideoVae(current_vae_backend)
        current_torch_module = SimpleNamespace(inference_mode=nullcontext)
        with patch.dict('sys.modules', {'torch': current_torch_module}):
            current_vae_wrapper.decode('latent')
            current_default_arguments = current_vae_backend.decode_tiled.call_args.kwargs
            current_vae_wrapper.decode('latent', current_temporal_tile_count=11)
            current_override_arguments = current_vae_backend.decode_tiled.call_args.kwargs
            self.assertEqual(current_default_arguments['tile_t'], 3)
            self.assertEqual(current_override_arguments, {**current_default_arguments, 'tile_t': 11})
            for current_invalid_value in (True, 0, 1, 2.5):
                with self.assertRaises(ValueError):
                    current_vae_wrapper.decode('latent', current_temporal_tile_count=current_invalid_value)

    def setUp(self):
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (832, 480), 'white').save(current_image_buffer, format='PNG')
        self.current_request_record = dict(action='generate', prompt='캐릭터가 걷는다.', negative_prompt='', images=[base64.b64encode(current_image_buffer.getvalue()).decode()]*6, width=832, height=480, frames=5, steps=20, seed=42, flow_shift=5, guidance_scale=6, switch_ratio=0.5, control_type='pose')

    def test_accepts_reference_and_control(self):
        self.assertEqual(validate_fun_request(self.current_request_record)['tag'], 'wan22-fun-control')
        self.assertEqual(resolve_management_command('wan22-fun-control', 'generate', self.current_request_record), ('POST', '/wan22-fun-control/jobs'))

    def test_extended_frame_count_accepts_exact_controls(self):
        current_extended_record={**self.current_request_record,'frames':129,'images':self.current_request_record['images'][:1]*130}
        self.assertEqual(validate_fun_request(current_extended_record)['frames'],129)
        with self.assertRaises(ValueError):
            validate_fun_request({**current_extended_record,'images':current_extended_record['images'][:-1]})

    def test_rejects_invalid_and_ambiguous_inputs(self):
        for current_field_name, current_field_value in [('frames', 133), ('frames', 6), ('steps', True), ('images', []), ('flow_shift', float('nan')), ('guidance_scale', 0), ('control_type', 'rgb'), ('switch_ratio', 1), ('model', 'other')]:
            with self.subTest(field=current_field_name), self.assertRaises(ValueError):
                validate_fun_request({**self.current_request_record, current_field_name: current_field_value})

    def test_ui_rejects_short_or_duplicate_control(self):
        from tools.review.ui.gradio.wan_fun_app import build_fun_payload
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_image_path = Path(current_temp_directory)/'input.png'
            Image.new('RGB', (832, 480), 'white').save(current_image_path)
            current_common_values = ['pose', '걷는다.', '', 5, 42, 20, 5, 6, 0.5]
            with self.assertRaises(ValueError):
                build_fun_payload(str(current_image_path), None, [str(current_image_path)], *current_common_values)
            with self.assertRaises(ValueError):
                build_fun_payload(str(current_image_path), 'video.mp4', [str(current_image_path)]*5, *current_common_values)
            self.assertEqual(len(build_fun_payload(str(current_image_path), None, [str(current_image_path)]*5, *current_common_values)['images']), 6)

    def test_restore_rejects_path_escape(self):
        from tools.review.ui.gradio.wan_fun_app import restore_fun_inputs
        with self.assertRaises(ValueError):
            restore_fun_inputs({'id':'../outside','request':{}})
