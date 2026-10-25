"""콘텐츠 실행 설정의 엄격한 입력과 원자적인 환경 적용을 검증한다."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from tools.review.common.content_launch_config import read_content_launch_environment, apply_content_launch_configuration


class ContentLaunchConfigurationTests(unittest.TestCase):
    def test_config_load_and_invalid_input_preserve_environment(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            current_secret_path = current_directory_path/'secret'
            current_secret_path.write_text('test-only-secret')
            current_config_path = current_directory_path/'content.yaml'
            current_config_record = {'serviceOrigin': 'http://127.0.0.1:18083', 'secretFile': str(current_secret_path),
                'assetRoot': current_directory_name, 'snapshotRoot': str(current_directory_path/'snapshots'),
                'gatewayOrigin': 'http://127.0.0.1:8771'}
            current_config_path.write_text(yaml.safe_dump(current_config_record))
            current_loaded_values = read_content_launch_environment(current_config_path)
            self.assertEqual(current_loaded_values['SLIME_CONTENT_STORAGE'], 'database')
            self.assertNotIn('test-only-secret', str(current_loaded_values))
            with patch.dict(os.environ, {'SLIME_CONTENT_CONFIG_FILE': str(current_config_path), 'SLIME_CONTENT_STORAGE': 'file'}):
                current_config_path.write_text(yaml.safe_dump({**current_config_record, 'secret': 'forbidden'}))
                with self.assertRaises(ValueError):
                    apply_content_launch_configuration()
                self.assertEqual(os.environ['SLIME_CONTENT_STORAGE'], 'file')
            for current_invalid_record in ({**current_config_record, 'serviceOrigin': 'http://remote.example'},
                    {**current_config_record, 'snapshotRoot': '../relative'}, {**current_config_record, 'assetRoot': '/missing-assets'}):
                current_config_path.write_text(yaml.safe_dump(current_invalid_record))
                with self.assertRaises(ValueError):
                    read_content_launch_environment(current_config_path)
            current_config_path.write_text(yaml.safe_dump(current_config_record)+'assetRoot: /tmp\n')
            with self.assertRaisesRegex(ValueError, '중복'):
                read_content_launch_environment(current_config_path)

    def test_default_connection_loaded_on_restart(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_path = Path(current_directory_name)
            current_secret_path = current_directory_path/'secret'
            current_secret_path.write_text('test-only-secret')
            current_config_path = current_directory_path/'connection.yaml'
            current_config_path.write_text(yaml.safe_dump({
                'serviceOrigin': 'http://127.0.0.1:18083', 'secretFile': str(current_secret_path),
                'assetRoot': current_directory_name, 'snapshotRoot': str(current_directory_path/'snapshots'),
                'gatewayOrigin': 'http://127.0.0.1:8771'}))
            with patch.dict(os.environ, {}, clear=True), patch(
                    'tools.review.common.content_launch_config.DEFAULT_CONTENT_CONFIG_PATH', current_config_path):
                apply_content_launch_configuration()
                self.assertEqual(os.environ['SLIME_CONTENT_STORAGE'], 'database')
                self.assertEqual(os.environ['SLIME_CONTENT_SNAPSHOT_ROOT'], str(current_directory_path/'snapshots'))
                current_config_path.write_text('invalid: true')
                with self.assertRaises(ValueError):
                    apply_content_launch_configuration()
