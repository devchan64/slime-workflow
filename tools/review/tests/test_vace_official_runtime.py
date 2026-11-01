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

    def test_rotary_chunks_match_official_equation(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:
            self.skipTest('추론 환경 torch 필요')
        import torch
        from generators.wan_vace.rotary_memory import apply_chunked_rotary
        for current_input_dtype in (torch.float32,torch.bfloat16,torch.float16):
            current_input_tensor = torch.randn(2,1237,4,128,dtype=current_input_dtype)
            current_grid_sizes = torch.tensor([[3,20,20],[2,20,20]])
            current_frequency_tensor = torch.polar(torch.ones(1024,64,dtype=torch.float64),torch.randn(1024,64,dtype=torch.float64))
            current_frequency_parts = current_frequency_tensor.split([22,21,21],dim=1)
            current_expected_rows = []
            for current_batch_index,(current_time_count,current_height_count,current_width_count) in enumerate(current_grid_sizes.tolist()):
                current_token_count = current_time_count*current_height_count*current_width_count
                current_full_frequencies = torch.cat([
                    current_frequency_parts[0][:current_time_count].view(current_time_count,1,1,-1).expand(current_time_count,current_height_count,current_width_count,-1),
                    current_frequency_parts[1][:current_height_count].view(1,current_height_count,1,-1).expand(current_time_count,current_height_count,current_width_count,-1),
                    current_frequency_parts[2][:current_width_count].view(1,1,current_width_count,-1).expand(current_time_count,current_height_count,current_width_count,-1)],dim=-1).reshape(current_token_count,1,-1)
                current_complex_tensor = torch.view_as_complex(current_input_tensor[current_batch_index,:current_token_count].float().reshape(current_token_count,4,-1,2))
                current_rotated_tensor = torch.view_as_real(current_complex_tensor*current_full_frequencies).flatten(2)
                current_expected_rows.append(torch.cat([current_rotated_tensor,current_input_tensor[current_batch_index,current_token_count:]]))
            self.assertTrue(torch.equal(torch.stack(current_expected_rows).to(current_input_dtype),apply_chunked_rotary(current_input_tensor,current_grid_sizes,current_frequency_tensor)))

    def test_feedforward_chunks_preserve_tokens(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:
            self.skipTest('추론 환경 torch 필요')
        import torch
        from generators.wan_vace.rotary_memory import ChunkedFeedForward
        current_original_module = torch.nn.Sequential(torch.nn.Linear(16,32),torch.nn.GELU(),torch.nn.Linear(32,16)).eval()
        current_input_tensor = torch.randn(2,2051,16)
        with torch.no_grad():
            torch.testing.assert_close(ChunkedFeedForward(current_original_module)(current_input_tensor),current_original_module(current_input_tensor),rtol=1e-5,atol=1e-6)

    def test_residual_chunks_preserve_precision_and_broadcast(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:
            self.skipTest('추론 환경 torch 필요')
        import torch
        from generators.wan_vace.residual_memory import add_chunked_residual
        for current_input_dtype in (torch.float32,torch.bfloat16,torch.float16):
            current_base_tensor = torch.randn(2,2051,16,dtype=current_input_dtype)
            current_delta_tensor = torch.randn_like(current_base_tensor)
            for current_scale_shape in ((2,1,16),(2,2051,16)):
                current_scale_tensor = torch.randn(current_scale_shape,dtype=torch.float32)
                self.assertTrue(torch.equal(current_base_tensor+current_delta_tensor*current_scale_tensor,add_chunked_residual(current_base_tensor,current_delta_tensor,current_scale_tensor)))
            self.assertTrue(torch.equal(current_base_tensor+current_delta_tensor,add_chunked_residual(current_base_tensor,current_delta_tensor)))
