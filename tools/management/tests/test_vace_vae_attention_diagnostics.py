"""생성 없이 VAE SDPA 진단의 범위와 기록을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
import torch.nn.functional as torch_functional_module
from safetensors.torch import load_file
from generators.wan_vace.vae_attention_diagnostics import capture_vace_vae_attention


class VaceVaeAttentionDiagnosticTest(unittest.TestCase):
    def test_same_inputs_and_mask_are_compared_and_function_restored(self):
        current_query_tensor = torch.arange(24, dtype=torch.float32).reshape(1, 1, 3, 8)[..., ::2]
        current_mask_tensor = torch.tensor([[True, True, False], [True, True, True], [True, False, True]])
        current_original_function = torch_functional_module.scaled_dot_product_attention
        current_expected_output = current_original_function(current_query_tensor, current_query_tensor, current_query_tensor, attn_mask=current_mask_tensor, scale=0.25)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            current_diagnostic_state = set()
            with capture_vace_vae_attention('encode', current_attempt_root, torch, current_diagnostic_state):
                current_actual_output = torch_functional_module.scaled_dot_product_attention(current_query_tensor, current_query_tensor, current_query_tensor, attn_mask=current_mask_tensor, scale=0.25)
            self.assertIs(torch_functional_module.scaled_dot_product_attention, current_original_function)
            self.assertTrue(torch.equal(current_actual_output, current_expected_output))
            current_record_value = json.loads((current_attempt_root / 'vae-sdpa-encode.json').read_text())
            self.assertEqual(current_record_value['status'], 'compared')
            self.assertEqual(current_record_value['inputs']['query']['stride'], list(current_query_tensor.stride()))
            self.assertEqual(current_record_value['options']['scale'], 0.25)
            self.assertTrue(all(current_record_value['outputs_finite'].values()))
            self.assertIn('relative_mean_error', current_record_value['default_vs_math'])
            self.assertTrue(torch.equal(load_file(str(current_attempt_root / 'vae-sdpa-encode.safetensors'))['attn_mask'], current_mask_tensor))

    def test_nonfinite_input_fails_and_restores(self):
        current_original_function = torch_functional_module.scaled_dot_product_attention
        current_query_tensor = torch.tensor([[[[float('nan')]]]])
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with self.assertRaisesRegex(ValueError, 'SDPA 입력'):
                with capture_vace_vae_attention('decode', current_attempt_root, torch, set()):
                    torch_functional_module.scaled_dot_product_attention(current_query_tensor, current_query_tensor, current_query_tensor)
            self.assertIs(torch_functional_module.scaled_dot_product_attention, current_original_function)
            self.assertFalse(json.loads((current_attempt_root / 'vae-sdpa-decode.json').read_text())['inputs_finite'])

    def test_large_finite_output_difference_does_not_overflow(self):
        from generators.wan_vace.vae_attention_diagnostics import measure_vace_difference
        current_high_tensor = torch.tensor([3e38], dtype=torch.float32)
        current_low_tensor = torch.tensor([-3e38], dtype=torch.float32)
        current_record_value = measure_vace_difference(current_high_tensor, current_low_tensor, torch)
        self.assertGreater(current_record_value['max_absolute_error'], 5e38)
        self.assertEqual(current_record_value['statistics_dtype'], 'float64')

    def test_nonfinite_default_output_is_saved_before_repeated_calls(self):
        current_input_tensor = torch.ones((1, 1, 1, 1))
        current_output_tensor = torch.full_like(current_input_tensor, float('nan'))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with patch.object(torch_functional_module, 'scaled_dot_product_attention', return_value=current_output_tensor) as current_original_mock:
                with self.assertRaisesRegex(ValueError, '기본 출력'):
                    with capture_vace_vae_attention('encode', current_attempt_root, torch, set()):
                        torch_functional_module.scaled_dot_product_attention(current_input_tensor, current_input_tensor, current_input_tensor)
                self.assertEqual(current_original_mock.call_count, 1)
            current_saved_tensors = load_file(str(current_attempt_root / 'numerical-failure.safetensors'))
            self.assertTrue(torch.isnan(current_saved_tensors['default']).all())
            self.assertEqual(json.loads((current_attempt_root / 'vae-sdpa-encode.json').read_text())['status'], 'nonfinite-output')

    def test_dropout_skips_comparison_and_executes_once(self):
        current_query_tensor = torch.ones((1, 1, 2, 2))
        current_output_tensor = torch.ones_like(current_query_tensor)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with patch.object(torch_functional_module, 'scaled_dot_product_attention', return_value=current_output_tensor) as current_original_mock:
                with capture_vace_vae_attention('encode', current_attempt_root, torch, set()):
                    self.assertIs(torch_functional_module.scaled_dot_product_attention(current_query_tensor, current_query_tensor, current_query_tensor, dropout_p=0.1), current_output_tensor)
                self.assertEqual(current_original_mock.call_count, 1)
            self.assertEqual(json.loads((current_attempt_root / 'vae-sdpa-encode.json').read_text())['status'], 'comparison-skipped')

    def test_guard_limits_diagnostic_to_vae_method_and_restores(self):
        from types import SimpleNamespace
        from generators.wan_vace.vae_numerical_guard import guard_vace_vae_boundaries
        current_original_function = torch_functional_module.scaled_dot_product_attention
        class FakeVaeModel:
            def encode(self, current_input_tensor):
                return torch_functional_module.scaled_dot_product_attention(current_input_tensor, current_input_tensor, current_input_tensor)
            def decode(self, current_input_tensor):
                return current_input_tensor
        class FakeVacePipeline:
            def __init__(self):
                self.vae = SimpleNamespace(model=FakeVaeModel())
            def vace_encode_frames(self, current_input_tensor):
                return self.vae.model.encode(current_input_tensor)
            def vace_encode_masks(self, current_input_tensor):
                return current_input_tensor
            def vace_latent(self, current_input_tensor):
                return current_input_tensor
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            current_pipeline_object = FakeVacePipeline()
            with guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, torch, True):
                self.assertIs(torch_functional_module.scaled_dot_product_attention, current_original_function)
                current_pipeline_object.vace_encode_frames(torch.ones((1, 1, 2, 2)))
                self.assertIs(torch_functional_module.scaled_dot_product_attention, current_original_function)
                current_pipeline_object.vace_encode_frames(torch.ones((1, 1, 2, 2)))
            self.assertEqual(json.loads((current_attempt_root / 'vae-sdpa-encode.json').read_text())['status'], 'compared')
