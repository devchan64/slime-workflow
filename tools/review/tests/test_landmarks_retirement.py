"""해부학 기준점 기능 폐기와 공유 ANNY 보존을 검증한다."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from unittest.mock import patch
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.common.management_asgi import build_management_application

class LandmarksRetirementTests(unittest.TestCase):
    def test_retired_commands_and_shared_service(self):
        self.assertNotIn('anny-landmarks',MANAGEMENT_SERVICE_COMMANDS)
        self.assertIn('kimodo',MANAGEMENT_SERVICE_COMMANDS)
        for current_command_name in ('landmark-source','landmark-save','landmark-preview','landmark-history','landmark-load'):
            with self.assertRaisesRegex(ValueError,'폐기'):
                resolve_management_command('anny-landmarks',current_command_name,{})

    def test_previous_routes_return_gone_without_build(self):
        with tempfile.TemporaryDirectory() as current_temp_name, patch('tools.review.common.management_asgi.build_management_blocks') as current_builder_mock:
            current_root_path=Path(current_temp_name)
            current_app_value=build_management_application(SimpleHTTPRequestHandler,current_root_path,current_root_path/'missing.json',8770,[])
            async def verify_retired_routes():
                for current_request_path,current_query_bytes in (('/anny-landmarks/landmark-save',b''),('/management/frame/anny-landmarks/',b''),('/management/',b'tool=anny-landmarks')):
                    for current_method_name in ('GET','POST'):
                        current_messages_list=[]
                        async def receive_empty_request():
                            return {'type':'http.request','body':b'','more_body':False}
                        async def collect_response_message(current_message_record):
                            current_messages_list.append(current_message_record)
                        await current_app_value({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':current_method_name,'scheme':'http','path':current_request_path,'raw_path':current_request_path.encode(),'query_string':current_query_bytes,'root_path':'','headers':[],'server':('localhost',8770),'client':('127.0.0.1',1000)},receive_empty_request,collect_response_message)
                        self.assertEqual(current_messages_list[0]['status'],410)
            asyncio.run(verify_retired_routes())
            current_builder_mock.assert_not_called()

    def test_stale_menu_and_shared_viewer(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_menu_path=Path(current_temp_name)/'menu.json'
            current_menu_path.write_text(json.dumps({'pages':[{'id':'anny-landmarks','label':'폐기','path':'/anny-landmarks/','category':'animation-tool','description':'폐기'}]}))
            self.assertNotIn('anny-landmarks',[current_page_record['id'] for current_page_record in load_manager_page_records(current_menu_path)])
        current_repository_root=Path(__file__).resolve().parents[3]
        self.assertFalse((current_repository_root/'tools/review/ui/anny/anny-mesh-viewer.js').exists())
        self.assertFalse((current_repository_root/'tools/review/domains/anny/landmarks.py').exists())
