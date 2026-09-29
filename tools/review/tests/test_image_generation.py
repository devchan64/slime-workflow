import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tools.review.domains.image.image_generation import ImageGenerationManager, validate_image_request, parse_unique_request


class ImageGenerationTests(unittest.TestCase):
    def test_reset_removes_orphan_files_and_preserves_other_services(self):
        with tempfile.TemporaryDirectory() as temporary_root_name:
            temporary_root_path = Path(temporary_root_name)
            current_manager_value = ImageGenerationManager()
            current_manager_value.job_storage_root = temporary_root_path / 'jobs'
            current_job_directory = current_manager_value.job_storage_root / '2026-09-29_08-43-31-d74d1cd0'
            current_job_directory.mkdir(parents=True)
            (current_job_directory / 'status.json').write_text('{"status":"completed"}')
            (current_job_directory / 'result.png').write_bytes(b'image')
            other_service_directory = current_manager_value.job_storage_root / 'tile-map'
            other_service_directory.mkdir()
            (other_service_directory / 'result.png').write_bytes(b'keep')
            with patch('tools.review.domains.image.image_generation.MANAGER_HISTORY_ROOT', temporary_root_path / 'history'):
                current_handler_value = self.make_http_handler('/image-generation/history/reset', 'POST')
                current_request_bytes = b'{"action":"reset"}'
                current_handler_value.rfile = io.BytesIO(current_request_bytes)
                current_handler_value.headers['Content-Length'] = str(len(current_request_bytes))
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.status, 200)
                self.assertFalse(current_job_directory.exists())
                self.assertTrue((other_service_directory / 'result.png').exists())

    def test_reset_rejects_active_or_symlink_before_deleting(self):
        for unsafe_job_kind in ('running', 'queued', 'symlink'):
            with self.subTest(kind=unsafe_job_kind), tempfile.TemporaryDirectory() as temporary_root_name:
                temporary_root_path = Path(temporary_root_name)
                current_manager_value = ImageGenerationManager()
                current_manager_value.job_storage_root = temporary_root_path / 'jobs'
                completed_job_directory = current_manager_value.job_storage_root / '2026-09-29_08-43-31-d74d1cd0'
                completed_job_directory.mkdir(parents=True)
                (completed_job_directory / 'status.json').write_text('{"status":"completed"}')
                unsafe_job_directory = current_manager_value.job_storage_root / '2026-09-29_08-43-32-d74d1cd1'
                if unsafe_job_kind == 'symlink':
                    unsafe_job_directory.symlink_to(completed_job_directory, target_is_directory=True)
                else:
                    unsafe_job_directory.mkdir()
                    (unsafe_job_directory / 'status.json').write_text(json.dumps({'status': unsafe_job_kind}))
                with self.assertRaises(ValueError):
                    current_manager_value.reset_generation_history()
                self.assertTrue(completed_job_directory.exists())

    def test_request_validation(self):
        self.assertEqual(validate_image_request({'action':'prepare'}),{'action':'prepare'})
        validate_image_request({'action':'generate','steps':4,'prompt':'풍경','width':1024,'height':512})
        validate_image_request({'action':'generate','steps':30,'prompt':'풍경','width':512,'height':512})
        for current_invalid_steps in (True, '4', 20, 4.0):
            with self.assertRaises(ValueError):
                validate_image_request({'action':'generate','steps':current_invalid_steps,'prompt':'풍경','width':512,'height':512})
        for current_request_record in [ {'action':'prepare','model':'other'}, {'action':'generate','steps':4,'prompt':'','width':512,'height':512}, {'action':'generate','steps':4,'prompt':'x','width':True,'height':512}, {'action':'generate','steps':4,'prompt':'x','width':100000,'height':512} ]:
            with self.assertRaises(ValueError):
                validate_image_request(current_request_record)
        with self.assertRaises(ValueError):
            parse_unique_request([('action','prepare'),('action','generate')])

    def make_http_handler(self, current_path_value, current_method_value='GET', current_origin_value='http://127.0.0.1:8770'):
        current_body_value=b'{"action":"prepare"}'
        current_handler_value=SimpleNamespace(path=current_path_value,command=current_method_value,headers={'Host':'127.0.0.1:8770','Origin':current_origin_value,'Content-Type':'application/json','Content-Length':str(len(current_body_value))},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(current_body_value),wfile=io.BytesIO(),status=None)
        current_handler_value.send_response=lambda current_status_code:setattr(current_handler_value,'status',current_status_code)
        current_handler_value.send_header=lambda *current_header_values:None
        current_handler_value.end_headers=lambda:None
        return current_handler_value

    def test_retired_page_status_and_origin(self):
        current_manager_value=ImageGenerationManager()
        current_handler_value=self.make_http_handler('/image-generation/')
        self.assertTrue(current_manager_value.handle_image_request(current_handler_value))
        self.assertEqual(current_handler_value.status,410)
        current_handler_value=self.make_http_handler('/image-generation/jobs','POST','https://elsewhere.invalid')
        current_manager_value.handle_image_request(current_handler_value)
        self.assertEqual(current_handler_value.status,400)
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_job_root=Path(current_temp_name)/'2026-09-23_22-00-00-1234abcd'
            current_job_root.mkdir()
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            (current_job_root/'result.png').write_bytes(b'test-image')
            (current_job_root/'reference-1.png').write_bytes(b'reference-image')
            with patch.object(current_manager_value,'job_storage_root',Path(current_temp_name)):
                current_handler_value=self.make_http_handler('/image-generation/jobs/'+current_job_root.name)
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.status,200)
                self.assertIn('image',json.loads(current_handler_value.wfile.getvalue()))
                current_handler_value=self.make_http_handler('/image-generation/jobs/'+current_job_root.name+'/result.png')
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.wfile.getvalue(),b'test-image')
                current_handler_value=self.make_http_handler('/image-generation/jobs/'+current_job_root.name+'/reference-1.png')
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.wfile.getvalue(),b'reference-image')
                current_handler_value=self.make_http_handler('/image-generation/jobs/'+current_job_root.name+'/request.json')
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.status,404)
    def test_running_image_generation_does_not_block_queue_submission(self):
        current_manager_value=ImageGenerationManager()
        current_request_value={'action':'generate','prompt':'대기열 검증','width':512,'height':512,'steps':4,'seed':1}
        current_request_bytes=json.dumps(current_request_value).encode()
        current_handler_value=self.make_http_handler('/image-generation/jobs','POST')
        current_handler_value.rfile=io.BytesIO(current_request_bytes)
        current_handler_value.headers['Content-Length']=str(len(current_request_bytes))
        worker_finished_event=threading.Event()
        queued_worker_process=SimpleNamespace(poll=lambda:None,wait=worker_finished_event.wait)
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path=Path(temporary_directory_name)
            def launch_queued_process(command_argument_values,generation_job_path,generation_service_name,**process_option_values):
                (generation_job_path/'status.json').write_text('{"status":"queued"}')
                return queued_worker_process
            with patch.object(current_manager_value,'job_storage_root',temporary_root_path/'jobs'),patch.object(current_manager_value,'history_storage_path',return_value=temporary_root_path/'history'),patch('tools.review.domains.image.image_generation.launch_gpu_process',side_effect=launch_queued_process):
                current_manager_value.current_worker_process=SimpleNamespace(poll=lambda:None)
                current_manager_value.handle_image_request(current_handler_value)
                self.assertEqual(current_handler_value.status,202)
                self.assertEqual(json.loads(current_handler_value.wfile.getvalue())['status'],'queued')
                self.assertEqual(len(current_manager_value.list_generation_history()),1)
                worker_finished_event.set()
                time.sleep(.01)


if __name__=='__main__':
    unittest.main()
