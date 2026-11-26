"""효과음 GUI·CLI·작업 기록 계약을 운영 GPU 작업 없이 검증한다."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from generators.music.contracts import build_music_request, load_music_defaults, verify_music_request, resolve_music_paths
from workflow.common.generation_records import write_record_atomically
from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, ManagementCommandGateway, execute_gateway_arguments, identify_management_command, resolve_management_command
from workflow.domains.music.generation import MusicGenerationManager
from workflow.tests.test_music_management_audit import MusicManagementAuditTests


class DashengAudioCleanupTests(MusicManagementAuditTests):
    """공용 삭제·종료 지표 계약을 새 서비스에서도 재사용한다."""
    def setUp(self):
        current_service_patch = patch('workflow.tests.test_music_management_audit.MUSIC_SERVICE_NAMES', ('sfx-dasheng-audiogen',))
        current_service_patch.start()
        self.addCleanup(current_service_patch.stop)

    def test_retired_model_cannot_return_from_cached_menu(self):
        self.assertNotIn('music-stable-audio', MANAGEMENT_SERVICE_COMMANDS)
        self.assertNotIn('sfx-stable-audio', MANAGEMENT_SERVICE_COMMANDS)
        self.assertIn('sfx-dasheng-audiogen', MANAGEMENT_SERVICE_COMMANDS)


class DashengAudioEffectsTests(unittest.TestCase):
    def test_offline_backup_prepare_is_explicit_and_persists_through_gateway(self):
        request = build_music_request('sfx-dasheng-audiogen', {'action': 'prepare', 'offline_backup': True})
        self.assertTrue(verify_music_request('sfx-dasheng-audiogen', request)['offline_backup'])
        job = self.current_service_instance.execute_music_command('prepare', {'action': 'prepare', 'offline_backup': True})
        saved = json.loads((self.current_service_instance.job_storage_root/job['id']/'request.json').read_text())
        self.assertTrue(saved['offline_backup'])
        for payload in ({'action': 'prepare', 'offline_backup': False}, {'action': 'prepare', 'offline_backup': 1},
                        {'action': 'generate', 'prompt': 'x', 'offline_backup': True}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                build_music_request('sfx-dasheng-audiogen', payload)
        with self.assertRaises(ValueError):
            build_music_request('music-heartmula', {'action': 'prepare', 'offline_backup': True})

    def test_offline_backup_cli_forwards_explicit_option(self):
        with patch('workflow.common.management_gateway.execute_management_command', return_value={'id': 'queued'}) as gateway, \
             patch('sys.stdout', new_callable=io.StringIO):
            execute_gateway_arguments('sfx-dasheng-audiogen', ['prepare', '--offline-backup'])
        self.assertEqual(gateway.call_args.args[:3], ('sfx-dasheng-audiogen', 'prepare', {'action': 'prepare', 'offline_backup': True}))

    def test_offline_backup_http_route_preserves_request(self):
        payload = {'action': 'prepare', 'offline_backup': True}
        method, path = resolve_management_command('sfx-dasheng-audiogen', 'prepare', payload)
        service, command, identified = identify_management_command(path, method, payload)
        self.assertEqual((service, command, identified), ('sfx-dasheng-audiogen', 'prepare', payload))
        job = self.current_service_instance.execute_music_command(command, identified)
        saved = json.loads((self.current_service_instance.job_storage_root/job['id']/'request.json').read_text())
        self.assertTrue(saved['offline_backup'])

    def test_offline_backup_failure_does_not_touch_prepare_or_cuda(self):
        from generators.music.worker import execute_music_worker
        job = self.current_service_instance.create_music_job({'action': 'prepare', 'offline_backup': True})
        job_root = self.current_service_instance.job_storage_root/job['id']
        model_root = self.current_test_root/'model'
        model_root.mkdir()
        record = model_root/'prepared.json'
        record.write_bytes(b'old record')
        metrics = Mock(current_run_state={})
        with patch('generators.music.worker.resolve_music_paths', return_value=(self.current_service_instance.job_storage_root, model_root, self.current_service_instance.runtime_python_path)), \
             patch('generators.music.worker.signal.signal'), patch('generators.music.worker.GenerationTelemetryRecorder', return_value=metrics), \
             patch('workflow.common.model_offline_audio_check.check_restored_audio', return_value={'matches': False}), \
             patch('generators.sound_effects.runtime.require_effects_cuda') as cuda, \
             patch('generators.sound_effects.runtime.prepare_effects_model') as prepare, \
             patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                execute_music_worker('sfx-dasheng-audiogen', job_root)
        cuda.assert_not_called()
        prepare.assert_not_called()
        self.assertEqual(record.read_bytes(), b'old record')
        self.assertEqual(json.loads((job_root/'status.json').read_text())['status'], 'failed')

    def test_offline_backup_success_prepares_with_local_only_hub_calls(self):
        from generators.music.worker import execute_music_worker
        from workflow.common.model_huggingface_download import tracked_snapshot_download
        from workflow.common.model_download_records import track_model_download
        job = self.current_service_instance.create_music_job({'action': 'prepare', 'offline_backup': True})
        job_root = self.current_service_instance.job_storage_root/job['id']
        model_root = self.current_test_root/'model'
        model_root.mkdir()
        metrics = Mock(current_run_state={})
        torch = Mock()
        torch.cuda.get_device_name.return_value = 'isolated GPU'
        calls = []
        def download(repo_id, *, local_dir=None, local_files_only=False, tqdm_class=None):
            calls.append(local_files_only)
            return local_dir
        def prepare(*args):
            tracked_snapshot_download('test', local_dir=str(model_root))
            return {'model_id': 'test'}
        def check(service, *, progress):
            self.assertEqual(service, 'sfx-dasheng-audiogen')
            progress('dasheng-audiogen', '스냅샷 해시 확인', 'config.json', 10, 20)
            return {'matches': True}
        with patch.dict('os.environ', {}, clear=False), \
             patch('generators.music.worker.resolve_music_paths', return_value=(self.current_service_instance.job_storage_root, model_root, self.current_service_instance.runtime_python_path)), \
             patch('generators.music.worker.signal.signal'), patch('generators.music.worker.GenerationTelemetryRecorder', return_value=metrics), \
             patch('workflow.common.model_offline_audio_check.check_restored_audio', side_effect=check), \
             patch('workflow.common.model_huggingface_download.track_model_download', lambda name: track_model_download(name, self.current_test_root/'downloads')), \
             patch('huggingface_hub.snapshot_download', download), \
             patch('generators.sound_effects.runtime.require_effects_cuda', return_value=torch), \
             patch('generators.sound_effects.runtime.prepare_effects_model', side_effect=prepare), \
             patch('sys.stdout', new_callable=io.StringIO) as output, patch('sys.stderr', new_callable=io.StringIO):
            execute_music_worker('sfx-dasheng-audiogen', job_root)
        self.assertIn('backup-verification model=dasheng-audiogen phase=스냅샷 해시 확인 path=config.json bytes=10/20', output.getvalue())
        self.assertEqual(calls, [True])
        self.assertEqual(json.loads((job_root/'status.json').read_text())['status'], 'completed')
        attempt = next((job_root/'attempts').iterdir())
        self.assertTrue(json.loads((attempt/'backup-verification.json').read_text())['matches'])

    def test_independent_components_keep_receipt_paths_and_reject_conflicts(self):
        from generators.sound_effects.runtime import resolve_effects_component, resolve_effects_file
        from workflow.common.audio_model_download import resolve_audio_receipt_file
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'.model/audio/dasheng-audiogen'
            old = root/'text-encoder'
            old.mkdir(parents=True)
            (old/'weights').write_bytes(b'model')
            new = root.parent.parent/'flan-t5-large'
            old.rename(new)
            self.assertEqual(resolve_effects_component(root, 'text-encoder'), new)
            self.assertEqual(resolve_effects_file(root, 'text-encoder/weights'), new/'weights')
            self.assertEqual(resolve_audio_receipt_file('sfx-dasheng-audiogen', root, 'text-encoder/weights'), new/'weights')
            with self.assertRaises(ValueError):
                resolve_effects_file(root, 'text-encoder/../weights')
            old.mkdir()
            with self.assertRaises(ValueError):
                resolve_effects_component(root, 'text-encoder')

    def test_checksum_cache_revalidates_changed_files(self):
        from generators.sound_effects.runtime import calculate_cached_checksum
        calculate_cached_checksum.cache_clear()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_file_path = Path(current_directory_name)/'weights'
            current_file_path.write_bytes(b'first')
            current_file_status = current_file_path.stat()
            current_first_digest = calculate_cached_checksum(current_file_path,current_file_status.st_size,current_file_status.st_mtime_ns,current_file_status.st_ctime_ns)
            current_file_path.write_bytes(b'changed')
            current_file_status = current_file_path.stat()
            current_next_digest = calculate_cached_checksum(current_file_path,current_file_status.st_size,current_file_status.st_mtime_ns,current_file_status.st_ctime_ns)
            self.assertNotEqual(current_first_digest,current_next_digest)

    def setUp(self):
        current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(current_temp_directory.cleanup)
        self.current_test_root = Path(current_temp_directory.name)
        self.current_service_instance = MusicGenerationManager('sfx-dasheng-audiogen')
        self.current_service_instance.job_storage_root = self.current_test_root/'jobs'
        self.current_service_instance.history_storage_root = self.current_test_root/'history'
        self.current_service_instance.runtime_python_path = self.current_test_root/'python'
        self.current_service_instance.runtime_python_path.touch()
        current_launch_patch = patch('workflow.domains.music.generation.launch_gpu_process')
        self.current_launch_mock = current_launch_patch.start()
        self.addCleanup(current_launch_patch.stop)

    def test_runtime_output_contract_and_seed(self):
        import contextlib
        import numpy
        from types import SimpleNamespace
        from generators.sound_effects.runtime import execute_effects_inference
        current_audio_array=numpy.full((1600,),0.1,dtype='float32')
        class AudioTensorStub:
            ndim=2
            shape=(1,1600)
            def __getitem__(self,current_item_index):
                return SimpleNamespace(float=lambda:SimpleNamespace(cpu=lambda:SimpleNamespace(numpy=lambda:current_audio_array)))
        current_tensor_stub=AudioTensorStub()
        current_torch_stub=Mock(Tensor=AudioTensorStub)
        current_torch_stub.cuda.max_memory_allocated.return_value=100
        current_torch_stub.cuda.max_memory_reserved.return_value=200
        current_torch_stub.inference_mode.return_value=contextlib.nullcontext()
        current_torch_stub.autocast.return_value=contextlib.nullcontext()
        current_model_stub=Mock()
        current_model_stub.generate.return_value=current_tensor_stub
        current_request_record=build_music_request('sfx-dasheng-audiogen',{'prompt':'A punch.','seed':17})
        current_output_path=self.current_test_root/'attempt'
        current_output_path.mkdir()
        with patch.dict('sys.modules',{'soundfile':SimpleNamespace(write=lambda current_path_value,*current_args_values,**current_kwargs_values:Path(current_path_value).write_bytes(b'isolated WAV'))}),patch('generators.sound_effects.runtime.resolve_music_paths',return_value=(self.current_test_root,self.current_test_root,self.current_test_root/'python')),patch('generators.sound_effects.runtime.configure_effects_cache'),patch('generators.sound_effects.runtime.validate_effects_model'),patch('generators.sound_effects.runtime.require_effects_cuda',return_value=current_torch_stub),patch('generators.sound_effects.runtime.load_effects_model',return_value=current_model_stub),patch.dict('os.environ',{},clear=False):
            current_result_record=execute_effects_inference('sfx-dasheng-audiogen',current_request_record,current_output_path,Mock(current_run_state={}))
            self.assertEqual(current_result_record['channels'],1)
            self.assertEqual(current_result_record['duration_seconds'],0.1)
            self.assertEqual(current_result_record['sample_rate'],16000)
            current_model_stub.generate.assert_called_once_with(prompts='<|caption|> A punch.',num_steps=25,guidance_scale=5.0)
            current_torch_stub.manual_seed.assert_called_once_with(17)
            current_tensor_stub.shape=(2,1600)
            with self.assertRaisesRegex(ValueError,'모노 Tensor'):
                execute_effects_inference('sfx-dasheng-audiogen',current_request_record,current_output_path,Mock(current_run_state={}))

    def test_effects_defaults_and_prompt_are_separate(self):
        current_request_record = build_music_request('sfx-dasheng-audiogen', {'prompt':' Wet  impact.\n'})
        self.assertEqual(current_request_record['model_id'], 'mispeech/Dasheng-AudioGen')
        self.assertEqual(current_request_record['final_prompt'], '<|caption|> Wet  impact.')
        self.assertEqual(current_request_record['final_prompt_words'], 3)
        self.assertEqual(current_request_record['prompt_sha256'], hashlib.sha256(b'<|caption|> Wet  impact.').hexdigest())
        self.assertEqual(verify_music_request('sfx-dasheng-audiogen', current_request_record), current_request_record)
        self.assertEqual(load_music_defaults()['duration_seconds'], 30)
        self.assertEqual(load_music_defaults('sfx-dasheng-audiogen')['duration_seconds'], None)
        current_request_record['final_prompt'] += ' tampered'
        with self.assertRaises(ValueError):
            verify_music_request('sfx-dasheng-audiogen', current_request_record)

    def test_invalid_inputs_never_launch_worker(self):
        for current_invalid_input in ({'model_id':'other'}, {'duration_seconds':0.49}, {'duration_seconds':31}, {'duration_seconds':True}, {'duration_seconds':float('nan')}, {'seed':True}, {'seed':1.5}, {'loop_request':'true'}, {'prompt':''}, {'action':'prepare'}):
            with self.subTest(payload=current_invalid_input), self.assertRaises(ValueError):
                self.current_service_instance.create_music_job({'prompt':'short impact', **current_invalid_input})
        self.current_launch_mock.assert_not_called()

    def test_cli_and_current_gui_restore_same_service_history(self):
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=lambda service,command,payload,current_server_address=None,**options:self.current_service_instance.execute_music_command(command,payload)),patch('sys.stdout',new_callable=io.StringIO):
            execute_gateway_arguments('sfx-dasheng-audiogen',['generate','--prompt','water splash','--seed','7','--detach'])
        record=self.current_service_instance.list_music_history()[0]
        self.assertIsNone(record['request']['duration_seconds'])
        app=build_management_application(SimpleHTTPRequestHandler,self.current_test_root,self.current_test_root/'source.json',8770,[])
        with patch('workflow.domains.music.generation.MusicGenerationManager',return_value=self.current_service_instance),TestClient(app) as client:
            response=client.get('/management/assistant/sfx-input/'+record['id'])
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['request'],{'prompt':'water splash','seed':7,'loop_request':False,'tag':''})
            self.assertEqual(client.get('/management/assistant/sfx-input/invalid').status_code,404)
        self.assertEqual(self.current_launch_mock.call_count,1)
        self.assertEqual(self.current_launch_mock.call_args.args[2],'sfx-dasheng-audiogen')

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
        from workflow.common.management_catalog import load_manager_page_records, resolve_management_page_path
        current_menu_path = self.current_test_root/'menu.json'
        current_menu_path.write_text(json.dumps({'pages':[{'id':'sfx-stable-audio','label':'폐기','path':'/management/frame/sfx-stable-audio/','category':'sound-management','description':'폐기'}]}))
        current_page_records = load_manager_page_records(current_menu_path)
        self.assertNotIn('sfx-stable-audio',[current_page_record['id'] for current_page_record in current_page_records])
        current_effects_record = next(current_page_record for current_page_record in current_page_records if current_page_record['id']=='sfx-dasheng-audiogen')
        self.assertEqual(current_effects_record['category'], 'sound-management')
        self.assertEqual(resolve_management_page_path(current_effects_record), '/management/frame/sfx-dasheng-audiogen/')

    def test_cuda_failure_has_no_cpu_fallback(self):
        from generators.sound_effects.runtime import require_effects_cuda
        current_torch_module = Mock()
        current_torch_module.cuda.is_available.return_value = False
        with patch.dict('sys.modules', {'torch':current_torch_module}), self.assertRaisesRegex(RuntimeError, 'CPU 추론'):
            require_effects_cuda()

    def test_nvidia_build_is_rejected_even_with_available_gpu(self):
        from generators.sound_effects.runtime import require_effects_cuda
        from generators.music.runtime import require_music_cuda
        current_torch_module = Mock()
        current_torch_module.version.hip = None
        current_torch_module.cuda.is_available.return_value = True
        with patch.dict('sys.modules', {'torch': current_torch_module}):
            for current_guard_function in (require_music_cuda, require_effects_cuda):
                with self.subTest(guard=current_guard_function.__name__), self.assertRaisesRegex(RuntimeError, 'ROCm'):
                    current_guard_function()

    def test_yaml_duplicate_and_unknown_fields_rejected(self):
        from generators.music import contracts
        current_default_text = contracts.SOUND_EFFECT_DEFAULTS.read_text()
        current_config_path = self.current_test_root/'defaults.yaml'
        for current_invalid_text in (current_default_text+'\nseed: 3\n', current_default_text+'\nunexpected: true\n'):
            current_config_path.write_text(current_invalid_text)
            with patch.object(contracts, 'SOUND_EFFECT_DEFAULTS', current_config_path), self.assertRaises(ValueError):
                load_music_defaults('sfx-dasheng-audiogen')

    def test_confirmation_cancel_and_duplicate_submission(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        result=subprocess.run(['node','--test',str(root/'workflow/tests/confirmation_gate.test.mjs')],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

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
                        execute_music_worker('sfx-dasheng-audiogen',current_job_root)
                else:
                    execute_music_worker('sfx-dasheng-audiogen',current_job_root)
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],current_status_name)
                current_metrics_recorder.finish_generation_telemetry.assert_called_with(current_status_name)
        self.assertEqual(len(list((current_job_root/'attempts').iterdir())),3)
        self.assertEqual(len(list((current_job_root/'attempts').glob('*/error.json'))),2)

    def test_worker_restores_previous_record_after_failed_refresh(self):
        from generators.music.worker import execute_music_worker
        job = self.current_service_instance.create_music_job({'action': 'prepare'})
        job_root = self.current_service_instance.resolve_music_job(job['id'])
        model_root = self.current_test_root/'model'
        model_root.mkdir()
        record = model_root/'prepared.json'
        record.write_text('{"old":true}')
        metrics = Mock(current_run_state={})
        torch = Mock()
        torch.cuda.get_device_name.return_value = 'isolated GPU'
        def fail_refresh(*args):
            record.unlink()
            raise RuntimeError('refresh failed')
        with patch('generators.music.worker.resolve_music_paths', return_value=(self.current_service_instance.job_storage_root, model_root, self.current_service_instance.runtime_python_path)), \
             patch('generators.music.worker.signal.signal'), \
             patch('generators.music.worker.GenerationTelemetryRecorder', return_value=metrics), \
             patch('generators.sound_effects.runtime.require_effects_cuda', return_value=torch), \
             patch('generators.sound_effects.runtime.prepare_effects_model', side_effect=fail_refresh), \
             patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaisesRegex(RuntimeError, 'refresh failed'):
                execute_music_worker('sfx-dasheng-audiogen', job_root)
        self.assertEqual(record.read_text(), '{"old":true}')
        self.assertEqual(json.loads((job_root/'status.json').read_text())['status'], 'failed')
