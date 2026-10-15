"""음악 GUI·CLI 계약, 이력·출력·CUDA 전용 실행의 격리 검증."""
import contextlib
import io
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
from generators.music.contracts import MUSIC_SERVICE_NAMES, build_music_request, validate_music_request, verify_music_request, load_music_defaults
from generators.music.runtime import reject_cpu_inference, reject_ace_cpu_decode
from tools.review.domains.music.generation import MusicGenerationManager
from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments, resolve_management_command
from tools.review.common.generation_records import write_record_atomically


class MusicGenerationTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle = tempfile.TemporaryDirectory()
        self.current_test_root = Path(self.current_temp_handle.name)
        self.current_music_service = MusicGenerationManager('music-ace-step')
        self.current_music_service.job_storage_root = self.current_test_root/'jobs'
        self.current_music_service.history_storage_root = self.current_test_root/'history'
        self.current_music_service.runtime_python_path = self.current_test_root/'python'
        self.current_music_service.runtime_python_path.touch()
        self.current_launcher_patch = patch('tools.review.domains.music.generation.launch_gpu_process')
        self.current_launcher_mock = self.current_launcher_patch.start()
        self.addCleanup(self.current_launcher_patch.stop)
        self.addCleanup(self.current_temp_handle.cleanup)

    def create_test_job(self,current_status_name='completed'):
        current_job_record = self.current_music_service.create_music_job({'prompt':'Soft flute village music','seed':7})
        current_job_root = self.current_music_service.resolve_music_job(current_job_record['id'])
        write_record_atomically(current_job_root/'status.json',{'status':current_status_name})
        return current_job_root

    def test_fixed_model_and_final_prompt_contract(self):
        for current_service_name in MUSIC_SERVICE_NAMES:
            current_request_record = build_music_request(current_service_name,{'prompt':'soft flute','loop_request':True})
            self.assertEqual(verify_music_request(current_service_name,current_request_record),current_request_record)
            self.assertGreater(current_request_record['final_prompt_words'],current_request_record['prompt_words'])
            self.assertEqual(resolve_management_command(current_service_name,'generate',{}),('POST','/'+current_service_name+'/jobs'))
            current_request_record['final_prompt'] += 'tampered'
            with self.assertRaisesRegex(ValueError,'해시'):
                verify_music_request(current_service_name,current_request_record)

    def test_invalid_input_rejected_before_queue(self):
        for current_invalid_payload in ({'prompt':''},{'prompt':'x','seed':True},{'prompt':'x','seed':1.5},{'prompt':'x','duration_seconds':float('nan')},{'prompt':'x','duration_seconds':121},{'prompt':'x','loop_request':'yes'},{'prompt':'x','model_id':'other'},{'action':'prepare','prompt':'x'}):
            with self.subTest(payload=current_invalid_payload), self.assertRaises(ValueError):
                self.current_music_service.create_music_job(current_invalid_payload)
        self.current_launcher_mock.assert_not_called()

    def test_minimax_native_diffusers_sample_rate(self):
        self.assertEqual(load_music_defaults()['profiles']['music-minimax']['sample_rate'],44100)
        with self.assertRaises(ValueError):
            validate_music_request('music-minimax',{'prompt':'x','duration_seconds':61})

    def test_shared_history_and_delete_removes_files(self):
        current_first_root = self.create_test_job()
        current_second_root = self.create_test_job()
        (current_first_root/'music.wav').write_bytes(b'preserved')
        self.assertEqual(len(self.current_music_service.list_music_history()),2)
        self.current_music_service.delete_music_history(current_first_root.name)
        self.assertEqual([current_record['id'] for current_record in self.current_music_service.list_music_history()],[current_second_root.name])
        self.assertFalse(current_first_root.exists())
        with self.assertRaises(ValueError):
            self.current_music_service.execute_music_command('resume',{'id':current_first_root.name})

    def test_delete_and_reset_reject_live_jobs(self):
        for current_status_name in ('running','queued'):
            current_job_root = self.create_test_job(current_status_name)
            with self.assertRaises(ValueError):
                self.current_music_service.delete_music_history(current_job_root.name)
            with self.assertRaises(ValueError):
                self.current_music_service.execute_music_command('history-reset',{'action':'reset'})
            self.assertFalse((current_job_root/'.history-deleted').exists())

    def test_resume_cancel_and_queue_use_common_executor(self):
        current_job_root = self.create_test_job('failed')
        current_launch_arguments = self.current_launcher_mock.call_args.args
        self.assertEqual(current_launch_arguments[2],'music-ace-step')
        self.assertIn('generators/music/worker.py',current_launch_arguments[0][2])
        with patch('tools.review.domains.music.generation.resume_gpu_generation',return_value={'status':'queued'}) as current_resume_mock:
            self.current_music_service.execute_music_command('resume',{'id':current_job_root.name})
            current_resume_mock.assert_called_once_with(current_job_root)
        with patch('tools.review.domains.music.generation.cancel_gpu_generation') as current_cancel_mock:
            self.current_music_service.execute_music_command('cancel',{'id':current_job_root.name})
            current_cancel_mock.assert_called_once_with(current_job_root)

    def test_paths_and_unknown_commands_fail(self):
        for current_invalid_identifier in ('../escape','bad-id',''):
            with self.assertRaises(ValueError):
                self.current_music_service.resolve_music_job(current_invalid_identifier)
        with self.assertRaises(ValueError):
            self.current_music_service.execute_music_command('model-status',{'model':'other'})
        current_job_root = self.create_test_job()
        current_link_path = current_job_root.parent/'2026-10-14_00-00-00-12345678'
        current_link_path.symlink_to(current_job_root,target_is_directory=True)
        with self.assertRaises(ValueError):
            self.current_music_service.resolve_music_job(current_link_path.name)

    def test_attempt_metrics_output_and_terminal_estimate(self):
        current_job_root = self.create_test_job('running')
        current_attempt_name = 'a'*32
        current_attempt_root = current_job_root/'attempts'/current_attempt_name
        current_attempt_root.mkdir(parents=True)
        write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_name})
        write_record_atomically(current_attempt_root/'metrics.json',{'stage':'inference','estimate':{'remaining':12},'gpu_observations':{'gpu':{'process_peak_mib':7000}}})
        self.assertEqual(self.current_music_service.read_music_status(current_job_root)['estimate']['remaining'],12)
        write_record_atomically(current_job_root/'status.json',{'status':'completed'})
        write_record_atomically(current_job_root/'result.json',{'attempt':current_attempt_name,'format':'wav'})
        current_status_record = self.current_music_service.read_music_status(current_job_root)
        self.assertIsNone(current_status_record['estimate']['remaining'])
        self.assertEqual(current_status_record['metrics']['gpu_observations']['gpu']['process_peak_mib'],7000)
        self.assertTrue(current_status_record['audio'].endswith('/music.wav'))
        write_record_atomically(current_job_root/'status.json',{'status':'queued'})
        current_status_record = self.current_music_service.read_music_status(current_job_root)
        self.assertNotIn('audio',current_status_record)
        self.assertNotIn('metrics',current_status_record)

    def test_cuda_guards_block_cpu_computation(self):
        current_cpu_module = Mock()
        current_cpu_module.parameters.return_value = [SimpleNamespace(device=SimpleNamespace(type='cpu'))]
        with self.assertRaisesRegex(RuntimeError,'CPU 모델'):
            reject_cpu_inference(current_cpu_module,())
        with self.assertRaisesRegex(RuntimeError,'CPU VAE'):
            reject_ace_cpu_decode(None)
        current_cpu_module.parameters.return_value = [SimpleNamespace(device=SimpleNamespace(type='cuda'))]
        reject_cpu_inference(current_cpu_module,())

    def test_cli_uses_same_request_schema(self):
        for current_service_name in MUSIC_SERVICE_NAMES:
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments(current_service_name,['generate','--prompt','soft flute','--duration-seconds','15','--seed','8','--loop-request','--detach'])
            current_command_arguments = current_command_mock.call_args.args
            self.assertEqual(current_command_arguments[:2],(current_service_name,'generate'))
            self.assertEqual(validate_music_request(current_service_name,current_command_arguments[2]),{'action':'generate','prompt':'soft flute','duration_seconds':15.0,'seed':8,'loop_request':True,'tag':''})

    def test_gateway_envelope_and_http_security(self):
        current_gateway_manager = ManagementCommandGateway({'music-ace-step':self.current_music_service.handle_music_request})
        current_request_bytes = json.dumps({'service':'music-ace-step','command':'generate','payload':{'prompt':'soft flute'}}).encode()
        current_http_handler = SimpleNamespace(command='POST',path='/management/command',server=SimpleNamespace(server_port=9999),headers={'Host':'127.0.0.1:9999','Origin':'http://127.0.0.1:9999','Content-Type':'application/json','Content-Length':str(len(current_request_bytes))},rfile=io.BytesIO(current_request_bytes),wfile=io.BytesIO(),send_response=Mock(),send_header=Mock(),end_headers=Mock())
        self.assertTrue(current_gateway_manager.handle(current_http_handler))
        current_http_handler.send_response.assert_called_once_with(200)
        self.assertEqual(json.loads(current_http_handler.wfile.getvalue())['status'],'queued')
        current_http_handler.headers['Host']='evil.example'
        current_http_handler.send_response.reset_mock()
        current_gateway_manager.handle(current_http_handler)
        current_http_handler.send_response.assert_called_once_with(400)

    def test_official_adapter_input_output_contracts(self):
        import numpy
        from generators.music.runtime import generate_ace_step, generate_minimax_music
        current_audio_array = numpy.zeros((100,2),dtype='float32')
        current_tensor_mock = MagicMock()
        current_tensor_mock.ndim = 3
        current_tensor_mock.shape = (1,2,100)
        current_tensor_mock.__getitem__.return_value.T.float.return_value.cpu.return_value.numpy.return_value = current_audio_array
        current_request_record = build_music_request('music-ace-step',{'prompt':'flute','seed':123})
        current_audio_path = self.current_test_root/'raw/music.wav'
        current_audio_path.parent.mkdir()
        current_audio_path.touch()
        current_api_module = SimpleNamespace(GenerationParams=Mock(),GenerationConfig=Mock(),generate_music=Mock(return_value=SimpleNamespace(success=True,audios=[{'path':str(current_audio_path)}],error=None)))
        with patch.dict('sys.modules',{'soundfile':SimpleNamespace(read=Mock(return_value=(current_audio_array,48000))),'acestep':SimpleNamespace(),'acestep.inference':current_api_module}), patch('generators.music.runtime.load_ace_step',return_value=(Mock(),Mock())):
            current_output_array,current_sample_rate = generate_ace_step(current_request_record,self.current_test_root,self.current_test_root,Mock())
        self.assertEqual(current_sample_rate,48000)
        self.assertTrue(current_api_module.GenerationParams.call_args.kwargs['instrumental'])
        self.assertFalse(current_api_module.GenerationConfig.call_args.kwargs['use_random_seed'])
        current_tensor_mock.ndim = 2
        current_tensor_mock.shape = (2,100)
        current_tensor_mock.T.float.return_value.cpu.return_value.numpy.return_value = current_audio_array
        # 공식 디코더는 output_type 생략 시 NumPy를 반환한다.
        def build_minimax_output(*current_argument_values,**current_keyword_values):
            return [current_tensor_mock] if current_keyword_values.get('output_type')=='pt' else [current_audio_array.T]
        current_pipeline_mock = Mock(sampling_rate=44100,side_effect=build_minimax_output)
        with patch.dict('sys.modules',{'torch':Mock()}),patch('generators.music.runtime.load_minimax_music',return_value=current_pipeline_mock):
            current_output_array,current_sample_rate = generate_minimax_music(current_request_record,self.current_test_root,self.current_test_root,Mock())
        self.assertEqual(current_sample_rate,44100)
        self.assertEqual(current_pipeline_mock.call_args.kwargs['lyrics'],'[Instrumental]')
        self.assertEqual(current_pipeline_mock.call_args.kwargs['audio_duration'],30)
        self.assertEqual(current_pipeline_mock.call_args.kwargs['output_type'],'pt')

    def test_worker_failure_and_cancellation_preserve_attempts(self):
        from generators.music.worker import execute_music_worker
        current_job_root = self.create_test_job()
        current_original_signals = {current_signal_number:signal.getsignal(current_signal_number) for current_signal_number in (signal.SIGTERM,signal.SIGINT)}
        try:
            for current_failure_error,current_expected_status in [(RuntimeError('CUDA OOM'),'failed'),(InterruptedError('cancel'),'cancelled')]:
                with patch('generators.music.worker.resolve_music_paths',return_value=(self.current_music_service.job_storage_root,self.current_test_root/'model',self.current_test_root/'python')), patch('generators.music.runtime.require_music_cuda',side_effect=current_failure_error), patch('tools.review.common.generation_telemetry.GenerationTelemetryRecorder.sample_generation_memory'), self.assertRaises(type(current_failure_error)):
                    execute_music_worker('music-ace-step',current_job_root)
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],current_expected_status)
                current_attempt_name = json.loads((current_job_root/'current-attempt.json').read_text())['id']
                current_attempt_root = current_job_root/'attempts'/current_attempt_name
                self.assertTrue((current_attempt_root/'error.json').exists())
                self.assertEqual(json.loads((current_attempt_root/'metrics.json').read_text())['status'],current_expected_status)
            self.assertEqual(len(list((current_job_root/'attempts').iterdir())),2)
        finally:
            for current_signal_number,current_signal_handler in current_original_signals.items():
                signal.signal(current_signal_number,current_signal_handler)

    def test_audio_history_has_output_indicator(self):
        from tools.review.common.gradio_history import render_history_selection_table
        current_job_root = self.create_test_job()
        current_history_record = self.current_music_service.list_music_history()[0]
        current_history_record['status']['audio']='/music-ace-step/jobs/'+current_job_root.name+'/music.wav'
        current_rendered_markup = render_history_selection_table([current_history_record])
        self.assertIn('WAV 오디오 결과',current_rendered_markup)
        self.assertIn('길이(초)',current_rendered_markup)
        self.assertNotIn('모션 길이',current_rendered_markup)

    def test_stage_and_final_memory_samples_are_recorded(self):
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        current_metrics_root = self.current_test_root/'metrics'
        current_metrics_root.mkdir()
        current_metrics_recorder = GenerationTelemetryRecorder(current_metrics_root,1,[])
        with patch.object(current_metrics_recorder,'sample_generation_memory') as current_memory_sample:
            current_metrics_recorder.start_generation_telemetry()
            current_metrics_recorder.update_generation_stage('inference')
            current_metrics_recorder.update_generation_stage('saving')
            current_metrics_recorder.finish_generation_telemetry('failed')
            self.assertGreaterEqual(current_memory_sample.call_count,3)
        self.assertEqual(json.loads((current_metrics_root/'metrics.json').read_text())['status'],'failed')

    def test_gui_two_models_have_shared_actions(self):
        from tools.review.ui.gradio.music_app import build_music_interface
        from tools.review.ui.gradio.management_menu_app import DEFAULT_PAGE_RECORDS, NATIVE_MANAGEMENT_APPLICATIONS
        for current_service_name in MUSIC_SERVICE_NAMES:
            current_interface_blocks = build_music_interface(current_service_name,'http://127.0.0.1:9999')
            current_component_values = [current_component['props'].get('value') for current_component in current_interface_blocks.config['components']]
            for current_button_label in ('우선 실행 · 대기 작업 선택','선택 이력 삭제','생성 재개','음악 생성 · 대기열 등록','모델 다운로드·준비'):
                self.assertIn(current_button_label,current_component_values)
            self.assertIn(current_service_name,NATIVE_MANAGEMENT_APPLICATIONS)
            self.assertEqual(next(current_page_record for current_page_record in DEFAULT_PAGE_RECORDS if current_page_record['id']==current_service_name)['category'],'music-generation')


if __name__=='__main__':
    unittest.main()
