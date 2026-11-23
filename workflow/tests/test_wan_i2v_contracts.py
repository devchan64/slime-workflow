import base64
import io
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from generators.wan_i2v.contracts import validate_request
from generators.wan_i2v.worker import apply_adapter
from workflow.domains.wan_i2v.generation import I2VGenerationManager
from workflow.common.gpu_job_queue import GPU_MEMORY_REQUIREMENTS, GPU_EXCLUSIVE_SERVICES, identify_dedicated_gpu_reservation_source
from workflow.common.management_gateway import resolve_management_command


class I2VContractsTest(unittest.TestCase):
    def setUp(self):
        image = io.BytesIO()
        Image.new('RGB', (832, 480)).save(image, format='PNG')
        self.request = dict(action='generate', prompt='one sword slash', negative_prompt='',
                            images=[base64.b64encode(image.getvalue()).decode()], width=832, height=480,
                            frames=21, steps=4, seed=45, flow_shift=5, guidance_scale=1,
                            lora_mode='lightning_kungfu', kungfu_strength=1)

    def test_input_and_lightning_constraints(self):
        self.assertEqual(validate_request(self.request)['tag'], 'wan22-i2v')
        for field, value in [('frames', 20), ('steps', 5), ('guidance_scale', 2),
                             ('kungfu_strength', math.nan), ('images', [])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_request({**self.request, field: value})

    def test_adapter_counts_overlapping_patches_and_rejects_unmatched(self):
        class Model:
            def __init__(self, patches):
                self.patches = patches
        class Utils:
            @staticmethod
            def load_torch_file(*args, **kwargs):
                return {'layer.lora_A.weight': 1, 'layer.lora_B.weight': 1}
        class SD:
            @staticmethod
            def load_lora_for_models(model, *_):
                return Model({'layer': model.patches.get('layer', []) + [1]}), None
        model, count = apply_adapter(Model({'layer': [0]}), Path('test'), 1, SD, Utils)
        self.assertEqual(count, 1)
        self.assertEqual(len(model.patches['layer']), 2)
        with patch.object(SD, 'load_lora_for_models', side_effect=lambda model, *_: (model, None)):
            with self.assertRaises(ValueError):
                apply_adapter(Model({}), Path('test'), 1, SD, Utils)

    def test_queue_registration_and_command(self):
        manager = I2VGenerationManager()
        self.assertEqual(manager.select_generation_service(), 'wan22-i2v')
        self.assertEqual(manager.select_generation_runner(), 'generators/wan_i2v/worker.py')
        self.assertEqual(GPU_MEMORY_REQUIREMENTS['wan22-i2v'], 81920)
        self.assertIn('wan22-i2v', GPU_EXCLUSIVE_SERVICES)
        method, path = resolve_management_command('wan22-i2v', 'generate', self.request)
        self.assertEqual((method, path), ('POST', '/wan22-i2v/jobs'))

    def test_queue_source_is_confined_to_i2v_root(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            valid = Path(root) / '.tmp/test/wan22-i2v/2026-11-23_00-00-00-12345678'
            valid.mkdir(parents=True)
            self.assertEqual(identify_dedicated_gpu_reservation_source(str(valid), 'wan22-i2v', root), 'wan22-i2v')
            self.assertIsNone(identify_dedicated_gpu_reservation_source(str(valid.parent.parent / 'other' / valid.name), 'wan22-i2v', root))

    def test_short_run_does_not_reduce_i2v_memory_reservation(self):
        from workflow.common import gpu_memory_history as memory
        with patch.object(memory, 'load_recent_observations', return_value=[]), patch.object(memory, 'summarize_memory_observations', return_value={'peak_memory_mib': 1000, 'usable_runs': 1, 'retained_runs': 1}):
            estimate = memory.estimate_required_memory('wan22-i2v', 81920, 'worker.py')
        self.assertGreaterEqual(estimate['required_memory_mib'], 81920)

    def test_hermes_video_proposal_and_manager(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal
        from workflow.domains.hermes_agent.video_operations import make_hermes_video_manager
        proposal = 'HERMES_VIDEO_PROPOSAL\n{"service":"wan22-i2v","mode":"first_frame","prompt":"one sword slash"}\nEND_HERMES_VIDEO_PROPOSAL'
        self.assertEqual(parse_hermes_video_proposal(proposal)['service'], 'wan22-i2v')
        self.assertIsInstance(make_hermes_video_manager('wan22-i2v'), I2VGenerationManager)
        with self.assertRaises(ValueError):
            parse_hermes_video_proposal(proposal.replace('first_frame', 'pose_video'))


if __name__ == '__main__':
    unittest.main()
