"""두 음악 생성기의 폐기 경계·파일 삭제·UI 갱신 계약을 격리 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from generators.music.contracts import MUSIC_SERVICE_NAMES, resolve_music_profile
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.music.generation import MusicGenerationManager


class MusicManagementAuditTests(unittest.TestCase):
    def test_retired_model_cannot_return_from_cached_menu(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        self.assertEqual(MUSIC_SERVICE_NAMES,('music-minimax',))
        self.assertNotIn('music-stable-audio',MANAGEMENT_SERVICE_COMMANDS)
        self.assertNotIn('music-ace-step',MANAGEMENT_SERVICE_COMMANDS)
        with self.assertRaises(ValueError):
            resolve_music_profile('music-ace-step')
        with self.assertRaises(ValueError):
            resolve_management_command('music-stable-audio','generate',{})
        with self.assertRaises(ValueError):
            resolve_music_profile('music-stable-audio')
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_menu_path=Path(current_temp_directory)/'menu.json'
            current_menu_path.write_text(json.dumps({'pages':[{'id':'music-ace-step','label':'폐기','path':'/management/frame/music-stable-audio/','category':'music-generation','description':'이전 메뉴'}]}))
            current_music_records=[current_page_record['id'] for current_page_record in load_manager_page_records(current_menu_path) if current_page_record['category']=='sound-management']
            self.assertCountEqual(current_music_records,[*MUSIC_SERVICE_NAMES,'sfx-dasheng-audiogen'])

    def test_both_services_delete_files_and_reset_hidden_jobs(self):
        for current_service_name in MUSIC_SERVICE_NAMES:
            with self.subTest(service=current_service_name),tempfile.TemporaryDirectory() as current_temp_directory,patch('tools.review.domains.music.generation.launch_gpu_process'):
                current_test_root=Path(current_temp_directory)
                current_music_service=MusicGenerationManager(current_service_name)
                current_music_service.job_storage_root=current_test_root/'jobs'
                current_music_service.history_storage_root=current_test_root/'history'
                current_music_service.runtime_python_path=current_test_root/'python'
                current_music_service.runtime_python_path.touch()
                current_protected_path=current_test_root/'external-source.wav'
                current_protected_path.write_bytes(b'protected')
                current_job_paths=[]
                for current_job_number in range(3):
                    current_job_record=current_music_service.create_music_job({'prompt':'flute','seed':current_job_number})
                    current_job_root=current_music_service.resolve_music_job(current_job_record['id'])
                    write_record_atomically(current_job_root/'status.json',{'status':'completed'})
                    for current_relative_name in ('input.wav','intermediate.bin','attempts/first/music.wav','attempts/first/metrics.json','attempts/second/request.json','attempts/second/worker.log'):
                        current_artifact_path=current_job_root/current_relative_name
                        current_artifact_path.parent.mkdir(parents=True,exist_ok=True)
                        current_artifact_path.write_bytes(b'test')
                    current_job_paths.append(current_job_root)
                current_expected_bytes=sum(current_artifact_path.stat().st_size for current_artifact_path in current_job_paths[0].rglob('*') if current_artifact_path.is_file())+(current_music_service.history_storage_root/(current_job_paths[0].name+'.json')).stat().st_size
                current_delete_result=current_music_service.execute_music_command('history-delete',{'id':current_job_paths[0].name})
                self.assertEqual(current_delete_result['deleted_jobs'],1)
                self.assertEqual(current_delete_result['deleted_bytes'],current_expected_bytes)
                self.assertFalse(current_job_paths[0].exists())
                self.assertTrue(current_job_paths[1].exists())
                (current_music_service.history_storage_root/(current_job_paths[2].name+'.json')).unlink()
                self.assertEqual(current_music_service.execute_music_command('history-reset-preview',{})['job_count'],2)
                current_job_paths[1].joinpath('external-link').symlink_to(current_protected_path)
                with self.assertRaises(ValueError):
                    current_music_service.execute_music_command('history-reset',{'action':'reset'})
                self.assertTrue(current_job_paths[2].exists())
                current_job_paths[1].joinpath('external-link').unlink()
                for current_live_state in ('queued','running'):
                    write_record_atomically(current_job_paths[1]/'status.json',{'status':current_live_state})
                    self.assertFalse(current_music_service.execute_music_command('history-reset-preview',{})['can_reset'])
                    with self.assertRaises(ValueError):
                        current_music_service.execute_music_command('history-delete',{'id':current_job_paths[1].name})
                    with self.assertRaises(ValueError):
                        current_music_service.execute_music_command('history-reset',{'action':'reset'})
                write_record_atomically(current_job_paths[1]/'status.json',{'status':'completed'})
                current_reset_result=current_music_service.execute_music_command('history-reset',{'action':'reset'})
                self.assertEqual(current_reset_result['deleted_jobs'],2)
                self.assertGreater(current_reset_result['deleted_bytes'],0)
                self.assertFalse(any(current_job_path.exists() for current_job_path in current_job_paths))
                self.assertEqual(current_protected_path.read_bytes(),b'protected')
                self.assertEqual(current_music_service.execute_music_command('history',{})['records'],[])

    def test_music_confirmation_preserves_prompt_readiness(self):
        from tools.review.ui.gradio.music_app import build_music_interface
        for current_service_name in MUSIC_SERVICE_NAMES:
            current_interface_blocks = build_music_interface(current_service_name, 'http://127.0.0.1:9988')
            current_callback_records = [current_callback.fn for current_callback in current_interface_blocks.fns.values() if current_callback.fn]
            current_readiness_callback = next(current_callback for current_callback in current_callback_records if current_callback.__name__ == 'refresh_generation_readiness')
            current_cancel_callback = next(current_callback for current_callback in current_callback_records if current_callback.__name__ == 'cancel_generation_confirmation')
            self.assertFalse(current_readiness_callback(None, '')['interactive'])
            self.assertTrue(current_readiness_callback(None, 'flute')['interactive'])
            current_pending_record = {'inputs': ('flute',), 'consumed': False}
            self.assertFalse(current_readiness_callback(current_pending_record, 'changed')['interactive'])
            self.assertFalse(current_cancel_callback(current_pending_record, '  ')[2]['interactive'])
            self.assertTrue(current_cancel_callback(None, 'flute')[2]['interactive'])

    def test_deleted_active_record_clears_preview_without_hiding_existing_errors(self):
        from tools.review.ui.gradio.music_app import build_music_interface
        for current_service_name in MUSIC_SERVICE_NAMES:
            current_interface_blocks=build_music_interface(current_service_name,'http://127.0.0.1:9988')
            current_refresh_callback=next(current_callback.fn for current_callback in current_interface_blocks.fns.values() if current_callback.fn and current_callback.fn.__name__=='refresh_music_result')
            def execute_deleted_command(current_service_value,current_command_value,current_payload_value):
                if current_command_value=='status':raise ValueError('작업 경로가 없습니다')
                return {'records':[]}
            with patch('tools.review.ui.gradio.music_app.execute_remote_management_command',side_effect=execute_deleted_command):
                current_update_values=current_refresh_callback('removed',True,'old.wav')
                self.assertEqual(current_update_values[-1],'')
                self.assertIn('삭제',current_update_values[0])
                self.assertNotIn('old.wav',current_update_values[1])
            with patch('tools.review.ui.gradio.music_app.execute_remote_management_command',side_effect=[ValueError('손상된 기록'),{'records':[{'id':'existing'}]}]):
                with self.assertRaisesRegex(ValueError,'손상된 기록'):
                    current_refresh_callback('existing',True,'')

    def test_both_services_keep_attempt_telemetry_across_terminal_and_resume_states(self):
        from tools.review.common.gradio_audio_results import describe_audio_generation_status
        for current_service_name in MUSIC_SERVICE_NAMES:
            with self.subTest(service=current_service_name), tempfile.TemporaryDirectory() as current_temp_directory:
                current_music_service = MusicGenerationManager(current_service_name)
                current_music_service.job_storage_root = Path(current_temp_directory)/'jobs'
                current_job_root = current_music_service.job_storage_root/'2026-10-15_00-00-00-12345678'
                current_job_root.mkdir(parents=True)
                current_attempt_names = ('a'*32, 'b'*32)
                for current_attempt_name, current_peak_value in zip(current_attempt_names, (7123, 6210)):
                    current_attempt_root = current_job_root/'attempts'/current_attempt_name
                    current_attempt_root.mkdir(parents=True)
                    write_record_atomically(current_attempt_root/'metrics.json', {
                        'stage':'inference', 'estimate':{'remaining':12, 'basis':'검증 표본'},
                        'gpu_observations':{'GPU-test':{'process_current_mib':0,
                            'process_peak_mib':current_peak_value,'scope':'작업자 및 자식 프로세스'}},
                    })
                current_first_metrics_path = current_job_root/'attempts'/current_attempt_names[0]/'metrics.json'
                current_first_metrics_bytes = current_first_metrics_path.read_bytes()
                write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_names[0]})
                for current_status_name in ('running','completed','failed','cancelled'):
                    write_record_atomically(current_job_root/'status.json',{'status':current_status_name})
                    current_status_record = current_music_service.execute_music_command('status',{'id':current_job_root.name})
                    self.assertEqual(current_status_record['metrics']['gpu_observations']['GPU-test']['process_peak_mib'],7123)
                    current_status_text = describe_audio_generation_status(current_status_record)
                    self.assertIn('현재 0 MiB', current_status_text)
                    self.assertIn('관측 피크 7123 MiB', current_status_text)
                    self.assertIn('작업자 및 자식 프로세스', current_status_text)
                    if current_status_name != 'running':
                        self.assertIsNone(current_status_record['estimate']['remaining'])
                write_record_atomically(current_job_root/'status.json',{'status':'queued'})
                current_status_record = current_music_service.execute_music_command('status',{'id':current_job_root.name})
                self.assertNotIn('metrics',current_status_record)
                self.assertNotIn('7123',describe_audio_generation_status(current_status_record))
                write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_names[1]})
                write_record_atomically(current_job_root/'status.json',{'status':'running'})
                current_status_record = current_music_service.execute_music_command('status',{'id':current_job_root.name})
                self.assertEqual(current_status_record['metrics']['gpu_observations']['GPU-test']['process_peak_mib'],6210)
                self.assertEqual(current_first_metrics_path.read_bytes(),current_first_metrics_bytes)

    def test_gui_and_cli_share_music_status_over_http(self):
        import contextlib
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import io
        import os
        import threading
        from tools.review.common.management_client import execute_remote_management_command
        from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_service_records = {}
            current_job_identifier = '2026-10-15_00-00-00-12345678'
            current_attempt_identifier = 'a'*32
            current_expected_metrics = {
                'stage':'inference','estimate':{'remaining':12,'basis':'격리 HTTP 검증'},
                'gpu_observations':{'GPU-test':{'process_current_mib':120,'process_peak_mib':7123,
                    'scope':'작업자 및 자식 프로세스','unit':'MiB','interval_seconds':5}},
            }
            for current_service_name in MUSIC_SERVICE_NAMES:
                current_music_service = MusicGenerationManager(current_service_name)
                current_music_service.job_storage_root = Path(current_temp_directory)/current_service_name
                current_job_root = current_music_service.job_storage_root/current_job_identifier
                current_attempt_root = current_job_root/'attempts'/current_attempt_identifier
                current_attempt_root.mkdir(parents=True)
                write_record_atomically(current_job_root/'status.json',{'status':'running'})
                write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_identifier})
                write_record_atomically(current_attempt_root/'metrics.json',current_expected_metrics)
                current_service_records[current_service_name] = current_music_service
            current_command_gateway = ManagementCommandGateway({current_service_name:current_music_service.handle_music_request for current_service_name,current_music_service in current_service_records.items()})
            class MusicAuditHttpHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    if not current_command_gateway.handle(self):
                        self.send_error(404)

                def log_message(self, current_format_text, *current_argument_values):
                    pass

            current_http_server = ThreadingHTTPServer(('127.0.0.1',0),MusicAuditHttpHandler)
            current_server_thread = threading.Thread(target=current_http_server.serve_forever,daemon=True)
            current_server_thread.start()
            current_server_address = f'http://127.0.0.1:{current_http_server.server_port}'
            try:
                with patch.dict(os.environ,{'SLIME_MANAGEMENT_GATEWAY_URL':current_server_address}):
                    for current_service_name in MUSIC_SERVICE_NAMES:
                        with self.subTest(service=current_service_name):
                            current_gui_status = execute_remote_management_command(current_service_name,'status',{'id':current_job_identifier})
                            current_cli_output = io.StringIO()
                            with contextlib.redirect_stdout(current_cli_output):
                                execute_gateway_arguments(current_service_name,['--server-url',current_server_address,'status',current_job_identifier])
                            current_cli_status = json.loads(current_cli_output.getvalue())
                            self.assertEqual(current_gui_status,current_cli_status)
                            self.assertEqual(current_gui_status['metrics'],current_expected_metrics)
                            self.assertEqual(current_gui_status['estimate'],current_expected_metrics['estimate'])
            finally:
                current_http_server.shutdown()
                current_http_server.server_close()
                current_server_thread.join(timeout=5)
                self.assertFalse(current_server_thread.is_alive())
