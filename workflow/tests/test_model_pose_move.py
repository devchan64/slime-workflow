import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workflow.common.model_pose_move import move_pose_component


class PoseMoveTest(unittest.TestCase):
    def _project(self, root):
        source = root/'.model/wan22-fun-pose'
        source.mkdir(parents=True)
        hashes = {}
        for name in ('yolox_l.onnx', 'yolox_l.cuda.onnx'):
            (source/name).write_bytes(name.encode())
            hashes[name] = hashlib.sha256(name.encode()).hexdigest()
        (source/'prepared.json').write_text(json.dumps({'revision': 'revision', 'files': hashes}))
        queue = root/'.tmp/gpu-queue'
        (queue/'active').mkdir(parents=True)
        (queue/'execution.lock').touch()
        backup = root/'.local/hermes/model-backup-verification'
        backup.mkdir(parents=True)
        (backup/'worker.lock').touch()
        return source

    def test_move_records_hashes_and_independent_preparation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._project(root)
            target = root/'.model/yolox-l'
            result = move_pose_component(root, 'yolox-l', root/'journal.json', lambda: None)
            self.assertEqual(set(result['files']), {'yolox_l.onnx', 'yolox_l.cuda.onnx'})
            self.assertFalse((source/'yolox_l.onnx').exists())
            self.assertEqual((target/'yolox_l.onnx').read_bytes(), b'yolox_l.onnx')
            self.assertEqual(json.loads((target/'prepared.json').read_text())['files']['yolox_l.onnx'], result['files']['yolox_l.onnx']['sha256'])
            self.assertTrue((source/'prepared.json').is_file())

    def test_consumer_failure_restores_original_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._project(root)
            def reject():
                raise ValueError('consumer failure')
            with self.assertRaisesRegex(ValueError, 'consumer failure'):
                move_pose_component(root, 'yolox-l', root/'journal.json', reject)
            self.assertEqual((source/'yolox_l.onnx').read_bytes(), b'yolox_l.onnx')
            self.assertFalse((root/'.model/yolox-l').exists())
            self.assertTrue((root/'journal.json').is_file())

    def test_reservation_or_hash_mismatch_prevents_move(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._project(root)
            reservation = root/'.tmp/gpu-queue/active/job'
            reservation.touch()
            with self.assertRaises(ValueError):
                move_pose_component(root, 'yolox-l', root/'journal.json', lambda: None)
            reservation.unlink()
            (source/'yolox_l.onnx').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                move_pose_component(root, 'yolox-l', root/'journal.json', lambda: None)
            self.assertFalse((root/'journal.json').exists())
