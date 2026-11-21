"""VACE VAE 경계 검사와 공식 메서드 복원을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import torch
from generators.wan_vace.vae_numerical_guard import guard_vace_vae_boundaries


class FakeVaceInnerModel:
    def encode(self, current_input_value):
        return current_input_value

    def decode(self, current_input_value):
        return current_input_value


class FakeVacePipeline:
    def __init__(self):
        self.vae = SimpleNamespace(model=FakeVaceInnerModel())

    def vace_encode_frames(self, current_input_value):
        return [self.vae.model.encode(current_input_value)]

    def vace_encode_masks(self, current_input_value):
        return [current_input_value]

    def vace_latent(self, current_input_value):
        return {'context': current_input_value}


class VaceVaeNumericalGuardTest(unittest.TestCase):
    def test_finite_values_preserve_results_and_restore_methods(self):
        current_pipeline_object = FakeVacePipeline()
        current_tensor_value = torch.ones((2, 3)).t()
        with tempfile.TemporaryDirectory() as current_directory_name:
            with guard_vace_vae_boundaries(current_pipeline_object, Path(current_directory_name), torch) as current_check_counts:
                current_frame_values = current_pipeline_object.vace_encode_frames(current_tensor_value)
                self.assertIs(current_frame_values[0], current_tensor_value)
                current_pipeline_object.vace_encode_masks(current_tensor_value)
                current_pipeline_object.vace_latent(current_frame_values)
                self.assertIs(current_pipeline_object.vae.model.decode(current_tensor_value), current_tensor_value)
                self.assertEqual(current_check_counts['vae-encode-output'], 1)
                self.assertEqual(current_check_counts['vae-decode-before-clamp'], 1)
                self.assertEqual(current_check_counts['condition-context'], 1)
            self.assertNotIn('encode', vars(current_pipeline_object.vae.model))
            self.assertNotIn('vace_latent', vars(current_pipeline_object))

    def test_infinity_is_caught_before_decoder_clamp_and_restores(self):
        current_pipeline_object = FakeVacePipeline()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with self.assertRaisesRegex(ValueError, 'vae-decode-before-clamp'):
                with guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, torch):
                    current_pipeline_object.vae.model.decode(torch.tensor([float('inf')])).clamp_(-1, 1)
            current_failure_record = json.loads((current_attempt_root / 'numerical-failure.json').read_text())
            self.assertEqual(current_failure_record['stage'], 'vae-decode-before-clamp')
            self.assertEqual(current_failure_record['shape'], [1])
            from safetensors.torch import load_file
            current_saved_tensors = load_file(str(current_attempt_root / 'numerical-failure.safetensors'))
            self.assertTrue(torch.isinf(current_saved_tensors['output']).all())
            self.assertTrue(torch.isinf(current_saved_tensors['input']).all())
            self.assertNotIn('decode', vars(current_pipeline_object.vae.model))

    def test_nonfinite_nested_condition_is_rejected(self):
        current_pipeline_object = FakeVacePipeline()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            with self.assertRaisesRegex(ValueError, 'condition-context'):
                with guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, torch):
                    current_pipeline_object.vace_latent([torch.tensor([float('nan')])])
            current_failure_record = json.loads((current_attempt_root / 'numerical-failure.json').read_text())
            self.assertEqual(current_failure_record['stage'], 'condition-context')
            self.assertEqual(current_failure_record['value_path'], 'output.context[0]')

    def test_existing_instance_method_is_restored(self):
        current_pipeline_object = FakeVacePipeline()
        current_instance_method = lambda current_value_object: current_value_object
        current_pipeline_object.vace_latent = current_instance_method
        with tempfile.TemporaryDirectory() as current_directory_name:
            with guard_vace_vae_boundaries(current_pipeline_object, Path(current_directory_name), torch):
                current_pipeline_object.vace_latent(torch.ones(1))
        self.assertIs(current_pipeline_object.vace_latent, current_instance_method)
