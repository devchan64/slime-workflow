import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generators.wan_vace import q8_assets
from workflow.common.management_gateway import resolve_management_command

class VaceQ8AssetTests(unittest.TestCase):
    def test_both_files_are_verified_and_missing_or_modified_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            samples = {'high': ('High/h.gguf', b'high'), 'low': ('Low/l.gguf', b'low')}
            files = {stage: (name, len(data), hashlib.sha256(data).hexdigest()) for stage, (name, data) in samples.items()}
            with patch.object(q8_assets, 'DIRECTORY', root), patch.object(q8_assets, 'FILES', files):
                self.assertFalse(q8_assets.inspect_q8_assets())
                for name, data in samples.values():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                self.assertTrue(q8_assets.inspect_q8_assets())
                (root / samples['low'][0]).write_bytes(b'LOW')
                self.assertFalse(q8_assets.inspect_q8_assets())

    def test_model_management_commands_validate_payload(self):
        self.assertEqual(resolve_management_command('wan22-vace-q8', 'prepare', {'action': 'prepare'}), ('POST', '/wan22-vace-q8/jobs'))
        self.assertEqual(resolve_management_command('wan22-vace-q8', 'model-status', {}), ('GET', '/wan22-vace-q8/model-status'))
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-vace-q8', 'prepare', {'action': 'prepare', 'path': '/tmp/test'})

class VaceQ8LinearTests(unittest.TestCase):
    def test_q8_linear_and_lora_strength_on_small_tensors(self):
        import numpy as np
        import torch
        import gguf
        from safetensors.torch import save_file
        from generators.wan_vace.q8_runtime import Q8Linear
        from generators.wan_vace.lora_merge import _merge_adapter
        weight = (np.arange(64, dtype=np.float32).reshape(2, 32) - 32) / 16
        packed = torch.from_numpy(gguf.quantize(weight, gguf.GGMLQuantizationType.Q8_0).copy())
        model = torch.nn.Module()
        model.layer = Q8Linear(packed, weight.shape)
        inputs = torch.ones((1, 32), dtype=torch.bfloat16)
        baseline = model.layer(inputs)
        self.assertTrue(torch.allclose(baseline, torch.nn.functional.linear(inputs, torch.from_numpy(weight).to(torch.bfloat16)), atol=0.3))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'adapter.safetensors'
            save_file({'layer.lora_A.weight': torch.ones((1,32)), 'layer.lora_B.weight': torch.ones((2,1))}, str(path))
            self.assertEqual(_merge_adapter(model, path, strength=0.5, require_cuda=False), 1)
            self.assertTrue(torch.allclose(model.layer(inputs), baseline + 16, atol=0.1))

class VaceQ8ContractTests(unittest.TestCase):
    def test_request_accepts_q8_and_explicit_fighting_strength(self):
        from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS, validate_vace_request
        request = {**VACE_DEFAULT_SETTINGS, 'action':'generate', 'mode':'text', 'prompt':'step', 'negative_prompt':'', 'images':[], 'width':832, 'height':480, 'model_profile':'q8-gguf-resident-v1', 'lora_mode':'fighting_lightning', 'fighting_strength':0.5, 'steps':4, 'guidance_scale':1, 'flow_shift':5}
        result = validate_vace_request(request)
        self.assertEqual(result['model_profile'], 'q8-gguf-resident-v1')
        self.assertEqual(result['fighting_strength'], 0.5)
        for strength in (-1, 0, 2.1, float('nan'), True):
            with self.subTest(strength=strength), self.assertRaises(ValueError):
                validate_vace_request({**request, 'fighting_strength':strength})
        with self.assertRaises(ValueError):
            validate_vace_request({**request, 'lora_mode':'lightning'})

    def test_memory_identity_is_distinct_and_conservative(self):
        import json
        from workflow.common.gpu_memory_history import identify_execution_command, estimate_required_memory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / 'request.json'
            request.write_text(json.dumps({'frames':49, 'model_profile':'q8-gguf-resident-v1'}))
            q8 = identify_execution_command(['python', '/workspace/generators/wan_vace/worker.py'], root, 'vram')
            request.write_text(json.dumps({'frames':49, 'model_profile':'official-bf16-resident-v1'}))
            bf16 = identify_execution_command(['python', '/workspace/generators/wan_vace/worker.py'], root, 'vram')
            self.assertNotEqual(q8, bf16)
            self.assertIn('wan-vace-q8:', q8)
            with patch('workflow.common.gpu_memory_history.load_recent_observations', return_value=[]):
                self.assertGreaterEqual(estimate_required_memory('image', 0, q8)['required_memory_mib'], 81920)

    def test_q8_preflight_checks_q8_and_both_loras(self):
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets') as assets, \
             patch('generators.wan_vace.lightning_lora.inspect_lightning_loras', return_value=True) as lightning, \
             patch('generators.wan_vace.fighting_lora.inspect_fighting_lora', return_value=True) as fighting:
            VaceVideoGenerationManager().validate_generation_runtime({'model_profile':'q8-gguf-resident-v1','lora_mode':'fighting_lightning'})
            assets.assert_called_once_with('q8-gguf-resident-v1')
            lightning.assert_called_once()
            fighting.assert_called_once()
