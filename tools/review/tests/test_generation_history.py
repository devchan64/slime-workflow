import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.image.image_generation import ImageGenerationManager, summarize_generation_progress
from tools.review.tests import test_image_generation


class GenerationHistoryTests(unittest.TestCase):
    def test_progress_from_actual_steps(self):
        self.assertEqual(summarize_generation_progress('denoise step=2/4','running')['percent'],50)
        self.assertEqual(summarize_generation_progress('heartbeat stage=inference step=12/30','running')['percent'],40)
        self.assertEqual(summarize_generation_progress("heartbeat {'stage': 'download-model'}",'running')['stage'],'download-model')
        self.assertIsNone(summarize_generation_progress('stage=load','running')['percent'])
        self.assertEqual(summarize_generation_progress('denoise step=4/4','running')['stage'],'saving')
        self.assertEqual(summarize_generation_progress('denoise step=2/4','failed')['stage'],'failed')

    def test_history_reset_scope(self):
        with tempfile.TemporaryDirectory() as current_directory_name, patch('tools.review.domains.image.image_generation.MANAGER_HISTORY_ROOT',Path(current_directory_name)/'history'):
            current_manager_value=ImageGenerationManager(three_reference_mode=True)
            other_manager_value=ImageGenerationManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-09-23_22-00-00-1234abcd'
            current_job_directory=current_manager_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text('{"status":"completed"}')
            (current_job_directory/'result.png').write_bytes(b'image')
            for selected_manager_value in (current_manager_value,other_manager_value):
                selected_manager_value.history_storage_path().mkdir(parents=True)
                (selected_manager_value.history_storage_path()/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier,'request':{'prompt':'테스트'}}))
            self.assertEqual(current_manager_value.list_generation_history()[0]['status']['status'],'completed')
            current_http_handler=test_image_generation.ImageGenerationTests().make_http_handler('/image-generation-2511/history/reset','POST')
            current_request_bytes=b'{"action":"reset"}'
            current_http_handler.rfile=io.BytesIO(current_request_bytes)
            current_http_handler.headers['Content-Length']=str(len(current_request_bytes))
            current_manager_value.handle_image_request(current_http_handler)
            self.assertEqual(current_http_handler.status,200)
            self.assertEqual(current_manager_value.list_generation_history(),[])
            self.assertEqual(len(list(other_manager_value.history_storage_path().glob('*.json'))),1)
            self.assertTrue((current_job_directory/'result.png').exists())
