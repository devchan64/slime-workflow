import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent import character_source_operations
from workflow.domains.hermes_agent.service import HermesServiceManager
from gui.ui.gradio import operations_history_app


class HermesCharacterSourceTests(unittest.TestCase):
    def test_source_status_reads_bounded_frame_without_mutating_records(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier[:19]/current_job_identifier
            current_frame_path=current_job_path/'down_left'/'frame-0002'
            current_frame_path.mkdir(parents=True)
            current_status_path=current_job_path/'status.json'
            current_status_path.write_text(json.dumps({'status':'completed'}))
            (current_job_path/'request.json').write_text(json.dumps({'frames':[{'direction':'down_left','frame':2}]}))
            current_image_path=current_frame_path/'result.png'
            current_image_path.write_bytes(b'fixture')
            with patch('workflow.domains.character_animation.character_animation_jobs.GENERATION_ROOT_DIRECTORY',current_root_path):
                current_job_record=character_source_operations.read_character_source_job(current_job_identifier)
                self.assertEqual(current_job_record['image'],'/character-animation/files/'+current_job_identifier+'/down_left/frame-0002/result.png')
                current_response_value={'service':'character-animation','job_id':current_job_identifier,'job':current_job_record}
                self.assertEqual(character_source_operations.validate_character_source_response(current_job_identifier,current_response_value),current_job_record)
                current_image_path.unlink()
                current_image_path.symlink_to(current_status_path)
                self.assertEqual(character_source_operations.read_character_source_job(current_job_identifier)['result_status'],'unavailable')
                self.assertEqual(json.loads(current_status_path.read_text()),{'status':'completed'})
                with self.assertRaises(ValueError):character_source_operations.read_character_source_job('../invalid')
                with self.assertRaises(ValueError):character_source_operations.validate_character_source_response(current_job_identifier,{**current_response_value,'job':{**current_job_record,'image':'/private/secret'}})
                with patch.object(character_source_operations,'read_bounded_delegation_record',side_effect=[{'status':'running'}, {'frames':[]}, {'status':'failed'}]):
                    with self.assertRaises(ValueError):character_source_operations.read_character_source_job(current_job_identifier)

    def test_running_frame_uses_separate_progress_and_rechecks_request(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier[:19]/current_job_identifier
            current_frame_path=current_job_path/'down_left'/'frame-0002'
            current_frame_path.mkdir(parents=True)
            current_status_record={'status':'running'}
            current_request_record={'frames':[{'direction':'down_left','frame':2}]}
            current_progress_record={'completed':1}
            (current_job_path/'status.json').write_text(json.dumps(current_status_record))
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            (current_job_path/'progress.json').write_text(json.dumps(current_progress_record))
            (current_frame_path/'result.png').write_bytes(b'fixture')
            with patch('workflow.domains.character_animation.character_animation_jobs.GENERATION_ROOT_DIRECTORY',current_root_path):
                current_job_record=character_source_operations.read_character_source_job(current_job_identifier)
                self.assertEqual(current_job_record['result_status'],'available')
                self.assertTrue(current_job_record['image'].endswith('/down_left/frame-0002/result.png'))
                with patch.object(character_source_operations,'read_bounded_delegation_record',side_effect=[current_status_record,current_request_record,current_progress_record,current_status_record,{'frames':[]}]):
                    with self.assertRaises(ValueError):character_source_operations.read_character_source_job(current_job_identifier)

    def test_character_source_link_crosses_actual_runtime_and_file_handler(self):
        import threading
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from urllib.request import urlopen
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES,execute_management_command
        from workflow.common.management_runtime import ManagementServiceRuntime,bind_stored_management_service
        from workflow.common.management_transport import proxy_management_request
        from workflow.domains.character_animation.character_animation import CharacterAnimationManager
        from workflow.gateway_server import create_gateway_request_handler
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/current_job_identifier[:19]/current_job_identifier
            current_frame_path=current_job_path/'down_left'/'frame-0002'
            current_frame_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_path/'request.json').write_text(json.dumps({'frames':[{'direction':'down_left','frame':2}]}))
            (current_frame_path/'result.png').write_bytes(b'character-test-bytes')
            current_hermes_manager=HermesServiceManager(current_root_path/'hermes',current_root_path/'sessions')
            current_character_manager=CharacterAnimationManager()
            current_bindings_map={current_name:bind_stored_management_service(lambda current_request:False,current_root_path) for current_name in MANAGEMENT_SERVICE_ROUTES}
            current_bindings_map['hermes-agent']=bind_stored_management_service(current_hermes_manager.handle_hermes_request,current_root_path/'hermes')
            current_bindings_map['character-animation']=bind_stored_management_service(current_character_manager.handle,current_root_path)
            current_runtime_value=ManagementServiceRuntime(current_bindings_map,lambda current_request:False,lambda:None)
            current_gateway_server=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_runtime_value.dispatch_runtime_request))
            current_gateway_server.emit_gateway_trace=lambda *current_values:None
            current_gateway_thread=threading.Thread(target=current_gateway_server.serve_forever,daemon=True)
            current_gateway_thread.start()
            current_gateway_url='http://127.0.0.1:'+str(current_gateway_server.server_port)
            class TestProxyHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if not proxy_management_request(self,current_gateway_url):self.send_error(404)
                def log_message(self,*current_values):pass
            current_proxy_server=ThreadingHTTPServer(('127.0.0.1',0),TestProxyHandler)
            current_proxy_thread=threading.Thread(target=current_proxy_server.serve_forever,daemon=True)
            current_proxy_thread.start()
            try:
                with patch('workflow.domains.character_animation.character_animation_jobs.GENERATION_ROOT_DIRECTORY',current_root_path):
                    current_response_value=execute_management_command('hermes-agent','hermes-character-source-status',{'job_id':current_job_identifier},current_gateway_url)
                    current_job_record=character_source_operations.validate_character_source_response(current_job_identifier,current_response_value)
                    with urlopen('http://127.0.0.1:'+str(current_proxy_server.server_port)+current_job_record['image'],timeout=5) as current_http_response:
                        self.assertEqual((current_http_response.status,current_http_response.read()),(200,b'character-test-bytes'))
                    self.assertEqual(json.loads((current_job_path/'status.json').read_text()),{'status':'completed'})
            finally:
                current_proxy_server.shutdown();current_proxy_server.server_close();current_proxy_thread.join(timeout=5)
                current_gateway_server.shutdown();current_gateway_server.server_close();current_gateway_thread.join(timeout=5)

    def test_gateway_command_and_history_ui_validate_selection(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_image_path='/character-animation/files/'+current_job_identifier+'/down_left/frame-0002/result.png'
        current_job_record={'status':'completed','image':current_image_path,'result_status':'available'}
        with TemporaryDirectory() as current_directory_name:
            current_manager_value=HermesServiceManager(Path(current_directory_name)/'jobs',Path(current_directory_name)/'sessions')
            with patch.object(character_source_operations,'read_character_source_job',return_value=current_job_record):
                current_response_value=current_manager_value.execute_hermes_command('hermes-character-source-status',{'job_id':current_job_identifier})
                with self.assertRaises(ValueError):current_manager_value.execute_hermes_command('hermes-character-source-status',{'job_id':current_job_identifier,'extra':True})
        current_page_value={'service':'character-animation','snapshot':'a'*64,'offset':0}
        current_rows_value=[[current_job_identifier,'완료','원본','조회 불가','조회 불가']]
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_response_value) as current_gateway_mock:
            self.assertTrue(operations_history_app.update_operations_media_source_button('character-animation',current_job_identifier,current_page_value,current_rows_value)['interactive'])
            current_result_value=operations_history_app.collect_operations_media_source_status('character-animation',current_job_identifier,current_page_value,current_rows_value,'token')
            self.assertIn('[완료 프레임 열기]('+current_image_path+')',current_result_value['notice'])
            self.assertIn('전체 결과는 별도 확인',current_result_value['notice'])
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-character-source-status',{'job_id':current_job_identifier})
            current_response_value['job']['image']='/private/secret'
            self.assertIn('확인할 수 없습니다',operations_history_app.collect_operations_media_source_status('character-animation',current_job_identifier,current_page_value,current_rows_value,'token')['notice'])
