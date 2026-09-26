import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tools.review.domains.image.image_generation import ImageGenerationManager, validate_image_request, parse_unique_request


class ImageGenerationTests(unittest.TestCase):
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
        current_manager_value.current_worker_process=SimpleNamespace(poll=lambda:None)
        current_handler_value=self.make_http_handler('/image-generation/jobs','POST')
        current_manager_value.handle_image_request(current_handler_value)
        self.assertEqual(current_handler_value.status,409)


if __name__=='__main__':
    unittest.main()
