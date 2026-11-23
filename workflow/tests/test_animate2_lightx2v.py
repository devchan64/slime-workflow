import tempfile
import unittest
from pathlib import Path

import torch
from safetensors.torch import save_file

from generators.wan_animate2.lightx2v import apply_lightx2v_weights, plan_lightx2v_weights


class LightX2VTests(unittest.TestCase):
    def test_lcm_schedule_and_update_match_comfy_flow_equations(self):
        import sys
        source = str(Path(__file__).resolve().parents[2] / '.local/wan-animate2/diffusers/src')
        sys.path.insert(0, source)
        try:
            from generators.wan_animate2.lightx2v_scheduler import AnimateLightX2VScheduler
            scheduler = AnimateLightX2VScheduler()
            scheduler.set_timesteps(6, device='cpu')
            indices = [999 - int(i * 1000 / 6) for i in range(6)]
            raw = torch.arange(1, 1001, dtype=torch.float32) / 1000
            expected = 5 * raw / (1 + 4 * raw)
            torch.testing.assert_close(scheduler.sigmas, torch.cat((expected[indices], torch.zeros(1))))
            sample = torch.tensor([0.2, 0.6])
            prediction = torch.tensor([0.1, -0.2])
            generator = torch.Generator().manual_seed(5)
            noise = torch.randn(sample.shape, generator=torch.Generator().manual_seed(5))
            actual = scheduler.step(prediction, scheduler.timesteps[0], sample, generator=generator, return_dict=False)[0]
            x0 = sample - expected[indices[0]] * prediction
            torch.testing.assert_close(actual, expected[indices[1]] * noise + (1 - expected[indices[1]]) * x0)
            with self.assertRaisesRegex(ValueError, '순서'):
                scheduler.step(prediction, scheduler.timesteps[0], sample, return_dict=False)
        finally:
            sys.path.remove(source)

    def test_applies_low_rank_and_direct_deltas(self):
        class Block(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.self_attn = torch.nn.Module()
                self.self_attn.to_q = torch.nn.Linear(2, 3)
                self.norm3 = torch.nn.LayerNorm(3)

        model = torch.nn.Module()
        model.blocks = torch.nn.ModuleList([Block()])
        original = {name: value.clone() for name, value in model.state_dict().items()}
        down = torch.tensor([[1., 2.]])
        up = torch.tensor([[2.], [3.], [4.]])
        data = {
            'diffusion_model.blocks.0.self_attn.q.lora_down.weight': down,
            'diffusion_model.blocks.0.self_attn.q.lora_up.weight': up,
            'diffusion_model.blocks.0.self_attn.q.diff_b': torch.ones(3),
            'diffusion_model.blocks.0.norm3.diff': torch.full((3,), 2.),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'adapter.safetensors'
            save_file(data, str(path))
            self.assertEqual(apply_lightx2v_weights(model, path), 3)
        actual = model.state_dict()
        torch.testing.assert_close(actual['blocks.0.self_attn.to_q.weight'], original['blocks.0.self_attn.to_q.weight'] + up @ down)
        torch.testing.assert_close(actual['blocks.0.self_attn.to_q.bias'], original['blocks.0.self_attn.to_q.bias'] + 1)
        torch.testing.assert_close(actual['blocks.0.norm3.weight'], original['blocks.0.norm3.weight'] + 2)

    def test_rejects_incomplete_and_mismatched_pairs(self):
        key = 'diffusion_model.blocks.0.self_attn.q.lora_down.weight'
        with self.assertRaisesRegex(ValueError, '쌍 누락'):
            plan_lightx2v_weights({key: (1, 2)}, {'blocks.0.self_attn.to_q.weight': (3, 2)})
        with self.assertRaisesRegex(ValueError, '크기 불일치'):
            plan_lightx2v_weights({key: (1, 2), key.replace('down', 'up'): (4, 1)}, {'blocks.0.self_attn.to_q.weight': (3, 2)})

    def test_asset_integrity_and_management_route(self):
        import hashlib
        from unittest.mock import patch
        from generators.wan_animate2 import lightx2v_assets as assets
        from workflow.common.management_gateway import resolve_management_command
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'adapter.safetensors'
            path.write_bytes(b'known content')
            with patch.object(assets, 'PATH', path), patch.object(assets, 'SIZE', 13), patch.object(assets, 'SHA256', hashlib.sha256(b'known content').hexdigest()):
                self.assertTrue(assets.inspect_lightx2v())
                path.write_bytes(b'wrong content')
                self.assertFalse(assets.inspect_lightx2v())
        self.assertEqual(resolve_management_command('wan22-animate2-lightx2v', 'prepare', {'action':'prepare'}), ('POST', '/wan22-animate2-lightx2v/jobs'))
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-animate2-lightx2v', 'prepare', {'action':'prepare', 'extra':True})

    def test_only_selected_lora_requires_adapter(self):
        from unittest.mock import patch
        from workflow.domains.wan_animate2.generation import AnimateTwoGenerationManager
        manager = AnimateTwoGenerationManager()
        with patch.object(manager, 'current_assets_validator'), patch('generators.wan_animate2.lightx2v_assets.validate_lightx2v', side_effect=ValueError('missing')) as validate:
            manager.validate_generation_runtime({'lora_mode':'none'})
            manager.validate_generation_runtime({})
            validate.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'missing'):
                manager.validate_generation_runtime({'lora_mode':'lightx2v'})

    def test_missing_adapter_fails_before_loading_pipeline(self):
        from unittest.mock import patch
        from generators.wan_animate2.worker import execute_animate_inference
        with patch('generators.wan_animate2.lightx2v_assets.validate_lightx2v', side_effect=ValueError('missing')):
            with self.assertRaisesRegex(ValueError, 'missing'):
                execute_animate_inference(None,None,{'lora_mode':'lightx2v'},None)

    def test_loading_rejects_silent_cpu_fallback(self):
        from types import SimpleNamespace
        from generators.wan_animate2.worker import load_animate_gpu_components
        class Component:
            def __init__(self, device): self.device = device
            def parameters(self): return [SimpleNamespace(device=SimpleNamespace(type=self.device))]
        class Pipeline:
            def __init__(self, bad=None): self.calls=[]; self.bad=bad
            def load_components(self, names, **kwargs):
                self.calls.append((names,kwargs))
                for name in names:
                    setattr(self,name,Component('cpu' if name==self.bad else 'cuda'))
        pipeline = Pipeline()
        load_animate_gpu_components(pipeline,{'dtype':'bf16'})
        self.assertEqual([names for names,_ in pipeline.calls], [['transformer'],['text_encoder'],['image_encoder'],['vae'],['tokenizer','scheduler']])
        self.assertTrue(all(kwargs.get('device_map') == 'cuda' for _,kwargs in pipeline.calls[:4]))
        with self.assertRaisesRegex(RuntimeError,'GPU 적재 실패'):
            load_animate_gpu_components(Pipeline('text_encoder'),{})


if __name__ == '__main__':
    unittest.main()
