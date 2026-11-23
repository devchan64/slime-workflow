import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json

import torch
from safetensors.torch import save_file

from generators.wan_vace.lora_merge import _merge_adapter, merge_adapter
from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS, validate_vace_request


class VaceLoraMergeTests(unittest.TestCase):
    def test_combined_request_requires_four_step_preset(self):
        request = {**VACE_DEFAULT_SETTINGS, 'mode': 'text', 'action': 'generate', 'prompt': 'FIGHTSCENE',
                   'negative_prompt': '', 'images': [], 'width': 832, 'height': 480,
                   'lora_mode': 'fighting_lightning', 'steps': 4, 'flow_shift': 5, 'guidance_scale': 1}
        self.assertEqual(validate_vace_request(request)['lora_mode'], 'fighting_lightning')
        for field, value in (('steps', 20), ('flow_shift', 12), ('guidance_scale', 5), ('lora_mode', 'other')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_vace_request({**request, field: value})
        lightning_request = {**request, 'lora_mode': 'lightning'}
        self.assertEqual(validate_vace_request(lightning_request)['lora_mode'], 'lightning')
        self.assertEqual(validate_vace_request({**lightning_request, 'guidance_scale': 2})['guidance_scale'], 2)
        with self.assertRaises(ValueError):
            validate_vace_request({**lightning_request, 'steps': 20})
        fighting_request = {**request, 'lora_mode': 'fighting', 'steps': 20, 'flow_shift': 12, 'guidance_scale': 5}
        self.assertEqual(validate_vace_request(fighting_request)['lora_mode'], 'fighting')

    def test_fighting_only_requires_and_merges_fighting_without_lightning(self):
        from generators.wan_vace.official_runtime import apply_vace_loras
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        high, low = object(), object()
        with tempfile.TemporaryDirectory() as directory, \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', side_effect=AssertionError('Lightning 불필요')), \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', return_value=True), \
             patch('generators.wan_vace.lora_merge.merge_adapter', return_value=400) as merge, \
             patch('workflow.domains.wan_vace.generation.validate_vace_assets'):
            VaceVideoGenerationManager().validate_generation_runtime({'model_profile': 'official-bf16-resident-v1', 'lora_mode': 'fighting'})
            apply_vace_loras(high, low, 'fighting', Path(directory))
            self.assertEqual(len(merge.call_args_list), 1)
            self.assertIs(merge.call_args.args[0], high)
            record = json.loads((Path(directory) / 'lora-merge.json').read_text())
            self.assertEqual(record['mode'], 'fighting')
            self.assertIn('fighting_sha256', record)
            self.assertNotIn('lightning_sha256', record)
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets'), \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', return_value=False):
            with self.assertRaises(ValueError):
                VaceVideoGenerationManager().validate_generation_runtime({'model_profile': 'official-bf16-resident-v1', 'lora_mode': 'fighting'})

    def test_lightning_alone_does_not_require_or_merge_fighting(self):
        from generators.wan_vace.official_runtime import apply_vace_loras
        high, low = object(), object()
        with tempfile.TemporaryDirectory() as directory, \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', return_value=True), \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', side_effect=AssertionError('격투 LoRA 불필요')), \
             patch('generators.wan_vace.lora_merge.merge_adapter', return_value=400) as merge:
            apply_vace_loras(high, low, 'lightning', Path(directory))
            self.assertEqual([call.args[0] for call in merge.call_args_list], [high, low])
            record = json.loads((Path(directory) / 'lora-merge.json').read_text())
            self.assertEqual(record['mode'], 'lightning')
            self.assertNotIn('fighting_sha256', record)

    def test_combined_mode_checks_fighting_before_merging(self):
        from generators.wan_vace.official_runtime import apply_vace_loras
        with tempfile.TemporaryDirectory() as directory, \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', return_value=True), \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', return_value=False), \
             patch('generators.wan_vace.lora_merge.merge_adapter') as merge:
            with self.assertRaises(ValueError):
                apply_vace_loras(object(), object(), 'fighting_lightning', Path(directory))
            merge.assert_not_called()

    def test_lightning_readiness_does_not_require_fighting(self):
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        manager = VaceVideoGenerationManager()
        request = {'model_profile': 'official-bf16-resident-v1', 'lora_mode': 'lightning'}
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets'), \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', return_value=True), \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', side_effect=AssertionError('격투 LoRA 불필요')):
            manager.validate_generation_runtime(request)
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets'), \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', return_value=False):
            with self.assertRaises(ValueError):
                manager.validate_generation_runtime(request)

    def test_stacks_adapters_and_respects_alpha(self):
        model = torch.nn.Module()
        model.layer = torch.nn.Linear(2, 2, bias=False, dtype=torch.bfloat16)
        model.layer.weight.data.zero_()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / 'first.safetensors'
            second = Path(directory) / 'second.safetensors'
            save_file({'diffusion_model.layer.lora_down.weight': torch.tensor([[1., 2.]]),
                       'diffusion_model.layer.lora_up.weight': torch.tensor([[1.], [2.]]),
                       'diffusion_model.layer.alpha': torch.tensor(.5)}, str(first))
            save_file({'diffusion_model.layer.lora_A.weight': torch.tensor([[1., 0.]]),
                       'diffusion_model.layer.lora_B.weight': torch.tensor([[0.], [1.]])}, str(second))
            self.assertEqual(_merge_adapter(model, first, require_cuda=False), 1)
            self.assertEqual(_merge_adapter(model, second, require_cuda=False), 1)
            self.assertTrue(torch.equal(model.layer.weight.float(), torch.tensor([[.5, 1.], [2., 2.]])))
            with self.assertRaises(ValueError):
                merge_adapter(model, second)

    def test_rejects_unknown_or_mismatched_weights_before_mutating(self):
        model = torch.nn.Module()
        model.layer = torch.nn.Linear(2, 2, bias=False, dtype=torch.bfloat16)
        before = model.layer.weight.detach().clone()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.safetensors'
            save_file({'diffusion_model.layer.lora_A.weight': torch.ones(1, 2),
                       'diffusion_model.layer.lora_B.weight': torch.ones(2, 1),
                       'unexpected': torch.ones(1)}, str(path))
            with self.assertRaises(ValueError):
                _merge_adapter(model, path, require_cuda=False)
            self.assertTrue(torch.equal(before, model.layer.weight))
