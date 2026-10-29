"""HY-Motion 폐기와 활성 Kimodo·ANNY 공용 자원 보존 계약."""
import json
from pathlib import Path
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from fastapi.testclient import TestClient
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.common.management_asgi import build_management_application
from tools.review.common.strict_yaml import UniqueConfigLoader
import yaml

CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

class HymotionRetirementTests(unittest.TestCase):
    def test_commands_reject_before_dispatch(self):
        self.assertNotIn('hy-motion', MANAGEMENT_SERVICE_COMMANDS)
        for current_command_name in ('generate', 'prepare', 'resume', 'history', 'history-reset', 'status'):
            with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('hy-motion', current_command_name, {})

    def test_retired_urls_never_build_interface(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            with patch('tools.review.common.management_asgi.build_management_blocks') as current_builder_mock:
                current_application_value = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_root_path/'missing.json', 8770, [])
                with TestClient(current_application_value) as current_test_client:
                    for current_request_path in ('/hy-motion-generator/', '/hy-motion-generator/jobs', '/management/frame/hy-motion-generator/', '/management/?tool=hy-motion-generator'):
                        for current_request_method in ('get', 'post'):
                            self.assertEqual(getattr(current_test_client, current_request_method)(current_request_path).status_code, 410)
                current_builder_mock.assert_not_called()

    def test_stale_catalog_excludes_retired_page(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_source_path = Path(current_directory_name)/'menu.json'
            current_source_path.write_text(json.dumps({'pages':[{'id':'hy-motion-generator','label':'HY-Motion','path':'/hy-motion-generator/','category':'animation-tool','description':'폐기 대상'}]}))
            current_page_records = load_manager_page_records(current_source_path)
            self.assertNotIn('hy-motion-generator', [current_page_record['id'] for current_page_record in current_page_records])
            self.assertIn('kimodo-generator', [current_page_record['id'] for current_page_record in current_page_records])

    def test_shared_renderer_and_registered_assets_preserved(self):
        self.assertFalse((CURRENT_REPOSITORY_ROOT/'generators/hy_motion').exists())
        self.assertFalse((CURRENT_REPOSITORY_ROOT/'tools/review/domains/hy_motion').exists())
        for current_relative_path in ('generators/animation/anny_render/vnccs_render.py', 'generators/animation/anny_render/official_shading.py', 'assets/motion-sheet/hy-motion-walking-v2/manifest.yaml'):
            self.assertTrue((CURRENT_REPOSITORY_ROOT/current_relative_path).is_file())
        with self.assertRaisesRegex(ValueError, '중복 YAML'):
            yaml.load('same: 1\nsame: 2', Loader=UniqueConfigLoader)
        self.assertEqual(yaml.load('value: 3', Loader=UniqueConfigLoader), {'value':3})
