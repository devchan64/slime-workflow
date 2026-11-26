import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from generators.wan_fun import prepare_pose


class PoseBackupRecoveryTest(unittest.TestCase):
    def test_prepare_reuses_verified_sources_without_hub(self):
        import os, sys, types
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ('yolox_l.onnx', 'dw-ll_ucoco_384.onnx')
            paths = {}
            for name, folder in zip(names, ('yolox-l', 'dwpose-ll-ucoco-384')):
                directory = root/folder
                directory.mkdir()
                target = directory/name
                target.write_bytes(name.encode())
                (directory/'prepared.json').write_text(json.dumps({'revision': prepare_pose.FUN_POSE_MODEL_REVISION,
                    'files': {name: hashlib.sha256(name.encode()).hexdigest()}}))
                paths[name] = target
                paths[Path(name).with_suffix('.cuda.onnx').name] = target.with_suffix('.cuda.onnx')
            graph = types.SimpleNamespace(input=[types.SimpleNamespace(name='image')])
            model = types.SimpleNamespace(graph=graph)
            fake_onnx = types.ModuleType('onnx')
            fake_onnx.load = Mock(return_value=model)
            fake_onnx.save = lambda value, path: Path(path).write_bytes(b'converted')
            fake_onnx.checker = types.SimpleNamespace(check_model=lambda value: None)
            fake_onnxsim = types.ModuleType('onnxsim')
            fake_onnxsim.simplify = lambda value, **kwargs: (value, True)
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(sys.modules, {'onnx': fake_onnx, 'onnxsim': fake_onnxsim}), \
                     patch.object(prepare_pose, 'pose_model_path', side_effect=lambda name: paths[name]), \
                     patch('workflow.common.model_huggingface_download.tracked_hf_hub_download') as download:
                    prepare_pose.prepare_fun_pose_models()
                download.assert_not_called()
                self.assertEqual(paths['yolox_l.cuda.onnx'].read_bytes(), b'converted')
                self.assertEqual(paths['dw-ll_ucoco_384.cuda.onnx'].read_bytes(), b'converted')
            finally:
                os.chdir(previous)

    def test_existing_source_is_reused_only_when_local_record_matches(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root/'yolox_l.onnx'
            target.write_bytes(b'weight')
            (root/'prepared.json').write_text(json.dumps({'revision': prepare_pose.FUN_POSE_MODEL_REVISION,
                'files': {target.name: hashlib.sha256(b'weight').hexdigest()}}))
            self.assertTrue(prepare_pose.prepared_pose_source_matches(target))
            target.write_bytes(b'changed')
            self.assertFalse(prepare_pose.prepared_pose_source_matches(target))

    def test_missing_source_uses_local_declaration_and_backup(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root/'yolox-l'/'yolox_l.onnx'
            target.parent.mkdir()
            digest = hashlib.sha256(b'weight').hexdigest()
            (target.parent/'prepared.json').write_text(json.dumps({'revision': prepare_pose.FUN_POSE_MODEL_REVISION, 'files': {target.name: digest}}))
            with patch('workflow.common.model_backup_restore.restore_verified_backup', return_value=True) as restore:
                self.assertTrue(prepare_pose.restore_pose_source_from_backup(target))
                restore.assert_called_once_with(target, digest)

    def test_bad_declaration_or_existing_target_never_triggers_restore(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root/'yolox_l.onnx'
            record = root/'prepared.json'
            record.write_text(json.dumps({'revision': prepare_pose.FUN_POSE_MODEL_REVISION, 'files': {target.name: 'bad'}}))
            with patch('workflow.common.model_backup_restore.restore_verified_backup') as restore:
                self.assertFalse(prepare_pose.restore_pose_source_from_backup(target))
                target.write_bytes(b'existing')
                self.assertFalse(prepare_pose.restore_pose_source_from_backup(target))
                restore.assert_not_called()
