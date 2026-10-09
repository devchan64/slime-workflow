"""MoMask 폐기·과거 URL 차단과 HY-Motion 분리를 검증한다."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from tools.review.common.management_gateway import resolve_management_command
from tools.review.domains.momask import momask_jobs
from tools.review.domains.momask.momask_generation import MoMaskGenerationManager


class MoMaskRetirementTests(unittest.TestCase):
    def test_commands_are_rejected_before_storage_access(self):
        for current_command_name in ('generate', 'resume', 'history', 'status', 'history-reset'):
            with self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('momask', current_command_name, {})
        with self.assertRaisesRegex(ValueError, '폐기'):
            momask_jobs.start_generation_job('standing', ['down_left'])
        with self.assertRaisesRegex(ValueError, '폐기'):
            momask_jobs.resume_generation_job('unused')

    def test_legacy_http_returns_gone(self):
        for current_request_path in ('/momask-generator/', '/momask-generator/history', '/momask-generator/jobs'):
            current_status_codes = []
            current_request_handler = SimpleNamespace(path=current_request_path, headers={'Host': '127.0.0.1:8771'}, server=SimpleNamespace(server_port=8771), send_response=current_status_codes.append, send_header=lambda *current_header_values: None, end_headers=lambda: None, wfile=io.BytesIO())
            self.assertTrue(MoMaskGenerationManager().handle(current_request_handler))
            self.assertEqual(current_status_codes, [410])

    def test_menu_excludes_legacy_records(self):
        from tools.review.build_animation_tools import build_animation_tools
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        self.assertNotIn('momask-generator', [current_record['id'] for current_record in build_animation_tools(None)])
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_menu_path = Path(current_temporary_directory) / 'menu.json'
            current_menu_path.write_text(json.dumps({'pages': [{'id': 'momask-generator', 'label': 'MoMask', 'path': '/momask-generator/', 'category': 'animation-tool', 'description': '과거 도구'}]}))
            self.assertNotIn('momask-generator', [current_record['id'] for current_record in load_manager_page_records(current_menu_path)])
        self.assertEqual(resolve_management_command('hy-motion', 'history', {})[0], 'GET')
