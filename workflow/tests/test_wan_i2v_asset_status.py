import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from generators.wan_i2v import assets


class WanI2VAssetStatusTests(unittest.TestCase):
    def test_retained_kungfu_path_tracks_move_and_rejects_conflicts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/'wan22-i2v'/'kungfu'
            new = root/'wan22-i2v-kungfu'
            old.mkdir(parents=True)
            with patch.object(assets, 'DIRECTORY', root/'wan22-i2v'):
                self.assertEqual(assets.asset_path('kungfu/high.safetensors'), old/'high.safetensors')
                old.rename(new)
                self.assertEqual(assets.asset_path('kungfu/high.safetensors'), new/'high.safetensors')
                old.mkdir()
                with self.assertRaises(ValueError):
                    assets.asset_path('kungfu/high.safetensors')

    def test_lightning_path_tracks_move_and_rejects_conflicts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/'wan22-i2v'/'lightning'
            new = root/'wan22-lightning-i2v-seko-v1'
            old.mkdir(parents=True)
            with patch.object(assets, 'DIRECTORY', root/'wan22-i2v'):
                self.assertEqual(assets.asset_path('lightning/high.safetensors'), old/'high.safetensors')
                old.rename(new)
                self.assertEqual(assets.asset_path('lightning/high.safetensors'), new/'high.safetensors')
                old.mkdir()
                with self.assertRaises(ValueError):
                    assets.asset_path('lightning/high.safetensors')
                self.assertIsNone(assets._asset_signature())

    def test_gateway_does_not_start_prepare_while_hash_verification_runs(self):
        from unittest.mock import Mock
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.tests.test_management_gateway import GatewayContractTest
        gateway = ManagementCommandGateway({'wan22-i2v-assets': Mock()})
        handler = GatewayContractTest().create_request_handler('/management/command',
            {'service': 'wan22-i2v-assets', 'command': 'prepare', 'payload': {'action': 'prepare'}})
        with patch.object(assets, 'inspect_assets_nonblocking', return_value='verifying'), \
             patch('workflow.common.model_prepare_process.inspect_registered_preparation_strict', return_value='idle'), \
             patch('workflow.common.model_prepare_process.start_registered_preparation') as start:
            self.assertTrue(gateway.handle(handler))
        start.assert_not_called()
        response = json.loads(handler.wfile.getvalue())
        self.assertFalse(response['ready'])
        self.assertFalse(response['can_prepare'])
        self.assertEqual(response['verification_status'], 'verifying')

    def test_nonblocking_status_verifies_and_invalidates_changed_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'model.safetensors'
            path.write_bytes(b'good')
            files = (('model.safetensors', 'repo', 'revision', 'remote', 4, hashlib.sha256(b'good').hexdigest()),)
            start, release = threading.Event(), threading.Event()
            real_inspect = assets.inspect_assets
            def slow_inspect():
                start.set()
                if not release.wait(5):
                    raise RuntimeError('test timed out')
                return real_inspect()
            with patch.object(assets, 'DIRECTORY', root), patch.object(assets, 'FILES', files), \
                 patch.dict(assets._status_state, {'signature': None, 'state': 'unverified', 'thread': None}, clear=True), \
                 patch.object(assets, 'inspect_assets', side_effect=slow_inspect):
                try:
                    self.assertEqual(assets.inspect_assets_nonblocking(), 'verifying')
                    self.assertTrue(start.wait(2))
                    self.assertEqual(assets.inspect_assets_nonblocking(), 'verifying')
                finally:
                    release.set()
                assets._status_state['thread'].join(5)
                self.assertEqual(assets.inspect_assets_nonblocking(), 'verified')
                path.write_bytes(b'bad!')
                self.assertEqual(assets.inspect_assets_nonblocking(), 'verifying')
                assets._status_state['thread'].join(5)
                self.assertEqual(assets.inspect_assets_nonblocking(), 'invalid')
                path.unlink()
                self.assertEqual(assets.inspect_assets_nonblocking(), 'missing')

    def test_hash_detects_in_place_change_during_read(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'model.safetensors'
            path.write_bytes(b'good')
            files = (('model.safetensors', 'repo', 'revision', 'remote', 4, hashlib.sha256(b'good').hexdigest()),)
            def mutate(stream, algorithm):
                digest = hashlib.sha256(b'good')
                path.write_bytes(b'bad!')
                return digest
            with patch.object(assets, 'DIRECTORY', root), patch.object(assets, 'FILES', files), \
                 patch('generators.wan_i2v.assets.hashlib.file_digest', side_effect=mutate):
                self.assertFalse(assets.inspect_assets())
