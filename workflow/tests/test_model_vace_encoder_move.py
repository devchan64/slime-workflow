import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from workflow.common.model_vace_encoder_move import move_vace_encoder


class VaceEncoderMoveTest(unittest.TestCase):
    def setup_project(self, root):
        source = root/'.model/wan22-vace/models_t5_umt5-xxl-enc-bf16.pth'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'encoder')
        queue = root/'.tmp/gpu-queue'
        (queue/'active').mkdir(parents=True)
        (queue/'execution.lock').touch()
        backup = root/'.local/hermes/model-backup-verification'
        backup.mkdir(parents=True)
        (backup/'worker.lock').touch()
        return source

    def test_move_and_validation_failure_rollback(self):
        for reject in (False, True):
            with self.subTest(reject=reject), TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = self.setup_project(root)
                target = root/'.model/umt5-xxl-encoder-bf16'/source.name
                def validate():
                    if reject:
                        raise ValueError('consumer unavailable')
                args = {'expected_size': 7, 'expected_sha256': hashlib.sha256(b'encoder').hexdigest()}
                if reject:
                    with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                        move_vace_encoder(root, root/'journal.json', validate, **args)
                    self.assertEqual(source.read_bytes(), b'encoder')
                    self.assertFalse(target.exists())
                else:
                    result = move_vace_encoder(root, root/'journal.json', validate, **args)
                    self.assertEqual(target.read_bytes(), b'encoder')
                    self.assertFalse(source.exists())
                    self.assertEqual(result['sha256'], args['expected_sha256'])

    def test_active_reservation_prevents_move(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.setup_project(root)
            (root/'.tmp/gpu-queue/active/job').touch()
            with self.assertRaises(ValueError):
                move_vace_encoder(root, root/'journal.json', lambda: None, expected_size=7, expected_sha256=hashlib.sha256(b'encoder').hexdigest())
            self.assertTrue(source.exists())
            self.assertFalse((root/'journal.json').exists())
