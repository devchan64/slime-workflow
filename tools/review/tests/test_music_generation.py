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
from generators.music.runtime import reject_cpu_inference
from tools.review.domains.music.generation import MusicGenerationManager
from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments, resolve_management_command
from tools.review.common.generation_records import write_record_atomically


class MusicGenerationTests(unittest.TestCase):
    def test_saved_music_inputs_restore_without_execution(self):
        from tools.review.ui.gradio import music_app
        for current_service_name in MUSIC_SERVICE_NAMES:
            with self.subTest(service=current_service_name):
                current_request_record=build_music_request(current_service_name,{'prompt':'soft flute','duration_seconds':15,'seed':77,'loop_request':True,'tag':'복원 검증'})
                current_history_record={'id':'isolated-music','request':current_request_record,'status':'completed'}
                with patch.object(music_app,'execute_remote_management_command',return_value={'records':[current_history_record]}) as current_command_mock:
                    current_interface_blocks=music_app.build_music_interface(current_service_name,'http://127.0.0.1:8798')
                    current_restore_callback=next(current_event.fn for current_event in current_interface_blocks.fns.values() if current_event.fn and current_event.fn.__name__=='restore_selected_inputs')
                    current_restored_values=current_restore_callback('isolated-music')
                    self.assertEqual(tuple(current_restored_values[:6]),('soft flute',375,77,True,'복원 검증','isolated-music'))
                    self.assertEqual(tuple(current_restored_values[7:9]),('[Instrumental]',True))
                    current_history_record['request'] = build_music_request(current_service_name,{'prompt':'soft flute','lyrics':'[verse] Morning light','duration_seconds':15})
                    current_new_restore = current_restore_callback('isolated-music')
                    self.assertEqual(tuple(current_new_restore[7:9]),('[verse] Morning light',False))
                    for current_invalid_fields in ({'duration_seconds': -1}, {'seed': True}, {'loop_request': 'yes'}, {'prompt': ''}):
                        current_history_record['request'] = {**current_request_record, **current_invalid_fields}
                        current_rejected_values = current_restore_callback('isolated-music')
                        self.assertTrue(all(current_value == {'__type__': 'update'} for current_value in current_rejected_values[:6]))
                        self.assertIn('입력값을 불러오지 못했습니다', current_rejected_values[-1])
                    current_history_record['request']={'action':'prepare'}
                    current_rejected_values=current_restore_callback('isolated-music')
                    self.assertTrue(all(current_value=={'__type__':'update'} for current_value in current_rejected_values[:6]))
                    self.assertIn('모델 준비 이력에는 음악 입력이 없습니다',current_rejected_values[-1])
                    self.assertTrue(all(current_call.args[1]=='history' for current_call in current_command_mock.call_args_list))

    def test_minimax_token_limits_preserve_runtime_frames(self):
        for current_token_count in (125,126,751,1499,1500,1501,2999,3000):
            current_saved_request = build_music_request('music-minimax',{'prompt':'soft flute','max_new_tokens':current_token_count})
            self.assertEqual(int(current_saved_request['duration_seconds']*25),current_token_count)
            self.assertEqual(verify_music_request('music-minimax',current_saved_request),current_saved_request)
        for current_invalid_value in (124,3001,True,750.5,None,'750'):
            with self.assertRaises(ValueError):
                validate_music_request('music-minimax',{'prompt':'soft flute','max_new_tokens':current_invalid_value})
        with self.assertRaises(ValueError):
            validate_music_request('music-minimax',{'prompt':'soft flute','max_new_tokens':750,'duration_seconds':30})
        with self.assertRaises(ValueError):
            validate_music_request('sfx-dasheng-audiogen',{'prompt':'punch','max_new_tokens':750})

    def test_minimax_gui_tokens_reach_shared_gateway(self):
        from tools.review.ui.gradio import music_app
        with patch.object(music_app,'execute_remote_management_command',return_value={'id':'test-only'}) as current_command_mock, patch.object(music_app,'bind_gpu_generation_confirmation') as current_bind_mock:
            current_interface_blocks = music_app.build_music_interface('music-minimax','http://127.0.0.1:8798')
            current_start_callback = next(current_call.args[1] for current_call in current_bind_mock.call_args_list if current_call.args[1].__name__=='start_music_generation')
            current_start_callback('soft flute',751,42,False,'test')
            self.assertEqual(current_command_mock.call_args.args[2]['max_new_tokens'],751)
            self.assertNotIn('duration_seconds',current_command_mock.call_args.args[2])
            current_start_callback('acoustic pop',1500,7,False,'example',0,'[verse] Morning light',False)
            self.assertEqual(current_command_mock.call_args.args[2]['lyrics'],'[verse] Morning light')

    def setUp(self):
        self.current_temp_handle = tempfile.TemporaryDirectory()
        self.current_test_root = Path(self.current_temp_handle.name)
        self.current_music_service = MusicGenerationManager('music-minimax')
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
            validate_music_request('music-minimax',{'prompt':'x','duration_seconds':121})

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
        self.assertEqual(current_launch_arguments[2],'music-minimax')
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
        current_cpu_module.parameters.return_value = [SimpleNamespace(device=SimpleNamespace(type='cuda'))]
        reject_cpu_inference(current_cpu_module,())

    def test_cli_uses_same_request_schema(self):
        for current_service_name in MUSIC_SERVICE_NAMES:
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments(current_service_name,['generate','--prompt','soft flute','--duration-seconds','15','--seed','8','--loop-request','--detach'])
            current_command_arguments = current_command_mock.call_args.args
            self.assertEqual(current_command_arguments[:2],(current_service_name,'generate'))
            self.assertEqual(validate_music_request(current_service_name,current_command_arguments[2]),{'action':'generate','prompt':'soft flute','duration_seconds':15.0,'seed':8,'loop_request':True,'tag':''})

    def test_cli_token_limit_uses_shared_normalization(self):
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('music-minimax',['generate','--prompt','soft flute','--max-new-tokens','751','--detach'])
        current_command_payload = current_command_mock.call_args.args[2]
        self.assertEqual(current_command_payload['max_new_tokens'],751)
        self.assertNotIn('duration_seconds',current_command_payload)
        self.assertEqual(int(validate_music_request('music-minimax',current_command_payload)['duration_seconds']*25),751)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_arguments('music-minimax',['generate','--prompt','soft flute','--max-new-tokens','750','--duration-seconds','30','--detach'])
        current_job_record = self.current_music_service.execute_music_command('generate',{'prompt':'soft flute','max_new_tokens':751})
        current_saved_request = json.loads((self.current_music_service.job_storage_root/current_job_record['id']/'request.json').read_text())
        self.assertEqual(int(current_saved_request['duration_seconds']*25),751)

    def test_gateway_envelope_and_http_security(self):
        current_gateway_manager = ManagementCommandGateway({'music-minimax':self.current_music_service.handle_music_request})
        current_request_bytes = json.dumps({'service':'music-minimax','command':'generate','payload':{'prompt':'soft flute'}}).encode()
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
        from generators.music.runtime import generate_minimax_music
        current_audio_array = numpy.zeros((100,2),dtype='float32')
        current_tensor_mock = MagicMock()
        current_tensor_mock.ndim = 3
        current_tensor_mock.shape = (1,2,100)
        current_tensor_mock.__getitem__.return_value.T.float.return_value.cpu.return_value.numpy.return_value = current_audio_array
        current_tensor_mock.ndim = 2
        current_tensor_mock.shape = (2,100)
        current_tensor_mock.T.float.return_value.cpu.return_value.numpy.return_value = current_audio_array
        # 공식 디코더는 output_type 생략 시 NumPy를 반환한다.
        def build_minimax_output(*current_argument_values,**current_keyword_values):
            return [current_tensor_mock] if current_keyword_values.get('output_type')=='pt' else [current_audio_array.T]
        current_request_record = build_music_request('music-minimax',{'prompt':'flute','seed':123})
        current_pipeline_mock = Mock(sampling_rate=44100,side_effect=build_minimax_output)
        with patch.dict('sys.modules',{'torch':Mock(),'diffusers.modular_pipelines.minimax_music3':SimpleNamespace(encoders=Mock())}),patch('generators.music.runtime.record_minimax_termination',return_value=contextlib.nullcontext()),patch('generators.music.runtime.load_minimax_music',return_value=current_pipeline_mock):
            current_output_array,current_sample_rate = generate_minimax_music(current_request_record,self.current_test_root,self.current_test_root,Mock())
        self.assertEqual(current_sample_rate,44100)
        self.assertEqual(current_pipeline_mock.call_args.kwargs['lyrics'],'[Instrumental]')
        self.assertEqual(current_pipeline_mock.call_args.kwargs['audio_duration'],30)
        self.assertEqual(current_pipeline_mock.call_args.kwargs['output_type'],'pt')

    def test_structured_minimax_inputs(self):
        from generators.music.contracts import verify_music_request
        from generators.music.structured_inputs import generate_structured_minimax, select_structured_adapter
        from generators.music import runtime as current_runtime_module
        current_request_record = build_music_request('music-minimax',{'prompt':'Genre: acoustic pop. Vocals: soft female lead.','lyrics':'[verse]\nMorning light','duration_seconds':60,'seed':7,'loop_request':False})
        self.assertEqual(current_request_record['final_prompt'],current_request_record['prompt'])
        self.assertEqual(verify_music_request('music-minimax',current_request_record),current_request_record)
        current_tensor_mock = MagicMock(ndim=2,shape=(2,100))
        current_pipeline_mock = Mock(sampling_rate=44100,return_value=[current_tensor_mock])
        current_torch_mock = Mock()
        with patch.dict('sys.modules',{'torch':current_torch_mock,'diffusers.modular_pipelines.minimax_music3':SimpleNamespace(encoders=Mock())}),patch('generators.music.runtime.record_minimax_termination',return_value=contextlib.nullcontext()),patch('generators.music.runtime.load_minimax_music',return_value=current_pipeline_mock):
            generate_structured_minimax(current_request_record,self.current_test_root,self.current_test_root,Mock())
        self.assertEqual(current_pipeline_mock.call_args.kwargs['lyrics'],'[verse]\nMorning light')
        self.assertEqual(current_pipeline_mock.call_args.kwargs['prompt'],current_request_record['prompt'])
        self.assertEqual(current_pipeline_mock.call_args.kwargs['audio_duration'],60)
        current_torch_mock.Generator.assert_called_once_with('cuda')
        current_torch_mock.Generator.return_value.manual_seed.assert_called_once_with(7)
        current_original_adapter = current_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax']
        with self.assertRaises(RuntimeError):
            with select_structured_adapter(current_request_record):
                self.assertIs(current_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax'],generate_structured_minimax)
                raise RuntimeError('격리 검증')
        self.assertIs(current_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax'],current_original_adapter)
        for current_invalid_lyrics in ('',None,42,'bad\x00text'):
            with self.assertRaises(ValueError):
                build_music_request('music-minimax',{'prompt':'flute','lyrics':current_invalid_lyrics})
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('music-minimax',['generate','--prompt','acoustic pop','--lyrics','[verse] Morning light','--duration-seconds','60','--seed','7','--no-loop-request','--detach'])
        current_cli_request = build_music_request('music-minimax',current_command_mock.call_args.args[2])
        self.assertEqual(current_cli_request['final_prompt'],'acoustic pop')
        self.assertEqual(current_cli_request['lyrics'],'[verse] Morning light')

    def test_minimax_termination_observation(self):
        from generators.music.runtime import record_minimax_termination
        current_pipeline_stub = SimpleNamespace(frame_rate=25,language_model=SimpleNamespace(config=SimpleNamespace(vocab_size=160000)))
        for current_case_name,current_token_values,current_expected_reason in (
            ('early',[10,11,151670],'audio_end_token'),
            ('limit',[10,11,12],'max_frames'),
            ('empty',[151670],'audio_end_token'),
            ('failure',[10],'not_observed')):
            with self.subTest(case=current_case_name):
                current_sampler_mock = Mock(side_effect=[SimpleNamespace(item=lambda current_token_value=current_token_value:current_token_value) for current_token_value in current_token_values])
                current_encoder_stub = SimpleNamespace(_sample_top_k=current_sampler_mock,_AUDIO_END_TOKEN_ID=151670,_MAX_AUDIO_FRAMES=9000)
                current_output_capture = io.StringIO()
                with contextlib.redirect_stdout(current_output_capture):
                    try:
                        with record_minimax_termination(current_encoder_stub,current_pipeline_stub,0.08,self.current_test_root):
                            for current_token_value in current_token_values:
                                current_returned_token = current_encoder_stub._sample_top_k(SimpleNamespace(shape=(1,160000)),None)
                                self.assertEqual(current_returned_token.item(),current_token_value)
                            if current_case_name == 'failure':
                                raise RuntimeError('검증용 디코더 실패')
                    except RuntimeError:
                        if current_case_name != 'failure':
                            raise
                current_trace_record = json.loads((self.current_test_root/'minimax-termination.json').read_text())
                self.assertEqual(current_trace_record['termination_reason'],current_expected_reason)
                self.assertEqual(current_trace_record['end_token_detected'],current_expected_reason=='audio_end_token')
                self.assertEqual(current_trace_record['sampled_audio_frames'],{'early':1,'limit':2,'empty':0,'failure':0}[current_case_name])
                self.assertEqual(current_trace_record['pipeline_status'],'failed' if current_case_name=='failure' else 'completed')
                self.assertIs(current_encoder_stub._sample_top_k,current_sampler_mock)
                self.assertEqual(current_sampler_mock.call_count,len(current_token_values))
                self.assertIn(current_expected_reason,current_output_capture.getvalue())
        current_sampler_mock = Mock(return_value=SimpleNamespace(item=lambda:151670))
        current_encoder_stub._sample_top_k = current_sampler_mock
        with contextlib.redirect_stdout(io.StringIO()),record_minimax_termination(current_encoder_stub,current_pipeline_stub,30,self.current_test_root) as current_trace_record:
            current_encoder_stub._sample_top_k(SimpleNamespace(shape=(1,1024)),None)
        self.assertFalse(current_trace_record['end_token_detected'])
        self.assertEqual(current_trace_record['semantic_samples'],0)

    def test_worker_failure_and_cancellation_preserve_attempts(self):
        from generators.music.worker import execute_music_worker
        current_job_root = self.create_test_job()
        current_original_signals = {current_signal_number:signal.getsignal(current_signal_number) for current_signal_number in (signal.SIGTERM,signal.SIGINT)}
        try:
            for current_failure_error,current_expected_status in [(RuntimeError('CUDA OOM'),'failed'),(InterruptedError('cancel'),'cancelled')]:
                with patch('generators.music.worker.resolve_music_paths',return_value=(self.current_music_service.job_storage_root,self.current_test_root/'model',self.current_test_root/'python')), patch('generators.music.runtime.require_music_cuda',side_effect=current_failure_error), patch('tools.review.common.generation_telemetry.GenerationTelemetryRecorder.sample_generation_memory'), self.assertRaises(type(current_failure_error)):
                    execute_music_worker('music-minimax',current_job_root)
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
        current_history_record['status']['audio']='/music-minimax/jobs/'+current_job_root.name+'/music.wav'
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
            for current_button_label in ('우선 실행 · 대기 작업 선택','선택 이력 삭제','생성 재개','대기열에 추가','모델 다운로드·준비'):
                self.assertIn(current_button_label,current_component_values)
            self.assertIn(current_service_name,NATIVE_MANAGEMENT_APPLICATIONS)
            self.assertEqual(next(current_page_record for current_page_record in DEFAULT_PAGE_RECORDS if current_page_record['id']==current_service_name)['category'],'sound-management')


if __name__=='__main__':
    unittest.main()
