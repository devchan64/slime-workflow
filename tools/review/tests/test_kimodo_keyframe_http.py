"""Kimodo 키프레임의 실제 로컬 HTTP 게이트웨이·CLI 연결 검사."""
import contextlib
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments, execute_management_command
from tools.review.domains.kimodo.generation import KimodoGenerationManager
from tools.review.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES
from tools.review.tests.test_kimodo_generation import write_keyframe_test_previews
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS


class KimodoKeyframeHttpTests(unittest.TestCase):
    def test_real_gateway_and_cli_share_keyframe_storage(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_temp_root = Path(current_temp_directory)
            current_service_manager = KimodoGenerationManager()
            current_service_manager.job_storage_root = current_temp_root / 'jobs'
            current_service_manager.keyframe_storage_root = current_temp_root / 'keyframes'
            current_job_identifier = '2026-11-06_12-00-00-12345678'
            current_attempt_identifier = 'a' * 32
            current_attempt_root = current_service_manager.job_storage_root / current_job_identifier / 'attempts' / current_attempt_identifier
            current_attempt_root.mkdir(parents=True)
            (current_attempt_root.parent.parent / 'status.json').write_text(json.dumps({'status':'completed'}))
            current_frame_hashes = write_keyframe_test_previews(current_attempt_root, 3)
            (current_attempt_root / 'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'frames':3,'fps':30,'frame_sha256':current_frame_hashes}))
            (current_attempt_root / 'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':[str(current_index) for current_index in range(77)],'parents':list(range(77))}))
            current_motion_arrays = {current_name:np.zeros((3,*current_shape)) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            current_motion_arrays['local_rot_mats'][:] = np.eye(3)
            np.savez_compressed(current_attempt_root / 'motion.npz', **current_motion_arrays)
            current_gateway_instance = ManagementCommandGateway({'kimodo':current_service_manager.handle_image_request})

            class CurrentGatewayHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    if not current_gateway_instance.handle(self):
                        self.send_error(404)

                def log_message(self, current_format_text, *current_format_arguments):
                    pass

            current_http_server = ThreadingHTTPServer(('127.0.0.1', 0), CurrentGatewayHandler)
            current_server_thread = threading.Thread(target=current_http_server.serve_forever, daemon=True)
            current_server_thread.start()
            try:
                current_server_address = f'http://127.0.0.1:{current_http_server.server_port}'
                current_payload_path = current_temp_root / 'save.json'
                current_payload_path.write_text(json.dumps({'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':2,'tag':'가드'}, ensure_ascii=False))
                current_cli_output = io.StringIO()
                with contextlib.redirect_stdout(current_cli_output):
                    self.assertEqual(execute_gateway_arguments('kimodo',['--server-url',current_server_address,'keyframe-save','--payload-file',str(current_payload_path)]), 0)
                current_saved_record = json.loads(current_cli_output.getvalue())
                current_list_record = execute_management_command('kimodo','keyframe-list',{},current_server_address)
                self.assertEqual(current_list_record['records'][0]['id'], current_saved_record['id'])
                current_preview_record = execute_management_command('kimodo','keyframe-preview',{'id':current_saved_record['id']},current_server_address)
                self.assertEqual(current_preview_record['record']['source_frame'], 2)
                import base64
                self.assertEqual(base64.b64decode(current_preview_record['image_base64']), (current_attempt_root/'output-001.png').read_bytes())
                with self.assertRaisesRegex(ValueError, '관리 API 오류 \\(400\\)'):
                    execute_management_command('kimodo','keyframe-preview',{'id':'invalid'},current_server_address)
                current_replacement_record = execute_management_command('kimodo','keyframe-save',{'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':1,'tag':'새 자세'},current_server_address)
                current_replace_path = current_temp_root/'replace.json'
                current_replace_path.write_text(json.dumps({'old_id':current_saved_record['id'],'new_id':current_replacement_record['id']}))
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(execute_gateway_arguments('kimodo',['--server-url',current_server_address,'keyframe-replace','--payload-file',str(current_replace_path)]),0)
                self.assertTrue((current_service_manager.keyframe_storage_root/'.replaced'/current_saved_record['id']/'motion.npz').is_file())
                self.assertEqual([current_record['id'] for current_record in execute_management_command('kimodo','keyframe-list',{},current_server_address)['records']],[current_replacement_record['id']])
                with self.assertRaisesRegex(ValueError, '관리 API 오류 \\(400\\)'):
                    execute_management_command('kimodo','keyframe-replace',{'old_id':current_replacement_record['id'],'new_id':current_replacement_record['id']},current_server_address)
                current_saved_record = current_replacement_record
                current_generation_record = {current_field_name:current_field_value for current_field_name,current_field_value in KIMODO_DEFAULT_SETTINGS.items() if current_field_name != 'schema_version'}
                current_generation_record.update({'action':'generate','post_processing':True,'keyframes':[{'id':current_saved_record['id'],'frame':1},{'id':current_saved_record['id'],'frame':30}]})
                current_generation_path = current_temp_root / 'generate.json'
                current_generation_path.write_text(json.dumps(current_generation_record),encoding='utf-8')

                class CurrentFakeProcess:
                    def wait(self):
                        return 0

                def launch_fake_worker(current_arguments, current_job_root, *current_arguments_tail, **current_keyword_values):
                    (current_job_root/'status.json').write_text('{"status":"completed"}')
                    return CurrentFakeProcess()

                current_cli_output = io.StringIO()
                with patch.object(current_service_manager,'history_storage_path',return_value=current_temp_root/'history'), patch.object(current_service_manager,'validate_generation_runtime'), patch('tools.review.domains.image.image_generation.launch_gpu_process',side_effect=launch_fake_worker), contextlib.redirect_stdout(current_cli_output):
                    self.assertEqual(execute_gateway_arguments('kimodo',['--server-url',current_server_address,'generate','--payload-file',str(current_generation_path),'--detach']), 0)
                    current_generated_record = json.loads(current_cli_output.getvalue())
                    current_new_job_root = current_service_manager.job_storage_root/current_generated_record['id']
                    current_saved_request = json.loads((current_new_job_root/'request.json').read_text())
                    self.assertEqual(current_saved_request['keyframes'],current_generation_record['keyframes'])
                    self.assertEqual(len(current_saved_request['keyframe_snapshots']),2)
                    self.assertTrue((current_new_job_root/'keyframes'/current_saved_record['id']/'motion.npz').is_file())
            finally:
                current_http_server.shutdown()
                current_server_thread.join(timeout=5)
                current_http_server.server_close()


if __name__ == '__main__':
    unittest.main()
