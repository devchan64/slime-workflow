"""MoMask 폐기·과거 URL 차단과 HY-Motion 분리를 검증한다."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from workflow.common.management_gateway import resolve_management_command
from workflow.common.retired_momask import RetiredMoMaskHandler as MoMaskGenerationManager


class MoMaskRetirementTests(unittest.TestCase):
    def test_retired_rig_implementation_removed(self):
        root = Path(__file__).resolve().parents[2]
        for name in ('generators/momask', 'generators/animation/anny_render', 'workflow/common/openpose_maps.py'):
            self.assertFalse((root / name).exists(), name)

    def test_commands_are_rejected_before_storage_access(self):
        for current_command_name in ('generate', 'resume', 'history', 'status', 'history-reset'):
            with self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('momask', current_command_name, {})

    def test_retired_domain_is_removed(self):
        current_review_root = Path(__file__).resolve().parents[1]
        self.assertFalse((current_review_root / 'domains/momask').exists())
        self.assertFalse((current_review_root / 'momask_jobs.py').exists())
        from workflow.common.retired_momask import reject_retired_record_access
        with self.assertRaisesRegex(ValueError, '폐기'):
            reject_retired_record_access('../unused')

    def test_legacy_http_returns_gone(self):
        for current_request_path in ('/momask-generator/', '/momask-generator/history', '/momask-generator/jobs'):
            current_status_codes = []
            current_request_handler = SimpleNamespace(path=current_request_path, headers={'Host': '127.0.0.1:8771'}, server=SimpleNamespace(server_port=8771), send_response=current_status_codes.append, send_header=lambda *current_header_values: None, end_headers=lambda: None, wfile=io.BytesIO())
            self.assertTrue(MoMaskGenerationManager().handle(current_request_handler))
            self.assertEqual(current_status_codes, [410])

    def test_menu_excludes_legacy_records(self):
        from workflow.build_animation_tools import build_animation_tools
        from workflow.common.management_catalog import load_manager_page_records
        self.assertNotIn('momask-generator', [current_record['id'] for current_record in build_animation_tools(None)])
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_menu_path = Path(current_temporary_directory) / 'menu.json'
            current_menu_path.write_text(json.dumps({'pages': [{'id': 'momask-generator', 'label': 'MoMask', 'path': '/momask-generator/', 'category': 'animation-tool', 'description': '과거 도구'}]}))
            self.assertNotIn('momask-generator', [current_record['id'] for current_record in load_manager_page_records(current_menu_path)])
        with self.assertRaisesRegex(ValueError, '폐기'):
            resolve_management_command('hy-motion', 'history', {})
