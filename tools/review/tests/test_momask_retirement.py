"""MoMask 폐기·과거 URL 차단과 HY-Motion 분리를 검증한다."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from tools.review.common.management_gateway import resolve_management_command
from tools.review.common.retired_momask import RetiredMoMaskHandler as MoMaskGenerationManager


class MoMaskRetirementTests(unittest.TestCase):
    def test_rig_renderer_removed_and_shared_templates_preserved(self):
        current_repository_root = Path(__file__).resolve().parents[3]
        for current_removed_path in ('generators/animation/render_momask_rig.py', 'generators/animation/resolve_default_rig.py', 'generators/animation/config/default_walk_rig.yaml', 'generators/momask/render_anny_frames.py', 'generators/momask/templates/render_asset.py'):
            self.assertFalse((current_repository_root / current_removed_path).exists())
        for current_shared_path in ('generators/momask/templates/run_stage.py', 'generators/momask/templates/retarget_loop.py', 'generators/hy_motion/templates/vnccs_render.py'):
            self.assertTrue((current_repository_root / current_shared_path).is_file())
        from generators.momask.run_managed_generation import reject_retired_generation
        from generators.momask.resume_render import resume_render_frames
        for current_retired_function, current_argument_values in ((reject_retired_generation, ()), (resume_render_frames, (Path('/unused'),))):
            with self.assertRaisesRegex(ValueError, '폐기'):
                current_retired_function(*current_argument_values)

    def test_commands_are_rejected_before_storage_access(self):
        for current_command_name in ('generate', 'resume', 'history', 'status', 'history-reset'):
            with self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('momask', current_command_name, {})

    def test_retired_domain_is_removed(self):
        current_review_root = Path(__file__).resolve().parents[1]
        self.assertFalse((current_review_root / 'domains/momask').exists())
        self.assertFalse((current_review_root / 'momask_jobs.py').exists())
        from tools.review.common.retired_momask import reject_retired_record_access
        with self.assertRaisesRegex(ValueError, '폐기'):
            reject_retired_record_access('../unused')

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
