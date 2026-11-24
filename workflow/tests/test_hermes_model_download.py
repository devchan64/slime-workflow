"""Hermes 모델 무결성과 관리 명령 계약 검증."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from workflow.common import hermes_model_download
from workflow.common.management_gateway import resolve_management_command, execute_management_command


class HermesModelDownloadTest(unittest.TestCase):
    def test_long_lived_readiness_resolves_after_directory_rename(self):
        from generators.writer_agent import prepare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / '.model/hermes-agent'
            old.mkdir(parents=True)
            weight = old / hermes_model_download.HERMES_MODEL_FILENAME
            weight.write_bytes(b'model')
            digest = hashlib.sha256(b'model').hexdigest()
            (old / 'ready.sha256').write_text(json.dumps({'sha256': digest, 'size': 5, 'mtime_ns': weight.stat().st_mtime_ns}))
            with patch.object(hermes_model_download, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(hermes_model_download, 'HERMES_MODEL_SHA256', digest):
                self.assertTrue(hermes_model_download.inspect_hermes_model_files())
                new = root / '.model/models/hermes-coding'
                new.parent.mkdir()
                old.rename(new)
                self.assertEqual(hermes_model_download.current_hermes_model_directory(), new)
                self.assertTrue(hermes_model_download.inspect_hermes_model_files())
                hermes_model_download.verify_hermes_model_integrity()
                self.assertEqual(prepare.generation_model_path(), new / hermes_model_download.HERMES_MODEL_FILENAME)

    def test_verified_model_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_model_root = Path(current_temp_directory)
            current_model_path = current_model_root / hermes_model_download.HERMES_MODEL_FILENAME
            current_model_path.write_bytes(b'valid model')
            current_expected_hash = hashlib.sha256(b'valid model').hexdigest()
            with patch.object(hermes_model_download, 'HERMES_MODEL_DIRECTORY', current_model_root), patch.object(hermes_model_download, 'HERMES_MODEL_SHA256', current_expected_hash), patch.object(hermes_model_download, 'download_verified_http'):
                hermes_model_download.prepare_hermes_model_files()
                self.assertTrue(hermes_model_download.inspect_hermes_model_files())
                hermes_model_download.verify_hermes_model_integrity()
                current_model_path.write_bytes(b'wrong model')
                with self.assertRaises(ValueError):
                    hermes_model_download.verify_hermes_model_integrity()

    def test_management_payload_is_strict(self):
        self.assertEqual(resolve_management_command('hermes-model', 'prepare', {'action': 'prepare'}), ('POST', '/hermes-model/jobs'))
        with self.assertRaises(ValueError):
            resolve_management_command('hermes-model', 'prepare', {'action': 'prepare', 'url': 'https://example.invalid'})
        with self.assertRaises(ValueError):
            resolve_management_command('hermes-model', 'model-status', {'extra': True})

    def test_runtime_readiness_is_distinct_from_model_file(self):
        for hermes_runtime_error, hermes_expected_ready in ((None, True), (ValueError('실행환경 필요'), False)):
            hermes_response_stream = io.BytesIO()
            hermes_handler_value = SimpleNamespace(wfile=hermes_response_stream, send_response=lambda *_:None, send_header=lambda *_:None, end_headers=lambda:None)
            with patch('workflow.common.hermes_model_download.inspect_hermes_model_files', return_value=True), patch('workflow.common.model_prepare_process.inspect_registered_preparation', return_value='idle'), patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready', side_effect=hermes_runtime_error):
                execute_management_command('hermes-model', 'model-status', {}, gateway_request_handler=hermes_handler_value)
            hermes_status_record = json.loads(hermes_response_stream.getvalue())
            self.assertTrue(hermes_status_record['ready'])
            self.assertEqual(hermes_status_record['generation_ready'], hermes_expected_ready)
