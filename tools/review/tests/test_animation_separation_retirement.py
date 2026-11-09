"""캐릭터 레퍼런스 복장 분리 생성기 폐기 계약."""
import asyncio
import json
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import httpx
from tools.review.common.management_asgi import build_management_application
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.ui.gradio.management_menu_app import load_manager_page_records
from tools.review.build_animation_tools import build_animation_tools


class AnimationSeparationRetirementTests(unittest.TestCase):
    def test_service_and_stale_menu_are_retired(self):
        self.assertNotIn('animation-separation', MANAGEMENT_SERVICE_COMMANDS)
        for current_command_name in ('generate', 'resume', 'history', 'history-reset'):
            with self.assertRaisesRegex(ValueError, '폐기'):
                resolve_management_command('animation-separation', current_command_name, {})
        self.assertNotIn('animation-separation', [current_record['id'] for current_record in build_animation_tools(None)])
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_source_path = Path(current_directory_name) / 'menu.json'
            current_source_path.write_text(json.dumps({'pages': [{'id': 'animation-separation', 'label': '복장 분리', 'path': '/animation-separation/', 'category': 'image-generation', 'description': '폐기'}]}))
            self.assertNotIn('animation-separation', [current_record['id'] for current_record in load_manager_page_records(current_source_path)])

    def test_old_paths_return_gone(self):
        async def verify_retired_paths():
            with tempfile.TemporaryDirectory() as current_directory_name:
                current_root_path = Path(current_directory_name)
                current_application = build_management_application(SimpleHTTPRequestHandler, current_root_path, current_root_path / 'missing.json', 8770, [])
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=current_application), base_url='http://localhost') as current_client:
                    for current_path in ('/animation-separation/', '/animation-separation/jobs', '/management/frame/animation-separation/', '/management/?tool=animation-separation'):
                        for current_method in ('GET', 'POST'):
                            current_response = await current_client.request(current_method, current_path)
                            self.assertEqual(current_response.status_code, 410)
        asyncio.run(verify_retired_paths())
