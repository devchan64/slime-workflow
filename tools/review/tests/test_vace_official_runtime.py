"""공식 실행 소스와 양자화 고정 계약을 검사한다."""
import unittest
from pathlib import Path
import yaml


class VaceOfficialRuntimeTest(unittest.TestCase):
    def test_existing_quantization_revision_is_preserved(self):
        from generators.wan_vace.contracts import VACE_MODEL_REVISION,VACE_SOURCE_REVISION,VACE_MODEL_FILES
        current_manifest_record=yaml.safe_load(Path('generators/wan_vace/config/official-runtime.yaml').read_text())
        self.assertEqual(VACE_MODEL_REVISION,'93b339260b1d819e2c171dd7ca9e66a761d4a84d')
        self.assertEqual(current_manifest_record['source_revision'],VACE_SOURCE_REVISION)
        self.assertIn('Q4_K_M',VACE_MODEL_FILES['high'][0])
        self.assertIn('Q4_K_M',VACE_MODEL_FILES['low'][0])
        self.assertIn('bf16',VACE_MODEL_FILES['encoder'][0])

    def test_official_source_and_tokenizer_are_verified(self):
        import tempfile
        import hashlib
        from unittest.mock import patch
        from generators.wan_vace import official_prepare
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_fixture_root = Path(current_directory_name)
            current_source_path = current_fixture_root/'source.py'
            current_tokenizer_path = current_fixture_root/'tokenizer.json'
            current_source_path.write_text('source')
            current_tokenizer_path.write_text('tokenizer')
            current_manifest_path = current_fixture_root/'manifest.yaml'
            current_manifest_path.write_text(yaml.safe_dump({
                'source_files': {'source.py': hashlib.sha256(b'source').hexdigest()},
                'tokenizer_files': {'tokenizer.json': hashlib.sha256(b'tokenizer').hexdigest()},
            }))
            with patch.object(official_prepare,'VACE_OFFICIAL_MANIFEST_PATH',current_manifest_path), patch.object(official_prepare,'VACE_OFFICIAL_INSTALL_ROOT',current_fixture_root), patch.object(official_prepare,'VACE_OFFICIAL_TOKENIZER_ROOT',current_fixture_root):
                official_prepare.verify_official_runtime()
                current_source_path.write_text('changed')
                with self.assertRaisesRegex(ValueError,'공식 소스'):
                    official_prepare.verify_official_runtime()

    def test_request_shift_matches_official_euler_schedule(self):
        import importlib.util
        if importlib.util.find_spec('diffusers') is None:
            self.skipTest('추론 환경 diffusers 필요')
        import torch
        from diffusers import FlowMatchEulerDiscreteScheduler
        from generators.wan_vace.sampling import build_vace_scheduler
        current_source_config = yaml.safe_load(Path('.local/videox-fun-vace-pinned/config/wan2.2/wan_civitai_t2v.yaml').read_text())
        current_scheduler_config = dict(current_source_config['scheduler_kwargs'])
        current_scheduler_config.pop('scheduler_subpath')
        current_official_scheduler = FlowMatchEulerDiscreteScheduler(**current_scheduler_config)
        current_default_scheduler = build_vace_scheduler(12)
        current_changed_scheduler = build_vace_scheduler(8)
        for current_scheduler_object in (current_official_scheduler,current_default_scheduler,current_changed_scheduler):
            current_scheduler_object.set_timesteps(20, device='cpu', mu=1)
        self.assertTrue(torch.equal(current_official_scheduler.sigmas,current_default_scheduler.sigmas))
        self.assertFalse(torch.equal(current_changed_scheduler.sigmas,current_default_scheduler.sigmas))
        self.assertEqual(int((current_default_scheduler.timesteps >= 875).sum()),13)

    def test_runtime_preserves_official_forward(self):
        current_runtime_source = Path('generators/wan_vace/official_runtime.py').read_text()
        for current_forbidden_text in ('rope_apply =', 'install_chunked_feedforward', 'install_residual_memory', 'install_prediction_capture', 'decode_step_previews'):
            self.assertNotIn(current_forbidden_text,current_runtime_source)
        current_offload_source = Path('generators/wan_vace/cpu_offload.py').read_text()
        self.assertNotIn('forward =',current_offload_source)
        self.assertNotIn('exec(',current_offload_source)
        self.assertIn("register_forward_pre_hook",current_offload_source)
        self.assertIn("register_forward_hook",current_offload_source)
