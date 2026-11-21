"""기록 폴더 열기의 경로 경계와 요청 출처 검증."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from workflow.common.record_folders import resolve_record_folder, handle_record_folder_request

class RecordFolderTests(unittest.TestCase):
    def test_registered_path_and_symlink_boundary(self):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            temporary_root_directory=Path(temporary_root_path)
            allowed_root_directory=temporary_root_directory/'jobs';allowed_root_directory.mkdir()
            valid_record_directory=allowed_root_directory/'valid';valid_record_directory.mkdir();(valid_record_directory/'status.json').write_text('{}')
            folder_service_routes={'/test':(allowed_root_directory,lambda record_identifier_value:allowed_root_directory/record_identifier_value)}
            self.assertEqual(resolve_record_folder(folder_service_routes,'/test','valid'),valid_record_directory)
            (allowed_root_directory/'escape').symlink_to(temporary_root_directory,target_is_directory=True)
            for selected_record_identifier in ('../valid','escape','missing'):
                with self.assertRaises(ValueError):resolve_record_folder(folder_service_routes,'/test',selected_record_identifier)
            with self.assertRaises(ValueError):resolve_record_folder(folder_service_routes,'/other','valid')

    @patch('workflow.common.record_folders.subprocess.run')
    def test_origin_and_explicit_open_request(self, folder_launch_mock):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            record_root_directory=Path(temporary_root_path);(record_root_directory/'status.json').write_text('{}')
            folder_service_routes={'/test':(record_root_directory,lambda record_identifier_value:record_root_directory)}
            response_status_values=[]
            request_body_bytes=json.dumps({'route':'/test','id':'valid'}).encode()
            request_handler_mock=SimpleNamespace(path='/management/record-folder/open',server=SimpleNamespace(server_port=8770),headers={'Host':'127.0.0.1:8770','Origin':'https://external.example','Content-Type':'application/json','Content-Length':str(len(request_body_bytes))},rfile=io.BytesIO(request_body_bytes),wfile=io.BytesIO(),send_response=response_status_values.append,send_header=lambda *header_field_values:None,end_headers=lambda:None)
            handle_record_folder_request(request_handler_mock,folder_service_routes)
            folder_launch_mock.assert_not_called();self.assertEqual(response_status_values[-1],400)
            request_handler_mock.headers['Origin']='http://127.0.0.1:8770'
            handle_record_folder_request(request_handler_mock,folder_service_routes)
            self.assertEqual(response_status_values[-1],200)
            self.assertEqual(folder_launch_mock.call_args.args[0],['xdg-open',str(record_root_directory)])

    @patch('workflow.common.record_folders.subprocess.run')
    def test_inspection_validates_origin_and_path_without_opening(self, folder_launch_mock):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            root=Path(temporary_root_path); job=root/'valid'; job.mkdir(); (job/'status.json').write_text('{}')
            routes={'/test':(root,lambda identifier:root/identifier)}
            body=json.dumps({'route':'/test','id':'valid'}).encode(); statuses=[]
            handler=SimpleNamespace(path='/management/record-folder/inspect',server=SimpleNamespace(server_port=8770),headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(body))},rfile=io.BytesIO(body),wfile=io.BytesIO(),send_response=statuses.append,send_header=lambda *args:None,end_headers=lambda:None)
            self.assertTrue(handle_record_folder_request(handler,routes))
            self.assertEqual(statuses[-1],200)
            self.assertEqual(json.loads(handler.wfile.getvalue())['path'],str(job))
            folder_launch_mock.assert_not_called()

    @patch('workflow.common.record_folders.subprocess.run')
    def test_inspection_resolves_registered_service_route(self, folder_launch_mock):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            root=Path(temporary_root_path); job=root/'valid'; job.mkdir(); (job/'status.json').write_text('{}')
            routes={'/flux-expression-generator':(root,lambda identifier:root/identifier)}
            body=json.dumps({'service':'flux-expression','id':'valid'}).encode(); statuses=[]
            handler=SimpleNamespace(path='/management/record-folder/inspect',server=SimpleNamespace(server_port=8770),headers={'Host':'127.0.0.1:8770','Origin':'http://127.0.0.1:8770','Content-Type':'application/json','Content-Length':str(len(body))},rfile=io.BytesIO(body),wfile=io.BytesIO(),send_response=statuses.append,send_header=lambda *args:None,end_headers=lambda:None)
            self.assertTrue(handle_record_folder_request(handler,routes))
            self.assertEqual(statuses[-1],200)
            self.assertEqual(json.loads(handler.wfile.getvalue())['path'],str(job))
            folder_launch_mock.assert_not_called()
