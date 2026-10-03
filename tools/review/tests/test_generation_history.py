import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.common.gradio_history import format_history_progress, format_generation_status
from tools.review.domains.image.image_generation import ImageGenerationManager, summarize_generation_progress
from tools.review.tests import test_image_generation


class GenerationHistoryTests(unittest.TestCase):
    def test_oom_failure_status_preserves_other_states(self):
        self.assertEqual(format_generation_status({'status':'failed','error':'CUDA out of memory. Tried to allocate 292 MiB.'}), 'OOM 실패 · GPU 메모리 부족')
        self.assertEqual(format_generation_status({'status':'failed','error':'입력 이미지 오류'}), '실패')
        self.assertEqual(format_generation_status({'status':'completed','error':'CUDA out of memory'}), '완료')
        self.assertEqual(format_generation_status('failed'), '실패')

    def test_individual_history_delete_removes_image_result_files(self):
        with tempfile.TemporaryDirectory() as current_directory_name, patch('tools.review.domains.image.image_generation.MANAGER_HISTORY_ROOT',Path(current_directory_name)/'history'):
            current_manager_value=ImageGenerationManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-09-27_12-00-00-1234abcd'
            current_job_directory=current_manager_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text('{"status":"completed"}')
            (current_job_directory/'result.png').write_bytes(b'image')
            current_manager_value.history_storage_path().mkdir(parents=True)
            (current_manager_value.history_storage_path()/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier,'request':{'prompt':'테스트'}}))

            self.assertEqual(current_manager_value.delete_generation_history(current_job_identifier),{'deleted':current_job_identifier,'files_preserved':False})
            self.assertEqual(current_manager_value.list_generation_history(),[])
            self.assertFalse(current_job_directory.exists())

    def test_individual_history_delete_rejects_active_job(self):
        with tempfile.TemporaryDirectory() as current_directory_name, patch('tools.review.domains.image.image_generation.MANAGER_HISTORY_ROOT',Path(current_directory_name)/'history'):
            current_manager_value=ImageGenerationManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-09-27_12-00-00-1234abcd'
            current_job_directory=current_manager_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text('{"status":"running"}')
            current_manager_value.history_storage_path().mkdir(parents=True)
            (current_manager_value.history_storage_path()/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier}))

            with self.assertRaisesRegex(ValueError,'먼저 중지'):
                current_manager_value.delete_generation_history(current_job_identifier)

    def test_history_delete_endpoint_uses_selected_identifier_only(self):
        with tempfile.TemporaryDirectory() as current_directory_name, patch('tools.review.domains.image.image_generation.MANAGER_HISTORY_ROOT',Path(current_directory_name)/'history'):
            current_manager_value=ImageGenerationManager()
            current_manager_value.job_storage_root=Path(current_directory_name)/'jobs'
            current_job_identifier='2026-09-27_12-00-00-1234abcd'
            current_job_directory=current_manager_value.job_storage_root/current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text('{"status":"completed"}')
            current_manager_value.history_storage_path().mkdir(parents=True)
            (current_manager_value.history_storage_path()/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier}))
            current_http_handler=test_image_generation.ImageGenerationTests().make_http_handler('/image-generation/history/'+current_job_identifier+'/delete','POST')
            current_request_bytes=json.dumps({'id':current_job_identifier}).encode()
            current_http_handler.rfile=io.BytesIO(current_request_bytes)
            current_http_handler.headers['Content-Length']=str(len(current_request_bytes))

            current_manager_value.handle_image_request(current_http_handler)

            self.assertEqual(current_http_handler.status,200)
            self.assertEqual(json.loads(current_http_handler.wfile.getvalue())['deleted'],current_job_identifier)

    def test_delete_rejects_unsafe_or_unknown_job_without_removing_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_manager_value = ImageGenerationManager()
            current_manager_value.job_storage_root = Path(temporary_directory_name) / 'jobs'
            current_job_identifier = '2026-09-27_12-00-00-1234abcd'
            current_job_directory = current_manager_value.job_storage_root / current_job_identifier
            current_job_directory.mkdir(parents=True)
            (current_job_directory / 'status.json').write_text('{"status":"unknown"}')
            for selected_job_identifier in ('../outside', current_job_identifier):
                with self.assertRaises(ValueError):
                    current_manager_value.delete_generation_history(selected_job_identifier)
            self.assertTrue(current_job_directory.exists())
            (current_job_directory / 'status.json').write_text('{"status":"completed"}')
            linked_job_identifier = '2026-09-27_12-00-00-abcd1234'
            (current_manager_value.job_storage_root / linked_job_identifier).symlink_to(current_job_directory, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, '심볼릭 링크'):
                current_manager_value.delete_generation_history(linked_job_identifier)
            self.assertTrue(current_job_directory.exists())

    def test_progress_from_actual_steps(self):
        self.assertEqual(summarize_generation_progress('denoise step=2/4','running')['percent'],50)
        self.assertEqual(summarize_generation_progress("heartbeat {'stage': 'inference', 'step': 26, 'total': 40}",'running')['percent'],65)
        self.assertEqual(summarize_generation_progress("step=2/4\nheartbeat {'stage': 'inference', 'step': 26, 'total': 40}",'running')['step'],26)
        self.assertEqual(summarize_generation_progress("heartbeat {'stage': 'inference', 'step': 26, 'total': 40}\nstep=28/40",'running')['percent'],70)
        self.assertEqual(summarize_generation_progress("heartbeat {'stage': 'inference', 'step': 40, 'total': 40}",'running')['stage'],'saving')
        self.assertEqual(summarize_generation_progress('heartbeat stage=inference step=12/30','running')['percent'],40)
        self.assertEqual(summarize_generation_progress("heartbeat {'stage': 'download-model'}",'running')['stage'],'download-model')
        self.assertIsNone(summarize_generation_progress('stage=load','running')['percent'])
        self.assertEqual(summarize_generation_progress('denoise step=4/4','running')['stage'],'saving')
        self.assertEqual(summarize_generation_progress('denoise step=2/4','failed')['stage'],'failed')

    def test_progress_display_uses_actual_image_steps(self):
        self.assertEqual(format_history_progress({'stage':'inference','step':2,'total':4,'percent':50}),'추론 중 50% · 2/4스텝')
        self.assertEqual(format_history_progress({'stage':'queued','queue_position':3}),'GPU 대기 중 · 대기 순서 3')

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
            self.assertFalse(current_job_directory.exists())
