import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from generators.minimax_h3 import assets


class MinimaxEncoderBackupPrepareTest(unittest.TestCase):
    def test_status_rejects_symlink_and_invalid_verification_receipt(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = root/'encoder.safetensors'
            target.write_bytes(b'encoder')
            records = [(root/'other', 0, ''), (target, 7, hashlib.sha256(b'encoder').hexdigest())]
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'current_files', return_value=records):
                assets._write_int8_verification(target, target.stat(), records[1][2])
                receipt = assets._int8_record_path()
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'verified')
                receipt.write_text('{invalid')
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'unverified')
                receipt.unlink()
                receipt.symlink_to(target)
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'unverified')

    def test_prepare_restores_real_snapshot_and_records_verification(self):
        import json
        from workflow.common.model_backup_sync import sync_snapshot
        from workflow.common import model_backup_restore
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source, backup = root/'.model', root/'backup'
            old_root = source/'minimax-h3-i2v'
            old = old_root/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
            old.parent.mkdir(parents=True)
            backup.mkdir()
            old.write_bytes(b'encoder')
            sync_snapshot('minimax-h3-i2v', 'a'*32, roots=(source, backup, None))
            old.rename(root/'preserved-original')
            config = root/'backup.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            records = [(root/'other', 0, ''), (old, 7, hashlib.sha256(b'encoder').hexdigest())]
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'OLD', old_root), \
                 patch.object(assets, 'FILES', records), patch.object(model_backup_restore, 'CONFIG_PATH', config), \
                 patch('workflow.common.model_download_records.track_model_download'):
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'missing')
                assets.prepare_int8_encoder_from_backup()
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'verified')
            target = source/'qwen3vl-32b-minimax-h3-int8-convrot'/old.name
            self.assertEqual(target.read_bytes(), b'encoder')
            self.assertEqual((root/'preserved-original').read_bytes(), b'encoder')

    def test_corrupt_snapshot_fails_without_publishing_or_receipt(self):
        import json
        from workflow.common.model_backup_sync import sync_snapshot
        from workflow.common import model_backup_restore
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source, backup = root/'.model', root/'backup'
            old_root = source/'minimax-h3-i2v'
            old = old_root/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
            old.parent.mkdir(parents=True)
            backup.mkdir()
            old.write_bytes(b'encoder')
            sync_snapshot('minimax-h3-i2v', 'b'*32, roots=(source, backup, None))
            old.rename(root/'preserved-original')
            snapshot = backup/'.model-backup-snapshots/minimax-h3-i2v'/('b'*32)/'text_encoders'/old.name
            snapshot.write_bytes(b'invalid')
            config = root/'backup.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            records = [(root/'other', 0, ''), (old, 7, hashlib.sha256(b'encoder').hexdigest())]
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'OLD', old_root), \
                 patch.object(assets, 'FILES', records), patch.object(model_backup_restore, 'CONFIG_PATH', config), \
                 patch('workflow.common.model_download_records.track_model_download'):
                with self.assertRaisesRegex(ValueError, '백업 인코더'):
                    assets.prepare_int8_encoder_from_backup()
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'missing')
                self.assertFalse(assets._int8_record_path().exists())
            self.assertEqual(snapshot.read_bytes(), b'invalid')
            self.assertEqual((root/'preserved-original').read_bytes(), b'encoder')

    def test_status_reads_receipt_without_hashing_and_invalidates_change(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = root/'encoder.safetensors'
            target.write_bytes(b'encoder')
            records = [(root/'other', 0, ''), (target, 7, hashlib.sha256(b'encoder').hexdigest())]
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'current_files', return_value=records):
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'unverified')
                assets._write_int8_verification(target, target.stat(), records[1][2])
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'verified')
                target.write_bytes(b'invalid')
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'unverified')
                target.unlink()
                self.assertEqual(assets.inspect_int8_encoder_nonblocking(), 'missing')

    def test_gateway_starts_only_for_missing_file_and_refuses_invalid(self):
        import json
        from unittest.mock import Mock
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.tests.test_management_gateway import GatewayContractTest
        gateway = ManagementCommandGateway({'minimax-h3-int8-encoder': Mock()})
        for verification, should_start in (('missing', True), ('unverified', True), ('invalid', False), ('verified', False)):
            with self.subTest(verification=verification):
                handler = GatewayContractTest().create_request_handler('/management/command',
                    {'service': 'minimax-h3-int8-encoder', 'command': 'prepare', 'payload': {'action': 'prepare'}})
                with patch('generators.minimax_h3.assets.inspect_int8_encoder_nonblocking', return_value=verification), \
                     patch('workflow.common.model_prepare_process.inspect_registered_preparation_strict', return_value='idle'), \
                     patch('workflow.common.model_prepare_process.start_registered_preparation', return_value={'preparation_status': 'running'}) as start:
                    self.assertTrue(gateway.handle(handler))
                self.assertEqual(start.called, should_start)
                response = json.loads(handler.wfile.getvalue())
                self.assertEqual(response['verification_status'], verification)
                self.assertEqual(response['ready'], verification == 'verified')

    def test_gateway_does_not_start_duplicate_running_preparation(self):
        import json
        from unittest.mock import Mock
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.tests.test_management_gateway import GatewayContractTest
        gateway = ManagementCommandGateway({'minimax-h3-int8-encoder': Mock()})
        handler = GatewayContractTest().create_request_handler('/management/command',
            {'service': 'minimax-h3-int8-encoder', 'command': 'prepare', 'payload': {'action': 'prepare'}})
        with patch('generators.minimax_h3.assets.inspect_int8_encoder_nonblocking', return_value='missing'), \
             patch('workflow.common.model_prepare_process.inspect_registered_preparation_strict', return_value='running'), \
             patch('workflow.common.model_prepare_process.start_registered_preparation') as start:
            self.assertTrue(gateway.handle(handler))
        start.assert_not_called()
        self.assertEqual(json.loads(handler.wfile.getvalue())['preparation_status'], 'running')

    def test_missing_encoder_restores_to_new_path_and_verifies(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            old_root = root/'.model/minimax-h3-i2v'
            old_root.mkdir(parents=True)
            old = old_root/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
            records = [(root/'other', 0, ''), (old, 7, hashlib.sha256(b'encoder').hexdigest())]
            expected = root/'.model/qwen3vl-32b-minimax-h3-int8-convrot'/old.name
            def restore(target, digest, size, **kwargs):
                self.assertEqual((target, digest, size), (expected, records[1][2], 7))
                target.write_bytes(b'encoder')
                return True
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'OLD', old_root), \
                 patch.object(assets, 'FILES', records), \
                 patch('workflow.common.model_download_records.track_model_download'), \
                 patch('workflow.common.model_backup_restore.restore_verified_backup', side_effect=restore):
                assets.prepare_int8_encoder_from_backup()
            self.assertEqual(expected.read_bytes(), b'encoder')

    def test_existing_mismatched_file_is_never_overwritten(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            old_root = root/'.model/minimax-h3-i2v'
            old = old_root/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
            old.parent.mkdir(parents=True)
            old.write_bytes(b'invalid')
            records = [(root/'other', 0, ''), (old, 7, hashlib.sha256(b'encoder').hexdigest())]
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'OLD', old_root), \
                 patch.object(assets, 'FILES', records), \
                 patch('workflow.common.model_download_records.track_model_download'), \
                 patch('workflow.common.model_backup_restore.restore_verified_backup') as restore:
                with self.assertRaises(ValueError):
                    assets.prepare_int8_encoder_from_backup()
                restore.assert_not_called()
            self.assertEqual(old.read_bytes(), b'invalid')
