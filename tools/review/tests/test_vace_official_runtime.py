"""공식 실행 소스와 양자화 고정 계약을 검사한다."""
import unittest
from pathlib import Path
import yaml


class VaceOfficialRuntimeTest(unittest.TestCase):
    def test_branch_offload_preserves_non_transfer_syntax(self):
        import ast
        from generators.wan_vace.activation_offload import VACE_BRANCH_OFFLOAD_REPLACEMENTS
        current_original_text = Path('.local/videox-fun-vace-pinned/videox_fun/models/wan_transformer3d_vace.py').read_text()
        current_execution_text = current_original_text
        for current_source_text, current_target_text in VACE_BRANCH_OFFLOAD_REPLACEMENTS:
            self.assertEqual(current_execution_text.count(current_source_text), 1)
            current_execution_text = current_execution_text.replace(current_source_text, current_target_text)
        class RemoveDeviceTransfers(ast.NodeTransformer):
            def visit_Call(self, current_ast_node):
                self.generic_visit(current_ast_node)
                if isinstance(current_ast_node.func, ast.Attribute) and current_ast_node.func.attr == 'to':
                    return current_ast_node.func.value
                return current_ast_node
            def visit_Assign(self, current_ast_node):
                self.generic_visit(current_ast_node)
                if len(current_ast_node.targets) == 1 and isinstance(current_ast_node.targets[0], ast.Name) and isinstance(current_ast_node.value, ast.Name) and current_ast_node.targets[0].id == current_ast_node.value.id:
                    return None
                return current_ast_node
        self.assertEqual(ast.dump(RemoveDeviceTransfers().visit(ast.parse(current_original_text))), ast.dump(RemoveDeviceTransfers().visit(ast.parse(current_execution_text))))

    def test_input_offload_only_inserts_cpu_transfers(self):
        import ast
        from generators.wan_vace.activation_offload import VACE_PIPELINE_OFFLOAD_INSERT, VACE_PIPELINE_OFFLOAD_ANCHOR, VACE_PIPELINE_RELATIVE_PATH
        current_source_text = (Path('.local/videox-fun-vace-pinned') / VACE_PIPELINE_RELATIVE_PATH).read_text()
        self.assertEqual(current_source_text.count(VACE_PIPELINE_OFFLOAD_ANCHOR), 1)
        current_execution_text = current_source_text.replace(VACE_PIPELINE_OFFLOAD_ANCHOR, VACE_PIPELINE_OFFLOAD_ANCHOR + VACE_PIPELINE_OFFLOAD_INSERT)
        ast.parse(current_execution_text)
        self.assertEqual(current_execution_text.replace(VACE_PIPELINE_OFFLOAD_INSERT, ''), current_source_text)
        import textwrap
        for current_ast_node in ast.walk(ast.parse(textwrap.dedent(VACE_PIPELINE_OFFLOAD_INSERT))):
            if isinstance(current_ast_node, ast.Call):
                self.assertIsInstance(current_ast_node.func, ast.Attribute)
                self.assertEqual(current_ast_node.func.attr, 'to')
                self.assertEqual([current_argument_node.value for current_argument_node in current_ast_node.args], ['cpu'])

    def test_non_block_hooks_preserve_output_and_device_owner(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from generators.wan_vace.cpu_offload import install_expert_block_offload, VACE_TRANSIENT_MODULE_NAMES
        current_module_names = VACE_TRANSIENT_MODULE_NAMES | {'patch_embedding'}
        current_model_object = SimpleNamespace(**{
            current_module_name: Mock() for current_module_name in current_module_names
        })
        current_model_object.blocks = [Mock()]
        current_model_object.vace_blocks = [Mock()]
        install_expert_block_offload(current_model_object)
        current_model_object.patch_embedding.register_forward_pre_hook.assert_not_called()
        current_model_object.patch_embedding.register_forward_hook.assert_not_called()
        current_output_value = object()
        for current_module_object in [
            *current_model_object.blocks, *current_model_object.vace_blocks,
            *(getattr(current_model_object, current_module_name) for current_module_name in VACE_TRANSIENT_MODULE_NAMES),
        ]:
            current_before_hook = current_module_object.register_forward_pre_hook.call_args.args[0]
            current_after_hook = current_module_object.register_forward_hook.call_args.args[0]
            self.assertIsNone(current_before_hook(current_module_object, ()))
            self.assertIsNone(current_after_hook(current_module_object, (), current_output_value))
            self.assertEqual([current_call.args[0] for current_call in current_module_object.to.call_args_list], ['cuda', 'cpu'])

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
