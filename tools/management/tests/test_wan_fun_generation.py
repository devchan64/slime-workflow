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
from tools.management.common.management_gateway import resolve_management_command

class FunAttentionOptimizationTests(unittest.TestCase):
    def test_fun_allocator_disables_expandable_segments_and_legacy_override(self):
        from generators.wan_fun.worker import configure_fun_memory_allocator
        current_environment_values = {'PYTORCH_ALLOC_CONF': 'expandable_segments:True', 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True', 'KEEP': 'yes'}
        configure_fun_memory_allocator(current_environment_values)
        self.assertEqual(current_environment_values, {'PYTORCH_ALLOC_CONF': 'expandable_segments:False', 'KEEP': 'yes'})

    def test_conditioning_fingerprint_detects_changed_tensors(self):
        import torch
        from generators.wan_fun.numerical_diagnostics import fingerprint_fun_tensor
        current_first_record = fingerprint_fun_tensor(torch, torch.tensor([1.0, 2.0]))
        current_same_record = fingerprint_fun_tensor(torch, torch.tensor([1.0, 2.0]))
        current_changed_record = fingerprint_fun_tensor(torch, torch.tensor([1.0, 3.0]))
        self.assertEqual(current_first_record, current_same_record)
        self.assertNotEqual(current_first_record['sha256'], current_changed_record['sha256'])
        self.assertFalse(fingerprint_fun_tensor(torch, torch.tensor([float('nan')]))['finite'])

    def test_vae_guard_rejects_infinity_before_clamp_and_restores(self):
        import json
        import torch
        from generators.wan_fun.numerical_diagnostics import guard_fun_vae_method
        class FakeFunVaeModel:
            def decode(self, current_input_tensor):
                return current_input_tensor
        current_inner_model = FakeFunVaeModel()
        current_vae_model = SimpleNamespace(first_stage_model=current_inner_model)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with self.assertRaisesRegex(ValueError, 'decode'):
                with guard_fun_vae_method(current_vae_model, current_attempt_root, torch, 'decode'):
                    current_inner_model.decode(torch.tensor([float('inf')])).clamp_(0, 1)
            self.assertEqual(json.loads((current_attempt_root / 'numerical-failure.json').read_text())['stage'], 'vae-decode-before-postprocessing')
            from safetensors.torch import load_file
            self.assertTrue(torch.isinf(load_file(str(current_attempt_root / 'numerical-failure.safetensors'))['output']).all())
            self.assertNotIn('decode', vars(current_inner_model))
            current_input_tensor = torch.ones(1)
            with guard_fun_vae_method(current_vae_model, current_attempt_root, torch, 'decode'):
                self.assertIs(current_inner_model.decode(current_input_tensor), current_input_tensor)

    def test_fingerprint_records_original_layout_and_dtype(self):
        import torch
        from generators.wan_fun.numerical_diagnostics import fingerprint_fun_tensor
        current_input_tensor = torch.arange(6, dtype=torch.bfloat16).reshape(2, 3).t()
        current_record_value = fingerprint_fun_tensor(torch, current_input_tensor)
        self.assertEqual(current_record_value['stride'], list(current_input_tensor.stride()))
        self.assertEqual(current_record_value['dtype'], 'torch.bfloat16')
        self.assertEqual(current_record_value['hash_representation'], 'cpu-float32-contiguous')

    def test_attention_path_records_callable_without_claiming_kernel(self):
        import torch
        from generators.wan_fun.numerical_diagnostics import describe_fun_vae_attention
        current_model_object = torch.nn.Module()
        current_model_object.optimized_attention = torch.nn.functional.scaled_dot_product_attention
        current_path_values = describe_fun_vae_attention(SimpleNamespace(first_stage_model=current_model_object))
        self.assertEqual(len(current_path_values), 1)
        self.assertIn('scaled_dot_product_attention', current_path_values[0])

    def test_optional_vae_attention_compares_matching_pytorch_and_restores(self):
        import json
        import torch
        import torch.nn.functional as torch_functional_module
        from generators.wan_fun.numerical_diagnostics import guard_fun_vae_attention
        def pytorch_attention(current_query_tensor, current_key_tensor, current_value_tensor):
            current_batch_count, current_channel_count = current_query_tensor.shape[:2]
            current_attention_inputs = [current_tensor.reshape(current_batch_count, 1, current_channel_count, -1).transpose(2, 3).contiguous() for current_tensor in (current_query_tensor, current_key_tensor, current_value_tensor)]
            return torch_functional_module.scaled_dot_product_attention(*current_attention_inputs).transpose(2, 3).reshape(current_query_tensor.shape)
        pytorch_attention.__module__ = 'comfy.ldm.modules.diffusionmodules.model'
        current_model_object = torch.nn.Module()
        current_model_object.optimized_attention = pytorch_attention
        current_vae_model = SimpleNamespace(first_stage_model=current_model_object)
        current_input_tensor = torch.arange(12, dtype=torch.float32).reshape(1, 3, 2, 2)
        current_expected_tensor = pytorch_attention(current_input_tensor, current_input_tensor, current_input_tensor)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with guard_fun_vae_attention(current_vae_model, current_attempt_root, torch, 'encode'):
                current_output_tensor = current_model_object.optimized_attention(current_input_tensor, current_input_tensor, current_input_tensor)
                self.assertTrue(torch.equal(current_output_tensor, current_expected_tensor))
            self.assertIs(current_model_object.optimized_attention, pytorch_attention)
            current_record_value = json.loads((current_attempt_root / 'vae-attention-encode.json').read_text())
            self.assertEqual(current_record_value['status'], 'compared')
            self.assertTrue((current_attempt_root / 'vae-attention-encode.safetensors').exists())
            self.assertIn('mean_absolute_error', current_record_value['default_vs_math'])
            self.assertEqual(current_record_value['sdpa_inputs']['query']['shape'], [1, 1, 4, 3])
            self.assertEqual(current_record_value['sdpa_scale'], 'default: 1/sqrt(head_dim)')

    def test_attention_difference_statistics_do_not_overflow(self):
        import torch
        from generators.wan_fun.numerical_diagnostics import measure_fun_attention_difference
        current_high_tensor = torch.tensor([3e38], dtype=torch.float32)
        current_low_tensor = torch.tensor([-3e38], dtype=torch.float32)
        current_record_value = measure_fun_attention_difference(current_high_tensor, current_low_tensor, torch)
        self.assertGreater(current_record_value['max_absolute_error'], 5e38)
        self.assertEqual(current_record_value['statistics_dtype'], 'float64')

    def test_nonfinite_vae_attention_output_is_preserved(self):
        import torch
        from safetensors.torch import load_file
        from generators.wan_fun.numerical_diagnostics import guard_fun_vae_attention
        def current_attention_function(current_query_tensor, current_key_tensor, current_value_tensor):
            return torch.full_like(current_query_tensor, float('inf'))
        current_model_object = torch.nn.Module()
        current_model_object.optimized_attention = current_attention_function
        current_input_tensor = torch.ones((1, 1, 1, 1))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with self.assertRaisesRegex(ValueError, '어텐션 출력'):
                with guard_fun_vae_attention(SimpleNamespace(first_stage_model=current_model_object), current_attempt_root, torch, 'decode'):
                    current_model_object.optimized_attention(current_input_tensor, current_input_tensor, current_input_tensor)
            current_saved_tensors = load_file(str(current_attempt_root / 'numerical-failure.safetensors'))
            self.assertTrue(torch.isinf(current_saved_tensors['default']).all())
            self.assertIs(current_model_object.optimized_attention, current_attention_function)

    def test_optional_vae_attention_skips_unknown_path(self):
        import json
        import torch
        from generators.wan_fun.numerical_diagnostics import guard_fun_vae_attention
        def normal_attention(current_query_tensor, current_key_tensor, current_value_tensor):
            return current_query_tensor
        current_model_object = torch.nn.Module()
        current_model_object.optimized_attention = normal_attention
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with guard_fun_vae_attention(SimpleNamespace(first_stage_model=current_model_object), current_attempt_root, torch, 'decode'):
                current_input_tensor = torch.ones((1, 1, 1, 1))
                self.assertIs(current_model_object.optimized_attention(current_input_tensor, current_input_tensor, current_input_tensor), current_input_tensor)
            self.assertEqual(json.loads((current_attempt_root / 'vae-attention-decode.json').read_text())['status'], 'comparison-skipped')

    def test_numerical_diagnostics_record_first_nonfinite_step(self):
        import json
        import torch
        from generators.wan_fun.numerical_diagnostics import record_fun_numerical_step
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            record_fun_numerical_step(torch, current_attempt_root, 'high', 1, torch.tensor([2.0]), torch.tensor([-3.0]))
            with self.assertRaisesRegex(ValueError, '2단계'):
                record_fun_numerical_step(torch, current_attempt_root, 'high', 2, torch.tensor([float('nan')]), torch.tensor([1.0]))
            current_records = [json.loads(current_line) for current_line in (current_attempt_root / 'numerical-steps.jsonl').read_text().splitlines()]
            self.assertEqual(current_records[0]['sample']['max_abs'], 3.0)
            self.assertEqual(current_records[1]['denoised']['nonfinite'], 1)
            self.assertIsNone(current_records[1]['denoised']['max_abs'])
            self.assertEqual(current_records[1]['denoised']['dtype'], 'torch.float32')
            self.assertTrue((current_attempt_root / 'numerical-failure.safetensors').exists())

    def test_long_attention_uses_contiguous_inputs_only_with_room(self):
        from generators.wan_fun.attention_optimization import install_fun_attention_optimization
        current_cuda_mock = SimpleNamespace(is_available=lambda:True,get_device_properties=lambda _:SimpleNamespace(gcnArchName='gfx1151'),mem_get_info=Mock(return_value=(2**40,2**40)),OutOfMemoryError=MemoryError,empty_cache=Mock())
        current_torch_mock = SimpleNamespace(version=SimpleNamespace(hip='7.15'),cuda=current_cuda_mock,float16='fp16',bfloat16='bf16')
        current_attention_mock = Mock(return_value='result')
        current_ops_mock = SimpleNamespace(scaled_dot_product_attention=current_attention_mock)
        def make_test_tensor(current_sequence_length):
            return SimpleNamespace(ndim=4,device=SimpleNamespace(type='cuda'),shape=(2,40,current_sequence_length,128),dtype='fp16',numel=lambda:100,element_size=lambda:2,is_contiguous=lambda:False,contiguous=Mock(return_value='contiguous'))
        self.assertTrue(install_fun_attention_optimization(current_torch_mock,current_ops_mock))
        current_tensors = [make_test_tensor(46800) for _ in range(3)]
        self.assertEqual(current_ops_mock.scaled_dot_product_attention(*current_tensors), 'result')
        current_attention_mock.assert_called_with('contiguous','contiguous','contiguous')
        current_cuda_mock.mem_get_info.return_value = (0,2**40)
        current_ops_mock.scaled_dot_product_attention(*current_tensors)
        current_attention_mock.assert_called_with(*current_tensors)
        current_cuda_mock.mem_get_info.return_value = (2**40,2**40)
        current_tensors[0].contiguous.side_effect = MemoryError('GPU 메모리 부족')
        current_ops_mock.scaled_dot_product_attention(*current_tensors)
        current_attention_mock.assert_called_with(*current_tensors)
        current_cuda_mock.empty_cache.assert_called_once()
        current_short_tensors = [make_test_tensor(512) for _ in range(3)]
        current_ops_mock.scaled_dot_product_attention(*current_short_tensors)
        current_attention_mock.assert_called_with(*current_short_tensors)

    def test_direct_gpu_loader_restores_model_builder_on_failure(self):
        from generators.wan_fun.gpu_direct_loader import load_fun_gpu_unet
        class TestFunConfig:
            def get_model(self, current_state_dict, current_prefix='', device=None):
                return None
        current_original_builder = TestFunConfig.get_model
        current_torch_mock = SimpleNamespace(device=lambda value:value,bfloat16='bf16',cuda=SimpleNamespace(mem_get_info=lambda _: (8*1024**3, 8*1024**3)))
        current_folder_mock = SimpleNamespace(get_full_path_or_raise=lambda *_: __file__)
        current_utils_mock = SimpleNamespace(load_torch_file=Mock(side_effect=RuntimeError('로드 오류')))
        with self.assertRaisesRegex(RuntimeError, '로드 오류'):
            load_fun_gpu_unet(current_torch_mock,current_folder_mock,SimpleNamespace(),current_utils_mock,SimpleNamespace(WAN21_FunControl2V=TestFunConfig),'model')
        self.assertIs(TestFunConfig.get_model, current_original_builder)
        self.assertEqual(current_utils_mock.load_torch_file.call_args.kwargs['device'],'cuda:0')

class FunGenerationContractTests(unittest.TestCase):
    def test_model_prepare_button_submits_prepare_job(self):
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        from tools.management.ui.gradio.wan_fun_app import build_fun_interface
        current_command_mock = Mock(return_value={'id': 'prepare-job'})
        current_interface = build_fun_interface('http://localhost', current_command_mock)
        current_prepare_callback = next(current_function.fn for current_function in current_interface.fns.values()
            if current_function.fn and current_function.fn.__name__ == 'enqueue_fun_model_prepare')
        self.assertEqual(current_prepare_callback()[0], 'prepare-job')
        current_command_mock.assert_called_with('prepare', {'action': 'prepare'})
        current_manager = FunControlGenerationManager()
        current_request = current_manager.validate_generation_request({'action': 'prepare'})
        self.assertEqual(current_request, {'action': 'prepare', 'images': []})
        current_manager.validate_generation_runtime(current_request)
        self.assertEqual(current_manager.select_generation_runner(current_request), 'generators/wan_fun/prepare_worker.py')

    def test_model_prepare_rejects_duplicate_active_job(self):
        import json
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_directory = Path(current_temp_directory) / 'existing'
            current_job_directory.mkdir()
            (current_job_directory / 'request.json').write_text(json.dumps({'action': 'prepare'}))
            (current_job_directory / 'status.json').write_text(json.dumps({'status': 'queued'}))
            current_manager = FunControlGenerationManager()
            current_manager.job_storage_root = Path(current_temp_directory)
            with self.assertRaisesRegex(ValueError, '이미 진행 중'):
                current_manager.ensure_generation_request_available({'action': 'prepare'})
            (current_job_directory / 'status.json').write_text(json.dumps({'status': 'completed'}))
            current_manager.ensure_generation_request_available({'action': 'prepare'})

    def test_model_prepare_request_uses_rocm_setup_worker(self):
        import json
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        from tools.management.tests.test_image_generation import ImageGenerationTests
        current_manager = FunControlGenerationManager()
        current_handler = ImageGenerationTests().make_http_handler('/wan22-fun-control/jobs', 'POST')
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_manager.job_storage_root = Path(current_temp_directory) / 'jobs'
            current_process_mock = Mock()
            current_process_mock.wait.return_value = 0
            current_process_mock.poll.return_value = 0
            with patch.object(current_manager, 'history_storage_path', return_value=Path(current_temp_directory) / 'history'), \
                    patch('tools.management.domains.image.image_generation.launch_gpu_process', return_value=current_process_mock) as current_launch_mock, \
                    patch('tools.management.domains.image.image_generation.threading.Thread'):
                current_manager.handle_image_request(current_handler)
            self.assertEqual(current_handler.status, 202)
            current_command_values = current_launch_mock.call_args.args[0]
            self.assertTrue(current_command_values[1].endswith('/generators/wan_fun/prepare_worker.py'))
            self.assertEqual(json.loads(current_handler.wfile.getvalue())['status'], 'running')

    def test_prepare_worker_reports_completion_without_video(self):
        import json
        from generators.wan_fun import prepare_worker
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_directory = Path(current_temp_directory) / 'job'
            current_job_directory.mkdir()
            (current_job_directory / 'request.json').write_text(json.dumps({'action': 'prepare'}))
            with patch.object(prepare_worker, 'FUN_JOB_STORAGE', Path(current_temp_directory)), \
                    patch.object(prepare_worker, 'setup_fun_rocm_environment'), \
                    patch('sys.argv', ['prepare_worker', '--job-dir', str(current_job_directory)]), \
                    patch('signal.signal'):
                prepare_worker.run_fun_prepare_worker()
            current_status = FunControlGenerationManager().read_generation_status_record(current_job_directory)
            self.assertEqual(current_status['status'], 'completed')
            self.assertNotIn('result_error', current_status)

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

    def test_soma_video_contract_and_saved_attachment(self):
        import cv2
        import numpy as np
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        from tools.management.ui.gradio.wan_fun_app import restore_fun_inputs
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_job_identifier = '2026-10-31_00-00-00-abcdef12'
            current_job_directory = Path(current_temporary_root)/current_job_identifier
            current_job_directory.mkdir()
            current_video_path = current_job_directory/'input.mp4'
            current_video_writer = cv2.VideoWriter(str(current_video_path), cv2.VideoWriter_fourcc(*'mp4v'), 30, (64, 64))
            for current_frame_index in range(9):
                current_video_writer.write(np.full((64, 64, 3), current_frame_index*20, dtype=np.uint8))
            current_video_writer.release()
            current_video_request = {**self.current_request_record, 'images': self.current_request_record['images'][:1], 'driving_video': base64.b64encode(current_video_path.read_bytes()).decode()}
            self.assertEqual(validate_fun_request(current_video_request)['frames'], 5)
            self.assertFalse(validate_fun_request(current_video_request)['pose_include_hands'])
            self.assertFalse(validate_fun_request(current_video_request)['pose_include_face'])
            for current_option_name in ('pose_include_hands', 'pose_include_face'):
                self.assertTrue(validate_fun_request({**current_video_request, current_option_name: True})[current_option_name])
                with self.assertRaises(ValueError):
                    validate_fun_request({**current_video_request, current_option_name: 'False'})
                with self.assertRaises(ValueError):
                    validate_fun_request({**self.current_request_record, current_option_name: False})
            with self.assertRaises(ValueError):
                validate_fun_request({**current_video_request, 'frames': 9})
            with self.assertRaises(ValueError):
                validate_fun_request({**current_video_request, 'control_type': 'depth'})
            with self.assertRaises(ValueError):
                validate_fun_request({**current_video_request, 'images': self.current_request_record['images']})
            current_saved_request = FunControlGenerationManager.save_generation_attachments(None, current_job_directory, current_video_request)
            self.assertNotIn('driving_video', current_saved_request)
            self.assertEqual((current_job_directory/'driving.mp4').read_bytes(), current_video_path.read_bytes())
            (current_job_directory/'reference-1.png').write_bytes(base64.b64decode(current_video_request['images'][0]))
            current_saved_request['references'] = ['reference-1.png']
            with patch('tools.management.ui.gradio.wan_fun_app.FUN_JOB_STORAGE', Path(current_temporary_root)), self.assertRaisesRegex(ValueError,'처리된 포즈 MP4'):
                restore_fun_inputs({'id':current_job_identifier,'request':current_saved_request})

    def test_pose_parts_preserve_body_and_select_details(self):
        from collections import namedtuple
        from generators.wan_fun.pose_preprocess import render_selected_pose_parts
        current_pose_type = namedtuple('Pose', 'body left_hand right_hand face')
        current_pose_record = current_pose_type(object(), object(), object(), object())
        current_draw_function = Mock(return_value='rendered')
        with patch.dict('sys.modules', {'generators.wan_fun.vendor.videox_fun.dwpose_utils': SimpleNamespace(draw_pose=current_draw_function)}):
            for current_hand_option, current_face_option in ((False, False), (True, False), (False, True), (True, True)):
                self.assertEqual(render_selected_pose_parts([current_pose_record], (512, 832), current_hand_option, current_face_option), 'rendered')
                current_selected_record = current_draw_function.call_args.args[0][0]
                self.assertIs(current_selected_record.body, current_pose_record.body)
                self.assertIs(current_selected_record.left_hand, current_pose_record.left_hand if current_hand_option else None)
                self.assertIs(current_selected_record.right_hand, current_pose_record.right_hand if current_hand_option else None)
                self.assertIs(current_selected_record.face, current_pose_record.face if current_face_option else None)

    def test_extended_frame_count_accepts_exact_controls(self):
        current_extended_record={**self.current_request_record,'frames':129,'images':self.current_request_record['images'][:1]*130}
        self.assertEqual(validate_fun_request(current_extended_record)['frames'],129)
        with self.assertRaises(ValueError):
            validate_fun_request({**current_extended_record,'images':current_extended_record['images'][:-1]})

    def test_rejects_invalid_and_ambiguous_inputs(self):
        for current_field_name, current_field_value in [('frames', 133), ('frames', 161), ('frames', 6), ('steps', True), ('images', []), ('flow_shift', float('nan')), ('guidance_scale', 0), ('control_type', 'rgb'), ('switch_ratio', 1), ('model', 'other')]:
            with self.subTest(field=current_field_name), self.assertRaises(ValueError):
                validate_fun_request({**self.current_request_record, current_field_name: current_field_value})

    def test_seed_bounds_match_generator_and_ui(self):
        import gradio as gr
        from generators.wan_fun.contracts import FUN_MAX_SEED_VALUE
        from generators.wan_fun.page.interface import build_fun_payload
        from tools.management.common.gradio_seed import build_generation_seed
        for current_seed_value in (0, FUN_MAX_SEED_VALUE):
            self.assertEqual(validate_fun_request({**self.current_request_record,'seed':current_seed_value})['seed'],current_seed_value)
        for current_seed_value in (-1, FUN_MAX_SEED_VALUE + 1):
            with self.subTest(seed=current_seed_value):
                with self.assertRaises(ValueError):
                    validate_fun_request({**self.current_request_record,'seed':current_seed_value})
                with self.assertRaisesRegex(ValueError,'시드는'):
                    build_fun_payload('reference.png',None,['control.png'],'pose','stand','',5,current_seed_value,20,5,6,0.5)
        with gr.Blocks() as current_interface_blocks:
            current_seed_control=build_generation_seed(42, maximum_seed_value=FUN_MAX_SEED_VALUE)
        self.assertEqual(current_seed_control.maximum,FUN_MAX_SEED_VALUE)
        with self.assertRaises(gr.Error):
            current_seed_control.preprocess(FUN_MAX_SEED_VALUE + 1)
        current_seed_callback=next(current_function for current_function in current_interface_blocks.fns.values() if current_function.fn.__name__=='generate_bounded_seed_value')
        with patch('tools.management.common.gradio_seed.secrets.randbelow',return_value=FUN_MAX_SEED_VALUE) as current_random_mock:
            self.assertEqual(current_seed_callback.fn(),FUN_MAX_SEED_VALUE)
            current_random_mock.assert_called_once_with(FUN_MAX_SEED_VALUE + 1)

    def test_ui_rejects_short_or_duplicate_control(self):
        from tools.management.ui.gradio.wan_fun_app import build_fun_payload
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
        from tools.management.ui.gradio.wan_fun_app import restore_fun_inputs
        with self.assertRaises(ValueError):
            restore_fun_inputs({'id':'../outside','request':{}})

class FunReferenceOnlyTests(unittest.TestCase):
    def test_retired_reference_mode_rejected(self):
        from generators.wan_fun.contracts import reject_retired_rgb_input
        from tools.management.ui.gradio.wan_fun_app import build_fun_payload
        with self.assertRaisesRegex(ValueError, '폐기'):
            reject_retired_rgb_input({'input_mode': 'reference-only'})
        with self.assertRaisesRegex(ValueError, '폐기'):
            build_fun_payload(None,None,None,'pose','stand','',9,42,20,5,6,.5,'reference-only')
