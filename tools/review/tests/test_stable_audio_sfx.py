"""효과음 GUI·CLI·작업 기록 계약을 운영 GPU 작업 없이 검증한다."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from generators.music.contracts import build_music_request, load_music_defaults, verify_music_request, resolve_music_paths
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, ManagementCommandGateway, execute_gateway_arguments
from tools.review.domains.music.generation import MusicGenerationManager
from tools.review.tests.test_music_management_audit import MusicManagementAuditTests


class StableAudioCleanupTests(MusicManagementAuditTests):
    """공용 삭제·종료 지표 계약을 새 서비스에서도 재사용한다."""
    def setUp(self):
        current_service_patch = patch('tools.review.tests.test_music_management_audit.MUSIC_SERVICE_NAMES', ('sfx-stable-audio',))
        current_service_patch.start()
        self.addCleanup(current_service_patch.stop)

    def test_retired_model_cannot_return_from_cached_menu(self):
        self.assertNotIn('music-stable-audio', MANAGEMENT_SERVICE_COMMANDS)
        self.assertIn('sfx-stable-audio', MANAGEMENT_SERVICE_COMMANDS)


class StableAudioEffectsTests(unittest.TestCase):
    def setUp(self):
        current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(current_temp_directory.cleanup)
        self.current_test_root = Path(current_temp_directory.name)
        self.current_service_instance = MusicGenerationManager('sfx-stable-audio')
        self.current_service_instance.job_storage_root = self.current_test_root/'jobs'
        self.current_service_instance.history_storage_root = self.current_test_root/'history'
        self.current_service_instance.runtime_python_path = self.current_test_root/'python'
        self.current_service_instance.runtime_python_path.touch()
        current_launch_patch = patch('tools.review.domains.music.generation.launch_gpu_process')
        self.current_launch_mock = current_launch_patch.start()
        self.addCleanup(current_launch_patch.stop)

    def test_effects_defaults_and_prompt_are_separate(self):
        current_request_record = build_music_request('sfx-stable-audio', {'prompt':' Wet  impact.\n', 'duration_seconds':0.5})
        self.assertEqual(current_request_record['model_id'], 'stabilityai/stable-audio-3-small-sfx')
        self.assertEqual(current_request_record['final_prompt'], 'Wet  impact.')
        self.assertEqual(current_request_record['final_prompt_words'], 2)
        self.assertEqual(current_request_record['prompt_sha256'], hashlib.sha256(b'Wet  impact.').hexdigest())
        self.assertEqual(verify_music_request('sfx-stable-audio', current_request_record), current_request_record)
        self.assertEqual(load_music_defaults()['duration_seconds'], 30)
        self.assertEqual(load_music_defaults('sfx-stable-audio')['duration_seconds'], 3)
        current_request_record['final_prompt'] += ' tampered'
        with self.assertRaises(ValueError):
            verify_music_request('sfx-stable-audio', current_request_record)

    def test_invalid_inputs_never_launch_worker(self):
        for current_invalid_input in ({'model_id':'other'}, {'duration_seconds':0.49}, {'duration_seconds':31}, {'duration_seconds':True}, {'duration_seconds':float('nan')}, {'seed':True}, {'seed':1.5}, {'loop_request':'true'}, {'prompt':''}, {'action':'prepare'}):
            with self.subTest(payload=current_invalid_input), self.assertRaises(ValueError):
                self.current_service_instance.create_music_job({'prompt':'short impact', **current_invalid_input})
        self.current_launch_mock.assert_not_called()

    def test_cli_and_gui_use_same_service_history(self):
        from tools.review.ui.gradio import music_app
        with patch('tools.review.common.management_gateway.execute_management_command', side_effect=lambda current_service_name,current_command_name,current_payload_record,current_server_address=None,**current_options: self.current_service_instance.execute_music_command(current_command_name,current_payload_record)), patch('sys.stdout', new_callable=io.StringIO):
            execute_gateway_arguments('sfx-stable-audio',['generate','--prompt','water splash','--duration-seconds','1.5','--seed','7','--detach'])
        current_history_record = self.current_service_instance.list_music_history()[0]
        self.assertEqual(current_history_record['request']['duration_seconds'], 1.5)
        with patch.object(music_app, 'execute_remote_management_command', side_effect=lambda current_service_name,current_command_name,current_payload_record: self.current_service_instance.execute_music_command(current_command_name,current_payload_record)):
            current_interface_blocks = music_app.build_music_interface('sfx-stable-audio', 'http://127.0.0.1:8770')
            current_restore_callback = next(current_event.fn for current_event in current_interface_blocks.fns.values() if current_event.fn and current_event.fn.__name__=='restore_selected_inputs')
            current_restore_values = current_restore_callback(current_history_record['id'])
            self.assertEqual(tuple(current_restore_values[:5]), ('water splash',1.5,7,False,''))
        self.assertEqual(self.current_launch_mock.call_count, 1)
        self.assertEqual(self.current_launch_mock.call_args.args[2], 'sfx-stable-audio')

    def test_result_route_uses_effects_wav_and_rejects_escape(self):
        current_job_record = self.current_service_instance.create_music_job({'prompt':'short impact'})
        current_job_root = self.current_service_instance.resolve_music_job(current_job_record['id'])
        current_attempt_name = 'a'*32
        write_record_atomically(current_job_root/'status.json', {'status':'completed'})
        write_record_atomically(current_job_root/'result.json', {'format':'wav','attempt':current_attempt_name})
        current_status_record = self.current_service_instance.read_music_status(current_job_root)
        self.assertTrue(current_status_record['audio'].endswith('/'+current_attempt_name+'/sound.wav'))
        current_audio_path = current_job_root/'attempts'/current_attempt_name/'sound.wav'
        current_audio_path.parent.mkdir(parents=True)
        current_audio_path.write_bytes(b'RIFF isolated')
        current_http_handler = Mock(command='GET', path=current_status_record['audio'], headers={'Host':'127.0.0.1:8771'})
        current_http_handler.server.server_port = 8771
        current_http_handler.wfile = io.BytesIO()
        self.current_service_instance.handle_music_request(current_http_handler)
        current_http_handler.send_response.assert_called_with(200)
        self.assertEqual(current_http_handler.wfile.getvalue(), b'RIFF isolated')
        current_audio_path.unlink()
        current_external_path = self.current_test_root/'external.wav'
        current_external_path.write_bytes(b'protected')
        current_audio_path.symlink_to(current_external_path)
        current_http_handler.server.server_port = 8771
        current_http_handler.wfile = io.BytesIO()
        self.current_service_instance.handle_music_request(current_http_handler)
        current_http_handler.send_response.assert_called_with(400)
        self.assertNotIn(b'protected', current_http_handler.wfile.getvalue())

    def test_menu_composes_effects_and_keeps_retired_music_hidden(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records, resolve_management_page_path
        current_menu_path = self.current_test_root/'menu.json'
        current_menu_path.write_text(json.dumps({'pages':[]}))
        current_page_records = load_manager_page_records(current_menu_path)
        current_effects_record = next(current_page_record for current_page_record in current_page_records if current_page_record['id']=='sfx-stable-audio')
        self.assertEqual(current_effects_record['category'], 'sound-management')
        self.assertEqual(resolve_management_page_path(current_effects_record), '/management/frame/sfx-stable-audio/')

    def test_cuda_failure_has_no_cpu_fallback(self):
        from generators.sound_effects.runtime import require_effects_cuda
        current_torch_module = Mock()
        current_torch_module.cuda.is_available.return_value = False
        with patch.dict('sys.modules', {'torch':current_torch_module}), self.assertRaisesRegex(RuntimeError, 'CPU 추론'):
            require_effects_cuda()

    def test_yaml_duplicate_and_unknown_fields_rejected(self):
        from generators.music import contracts
        current_default_text = contracts.SOUND_EFFECT_DEFAULTS.read_text()
        current_config_path = self.current_test_root/'defaults.yaml'
        for current_invalid_text in (current_default_text+'\nseed: 3\n', current_default_text+'\nunexpected: true\n'):
            current_config_path.write_text(current_invalid_text)
            with patch.object(contracts, 'SOUND_EFFECT_DEFAULTS', current_config_path), self.assertRaises(ValueError):
                load_music_defaults('sfx-stable-audio')

    def test_confirmation_cancel_and_duplicate_submission(self):
        from tools.review.ui.gradio import music_app
        with patch.object(music_app, 'execute_remote_management_command', return_value={'id':'mock-job'}) as current_command_mock:
            current_interface_blocks = music_app.build_music_interface('sfx-stable-audio', 'http://127.0.0.1:8770')
            current_event_functions = [current_event.fn for current_event in current_interface_blocks.fns.values() if current_event.fn]
            current_prepare_callback = next(current_function_value for current_function_value in current_event_functions if current_function_value.__name__=='prepare_generation_confirmation')
            current_cancel_callback = next(current_function_value for current_function_value in current_event_functions if current_function_value.__name__=='cancel_generation_confirmation')
            current_execute_callback = next(current_function_value for current_function_value in current_event_functions if current_function_value.__name__=='execute_confirmed_generation')
            current_pending_record = current_prepare_callback('wet impact',3,42,False,'test')[0]
            current_cancel_callback(current_pending_record,'wet impact')
            with self.assertRaises(Exception):
                list(current_execute_callback(current_pending_record))
            current_command_mock.assert_not_called()
            current_pending_record = current_prepare_callback('wet impact',3,42,False,'test')[0]
            current_result_values = list(current_execute_callback(current_pending_record))
            self.assertEqual(current_result_values[0][0], 'mock-job')
            self.assertEqual(current_command_mock.call_args.args[:2], ('sfx-stable-audio','generate'))
            with self.assertRaises(Exception):
                list(current_execute_callback(current_pending_record))
            self.assertEqual(current_command_mock.call_count, 1)

    def test_worker_terminal_states_and_resume_keep_attempts(self):
        from generators.music.worker import execute_music_worker
        current_job_record = self.current_service_instance.create_music_job({'prompt':'wet impact'})
        current_job_root = self.current_service_instance.resolve_music_job(current_job_record['id'])
        current_metrics_recorder = Mock(current_run_state={})
        current_torch_module = Mock()
        current_torch_module.cuda.get_device_name.return_value = 'isolated GPU'
        with patch('generators.music.worker.resolve_music_paths',return_value=(self.current_service_instance.job_storage_root,self.current_test_root/'model',self.current_service_instance.runtime_python_path)), patch('generators.music.worker.signal.signal'), patch('generators.music.worker.GenerationTelemetryRecorder',return_value=current_metrics_recorder), patch('generators.sound_effects.runtime.require_effects_cuda',return_value=current_torch_module), patch('generators.sound_effects.runtime.prepare_effects_model',return_value={'model_id':'fixed'}), patch('generators.sound_effects.runtime.execute_effects_inference') as current_inference_mock, patch('sys.stdout',new_callable=io.StringIO), patch('sys.stderr',new_callable=io.StringIO):
            for current_exception_value,current_status_name in ((RuntimeError('CUDA out of memory'),'failed'),(InterruptedError('cancel'),'cancelled'),(None,'completed')):
                current_inference_mock.side_effect = current_exception_value
                current_inference_mock.return_value = {'format':'wav'}
                if current_exception_value:
                    with self.assertRaises(type(current_exception_value)):
                        execute_music_worker('sfx-stable-audio',current_job_root)
                else:
                    execute_music_worker('sfx-stable-audio',current_job_root)
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],current_status_name)
                current_metrics_recorder.finish_generation_telemetry.assert_called_with(current_status_name)
        self.assertEqual(len(list((current_job_root/'attempts').iterdir())),3)
        self.assertEqual(len(list((current_job_root/'attempts').glob('*/error.json'))),2)
