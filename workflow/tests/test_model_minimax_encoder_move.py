import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from workflow.common.model_minimax_encoder_move import move_minimax_int8_encoder, move_minimax_encoder


class MinimaxEncoderMoveTest(unittest.TestCase):
    def test_running_preparation_prevents_move(self):
        from workflow.common.model_prepare_process import hold_registered_preparation_guard
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.project(root)
            with hold_registered_preparation_guard(root, 'minimax-h3-int8-encoder'):
                with self.assertRaisesRegex(ValueError, '준비가 진행 중'):
                    move_minimax_int8_encoder(root, root/'journal.json', lambda: None, expected_size=7,
                                              expected_sha256=hashlib.sha256(b'encoder').hexdigest())
            self.assertEqual(source.read_bytes(), b'encoder')
            self.assertFalse((root/'journal.json').exists())

    def test_nvfp4_move_preserves_int8_and_can_roll_back_on_failure(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            int8 = self.project(root)
            source = int8.parent/'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
            source.write_bytes(b'nvfp4')
            target = root/'.model/qwen3vl-32b-minimax-h3-nvfp4-awq'/source.name
            def reject():
                raise ValueError('검증 실패')
            with self.assertRaisesRegex(ValueError, '검증 실패'):
                move_minimax_encoder(root, root/'journal.json', reject, variant='nvfp4-awq', expected_size=5,
                                     expected_sha256=hashlib.sha256(b'nvfp4').hexdigest())
            self.assertEqual(int8.read_bytes(), b'encoder')
            self.assertEqual(source.read_bytes(), b'nvfp4')
            self.assertFalse(target.exists())

    def project(self, root):
        source = root/'.model/minimax-h3-i2v/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'encoder')
        queue = root/'.tmp/gpu-queue'
        (queue/'active').mkdir(parents=True)
        (queue/'execution.lock').touch()
        backup = root/'.local/hermes/model-backup-verification'
        backup.mkdir(parents=True)
        (backup/'worker.lock').touch()
        return source

    def test_move_or_consumer_failure_rollback(self):
        for reject in (False, True):
            with self.subTest(reject=reject), TemporaryDirectory() as temp:
                root = Path(temp)
                source = self.project(root)
                target = root/'.model/qwen3vl-32b-minimax-h3-int8-convrot'/source.name
                def validate():
                    if reject:
                        raise ValueError('consumer unavailable')
                args = {'expected_size': 7, 'expected_sha256': hashlib.sha256(b'encoder').hexdigest()}
                if reject:
                    with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                        move_minimax_int8_encoder(root, root/'journal.json', validate, **args)
                    self.assertEqual(source.read_bytes(), b'encoder')
                    self.assertFalse(target.exists())
                else:
                    result = move_minimax_int8_encoder(root, root/'journal.json', validate, **args)
                    self.assertEqual(target.read_bytes(), b'encoder')
                    self.assertFalse(source.exists())
                    self.assertEqual(result['sha256'], args['expected_sha256'])

    def test_reservation_prevents_move(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.project(root)
            (root/'.tmp/gpu-queue/active/job').touch()
            with self.assertRaises(ValueError):
                move_minimax_int8_encoder(root, root/'journal.json', lambda: None, expected_size=7, expected_sha256=hashlib.sha256(b'encoder').hexdigest())
            self.assertTrue(source.exists())
            self.assertFalse((root/'journal.json').exists())

    def test_destination_conflict_and_wrong_hash_preserve_source(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.project(root)
            target = root/'.model/qwen3vl-32b-minimax-h3-int8-convrot'
            target.mkdir()
            args = {'expected_size': 7, 'expected_sha256': hashlib.sha256(b'encoder').hexdigest()}
            with self.assertRaisesRegex(ValueError, '대상 경로'):
                move_minimax_int8_encoder(root, root/'journal.json', lambda: None, **args)
            target.rmdir()
            args['expected_sha256'] = hashlib.sha256(b'wrong').hexdigest()
            with self.assertRaisesRegex(ValueError, '해시'):
                move_minimax_int8_encoder(root, root/'journal.json', lambda: None, **args)
            self.assertEqual(source.read_bytes(), b'encoder')
            self.assertFalse((root/'journal.json').exists())

    def test_backup_worker_lock_prevents_move(self):
        import fcntl
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.project(root)
            with (root/'.local/hermes/model-backup-verification/worker.lock').open('r+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    move_minimax_int8_encoder(root, root/'journal.json', lambda: None, expected_size=7,
                                              expected_sha256=hashlib.sha256(b'encoder').hexdigest())
            self.assertEqual(source.read_bytes(), b'encoder')
            self.assertFalse((root/'journal.json').exists())

    def test_replacement_after_hash_stops_before_rename(self):
        from unittest.mock import patch
        from workflow.common import model_minimax_encoder_move as move
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.project(root)
            real_verify = move._verify
            def replace_after_verify(path, size, digest):
                info = real_verify(path, size, digest)
                path.rename(path.with_name('original-preserved'))
                path.write_bytes(b'changed')
                return info
            with patch.object(move, '_verify', side_effect=replace_after_verify):
                with self.assertRaisesRegex(ValueError, '교체'):
                    move_minimax_int8_encoder(root, root/'journal.json', lambda: None, expected_size=7,
                                              expected_sha256=hashlib.sha256(b'encoder').hexdigest())
            self.assertEqual(source.read_bytes(), b'changed')
            self.assertEqual((source.parent/'original-preserved').read_bytes(), b'encoder')
            self.assertFalse((root/'.model/qwen3vl-32b-minimax-h3-int8-convrot').exists())
