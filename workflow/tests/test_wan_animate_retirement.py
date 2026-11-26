"""Animate 폐기와 활성 생성기의 공유 자원 연결을 검사한다."""
import unittest
from pathlib import Path
from workflow.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS
from workflow.common.management_catalog import NATIVE_MANAGEMENT_APPLICATIONS

class WanAnimateRetirementTests(unittest.TestCase):
    def test_shared_validation_accepts_separated_pose_files_and_rejects_conflict(self):
        import hashlib, json, tempfile
        from unittest.mock import patch
        from generators.kimodo import dwpose_runtime
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root/'wan22-fun-pose'
            legacy.mkdir()
            hashes = {}
            for name, folder in (('yolox_l.cuda.onnx', 'yolox-l'),
                                 ('dw-ll_ucoco_384.cuda.onnx', 'dwpose-ll-ucoco-384')):
                path = root/folder/name
                path.parent.mkdir()
                path.write_bytes(name.encode())
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            (legacy/'prepared.json').write_text(json.dumps({'revision': dwpose_runtime.FUN_POSE_MODEL_REVISION, 'files': hashes}))
            with patch.object(dwpose_runtime, 'FUN_POSE_MODEL_DIRECTORY', legacy):
                dwpose_runtime.validate_fun_pose_assets()
                for name, folder in (('yolox_l.cuda.onnx', 'yolox-l'),
                                     ('dw-ll_ucoco_384.cuda.onnx', 'dwpose-ll-ucoco-384')):
                    (root/folder/'prepared.json').write_text(json.dumps({'revision': dwpose_runtime.FUN_POSE_MODEL_REVISION, 'files': {name: hashes[name]}}))
                dwpose_runtime.validate_fun_pose_assets()
                (root/'yolox-l'/'prepared.json').write_text(json.dumps({'revision': dwpose_runtime.FUN_POSE_MODEL_REVISION, 'files': {'yolox_l.cuda.onnx': 'bad'}}))
                with self.assertRaisesRegex(ValueError, '해시 불일치'):
                    dwpose_runtime.validate_fun_pose_assets()
                (legacy/'yolox_l.cuda.onnx').write_bytes(b'duplicate')
                with self.assertRaises(ValueError):
                    dwpose_runtime.validate_fun_pose_assets()

    def test_retired_service_and_ui(self):
        self.assertNotIn('wan22-animate', MANAGEMENT_SERVICE_COMMANDS)
        self.assertNotIn('wan22-animate-generator', NATIVE_MANAGEMENT_APPLICATIONS)
        for current_command_name in ('generate','resume','history','model-status'):
            with self.assertRaisesRegex(ValueError,'폐기'):
                resolve_management_command('wan22-animate',current_command_name,{})
        self.assertFalse(Path('generators/wan_animate').exists())
        from workflow.common.management_catalog import REACT_REVIEW_PATHS
        self.assertNotIn('wan22-animate-generator', REACT_REVIEW_PATHS)

    def test_shared_validation_preserved(self):
        from generators.common.onnx_model_validation import validate_external_tensor_files
        self.assertTrue(callable(validate_external_tensor_files))
        import hashlib
        import json
        import tempfile
        from unittest.mock import patch
        from generators.kimodo import dwpose_runtime
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_model_directory = Path(temporary_directory_name)
            current_model_hashes = {}
            for current_model_name in dwpose_runtime.FUN_POSE_MODEL_NAMES:
                current_model_path = (current_model_directory / current_model_name).with_suffix('.cuda.onnx')
                current_model_path.write_bytes(current_model_name.encode())
                current_model_hashes[current_model_path.name] = hashlib.sha256(current_model_path.read_bytes()).hexdigest()
            (current_model_directory / 'prepared.json').write_text(json.dumps({'revision': dwpose_runtime.FUN_POSE_MODEL_REVISION, 'files': current_model_hashes}))
            with patch.object(dwpose_runtime, 'FUN_POSE_MODEL_DIRECTORY', current_model_directory):
                dwpose_runtime.validate_fun_pose_assets()
                current_model_path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, '해시 불일치'):
                    dwpose_runtime.validate_fun_pose_assets()
        from generators.wan_vace.contracts import VACE_MODEL_FILES
        self.assertIn('wan_2.1_vae.safetensors',VACE_MODEL_FILES['vae'][0])
