"""포즈 변환 폐기와 공유 이미지 생성기 보존 계약."""
import json
from pathlib import Path
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from fastapi.testclient import TestClient
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.common.management_asgi import build_management_application

class PoseTransferRetirementTests(unittest.TestCase):
    def test_commands_reject_before_dispatch(self):
        self.assertNotIn('pose-transfer', MANAGEMENT_SERVICE_COMMANDS)
        for current_command_name in ('generate','resume','history','status','history-reset'):
            with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError,'폐기'):
                resolve_management_command('pose-transfer',current_command_name,{})
        for current_service_name in ('qwen-21','outfit-transfer','kimodo'):
            self.assertIn(current_service_name,MANAGEMENT_SERVICE_COMMANDS)

    def test_previous_routes_return_gone(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            with patch('tools.review.common.management_asgi.build_management_blocks') as current_builder_mock:
                current_application_value=build_management_application(SimpleHTTPRequestHandler,current_root_path,current_root_path/'missing.json',8770,[])
                with TestClient(current_application_value) as current_test_client:
                    for current_request_path in ('/pose-transfer/','/pose-transfer/jobs','/management/frame/pose-transfer-generator/','/management/?tool=pose-transfer-generator'):
                        for current_request_method in ('get','post'):
                            self.assertEqual(getattr(current_test_client,current_request_method)(current_request_path).status_code,410)
                current_builder_mock.assert_not_called()

    def test_stale_menu_and_shared_interfaces(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_source_path=Path(current_directory_name)/'menu.json'
            current_source_path.write_text(json.dumps({'pages':[{'id':'pose-transfer-generator','label':'포즈 변환','path':'/pose-transfer/','category':'animation-tool','description':'폐기'}]}))
            current_page_records=load_manager_page_records(current_source_path)
            self.assertNotIn('pose-transfer-generator',[current_page_record['id'] for current_page_record in current_page_records])
        with self.assertRaisesRegex(ValueError,'폐기'):
            build_qwen_2511_interface('http://127.0.0.1:8770',qwen21_mode_enabled=True,pose_transfer_enabled=True)
        for current_mode_options in ({'qwen21_mode_enabled':True},{'qwen21_mode_enabled':True,'outfit_transfer_enabled':True}):
            current_interface_blocks=build_qwen_2511_interface('http://127.0.0.1:8770',**current_mode_options)
            self.assertGreater(len(current_interface_blocks.fns),0)

    def test_retired_source_removed(self):
        current_repository_root=Path(__file__).resolve().parents[3]
        for current_relative_path in ('generators/image/vnccs_runtime.py','generators/image/vnccs_profile.py','tools/review/domains/image/pose_transfer_generation.py','tools/review/ui/gradio/pose_transfer_app.py'):
            self.assertFalse((current_repository_root/current_relative_path).exists())
        self.assertTrue((current_repository_root/'assets/motion-sheet/hy-motion-walking-v2/manifest.yaml').is_file())
