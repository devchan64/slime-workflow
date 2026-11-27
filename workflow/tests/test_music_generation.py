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
from workflow.domains.music.generation import MusicGenerationManager
from workflow.common.management_gateway import ManagementCommandGateway, execute_gateway_arguments, resolve_management_command
from workflow.common.generation_records import write_record_atomically


class MusicGenerationTests(unittest.TestCase):
    def test_audio_service_cleanup_keeps_other_service_with_same_id(self):
        from itertools import product
        for service,action in product(('music-heartmula','sfx-dasheng-audiogen'),('selected','all')):
            with self.subTest(service=service,action=action), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); job_id='2026-11-27_00-00-00-1234abcd'
                music=MusicGenerationManager('music-heartmula'); effect=MusicGenerationManager('sfx-dasheng-audiogen')
                for manager in (music,effect):
                    manager.job_storage_root=root/manager.current_service_name/'jobs'
                    manager.history_storage_root=root/manager.current_service_name/'history'
                    job=manager.job_storage_root/job_id; job.mkdir(parents=True)
                    (job/'status.json').write_text('{"status":"completed"}')
                    (job/manager.audio_output_filename).write_bytes(b'audio')
                    manager.history_storage_root.mkdir(parents=True)
                    (manager.history_storage_root/(job_id+'.json')).write_text(json.dumps({'id':job_id}))
                target,other=(music,effect) if service=='music-heartmula' else (effect,music)
                if action=='selected': target.delete_music_history(job_id)
                else:
                    preview=target.execute_music_command('history-reset-preview',{})
                    target.execute_music_command('history-reset',{'action':'reset','expected_jobs':preview['jobs']})
                self.assertFalse((target.job_storage_root/job_id).exists())
                self.assertFalse((target.history_storage_root/(job_id+'.json')).exists())
                self.assertTrue((other.job_storage_root/job_id/other.audio_output_filename).is_file())
                self.assertTrue((other.history_storage_root/(job_id+'.json')).is_file())
    def test_heartmula_default_limit_and_examples(self):
        from generators.music.examples import load_music_examples
        current_request_record = validate_music_request('music-heartmula', {'prompt':'piano','lyrics':'[Verse]\nHome again'})
        self.assertEqual(current_request_record['duration_seconds'], 300)
        with self.assertRaises(ValueError):
            validate_music_request('music-heartmula', {'prompt':'piano','lyrics':'Home','duration_seconds':301})
        current_example_records = load_music_examples('music-heartmula')
        self.assertEqual(len(current_example_records), 31)
        self.assertEqual(len({current_example_record['request']['prompt'] for current_example_record in current_example_records}), 31)
        for current_example_record in current_example_records:
            self.assertEqual(current_example_record['request']['duration_seconds'], 300)
            current_song_lines = current_example_record['request']['lyrics'].splitlines()
            current_section_positions = [current_song_lines.index('[Chorus]'),current_song_lines.index('[Outro]')]
            self.assertEqual(current_song_lines[0], '[Verse]')
            self.assertGreater(current_section_positions[0], 1)
            self.assertGreater(current_section_positions[1], current_section_positions[0] + 1)
            self.assertGreaterEqual(len(current_song_lines) - current_section_positions[1] - 1, 2)


    def test_example_endpoint_preserves_all_records(self):
        from http.server import SimpleHTTPRequestHandler
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        from generators.music.examples import load_music_examples
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:response=client.get('/management/assistant/heartmula-examples')
        self.assertEqual(response.status_code,200)
        records=response.json()
        self.assertEqual(records,load_music_examples('music-heartmula'))
        self.assertEqual(len({item['id'] for item in records}),len(records))
        self.assertTrue(all(item['request']['prompt'] and isinstance(item['request']['lyrics'],str) for item in records))

    def test_heartmula_empty_lyrics_experiment(self):
        current_request_record = validate_music_request('music-heartmula', {'prompt':'piano,happy','lyrics':''})
        self.assertEqual(current_request_record['lyrics'], '')

    def test_heartmula_explicit_lyrics_required(self):
        with self.assertRaisesRegex(ValueError, '직접 입력'):
            validate_music_request('music-heartmula', {'prompt':'piano'})
        current_request_record = validate_music_request('music-heartmula', {'prompt':'piano','lyrics':'[Intro]\n[Outro]'})
        self.assertEqual(current_request_record['lyrics'], '[Intro]\n[Outro]')
        self.assertNotIn('instrumental', load_music_defaults('music-heartmula')['prompt'])

    def test_saved_music_inputs_restore_without_execution(self):
        from http.server import SimpleHTTPRequestHandler
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/'job';job.mkdir();path=job/'request.json'
            request=build_music_request('music-heartmula',{'prompt':'piano,soft','lyrics':'[verse] Morning light','duration_seconds':15,'seed':77,'loop_request':False,'tag':'복원 검증'})
            write_record_atomically(path,request)
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('workflow.domains.music.generation.MusicGenerationManager') as manager, TestClient(app) as client:
                manager.return_value.resolve_music_job.return_value=job
                original=path.read_bytes()
                response=client.get('/management/assistant/heartmula-input/isolated-music')
                self.assertEqual(response.status_code,200,response.text)
                restored=response.json()['request']
                self.assertEqual((restored['prompt'],restored['lyrics'],restored['duration_seconds'],restored['seed'],restored['tag']),('piano,soft','[verse] Morning light',15,77,'복원 검증'))
                self.assertEqual(path.read_bytes(),original)
                for invalid in ({'duration_seconds':-1},{'seed':True},{'loop_request':'yes'},{'prompt':''},{'action':'prepare'}):
                    with self.subTest(invalid=invalid):
                        write_record_atomically(path,{**request,**invalid})
                        self.assertEqual(client.get('/management/assistant/heartmula-input/isolated-music').status_code,422)
                manager.return_value.start_music_generation.assert_not_called()

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

    def test_minimax_generation_is_retired_but_history_remains(self):
        from generators.music.service_constants import inspect_retired_audio_rejection
        self.assertIn('폐기',inspect_retired_audio_rejection('music-minimax','generate'))
        self.assertIsNone(inspect_retired_audio_rejection('music-minimax','history'))

    def setUp(self):
        self.current_temp_handle = tempfile.TemporaryDirectory()
        self.current_test_root = Path(self.current_temp_handle.name)
        self.current_music_service = MusicGenerationManager('music-minimax')
        self.current_music_service.job_storage_root = self.current_test_root/'jobs'
        self.current_music_service.history_storage_root = self.current_test_root/'history'
        self.current_music_service.runtime_python_path = self.current_test_root/'python'
        self.current_music_service.runtime_python_path.touch()
        self.current_launcher_patch = patch('workflow.domains.music.generation.launch_gpu_process')
        self.current_launcher_mock = self.current_launcher_patch.start()
        self.addCleanup(self.current_launcher_patch.stop)
        self.addCleanup(self.current_temp_handle.cleanup)

    def create_test_job(self,current_status_name='completed'):
        import uuid
        current_job_identifier = '2026-10-24_00-00-00-'+uuid.uuid4().hex[:8]
        current_job_root = self.current_music_service.job_storage_root/current_job_identifier
        current_job_root.mkdir(parents=True)
        self.current_music_service.history_storage_root.mkdir(parents=True,exist_ok=True)
        current_request_record = build_music_request('music-minimax',{'prompt':'Soft flute village music','seed':7})
        write_record_atomically(current_job_root/'request.json',current_request_record)
        write_record_atomically(current_job_root/'status.json',{'status':current_status_name})
        write_record_atomically(self.current_music_service.history_storage_root/(current_job_identifier+'.json'),{'id':current_job_identifier,'created_at':'2026-10-24T00:00:00+09:00','request':current_request_record,'path':str(current_job_root)})
        return current_job_root

    def test_fixed_model_and_final_prompt_contract(self):
        for current_service_name in ('music-minimax',):
            current_request_record = build_music_request(current_service_name,{'prompt':'soft flute','loop_request':True})
            self.assertEqual(verify_music_request(current_service_name,current_request_record),current_request_record)
            self.assertGreater(current_request_record['final_prompt_words'],current_request_record['prompt_words'])
            self.assertEqual(resolve_management_command(current_service_name,'generate',{}),('POST','/'+current_service_name+'/jobs'))
            current_request_record['final_prompt'] += 'tampered'
            with self.assertRaisesRegex(ValueError,'해시'):
                verify_music_request(current_service_name,current_request_record)

    def test_damaged_music_job_blocks_preparation_before_gpu_queue(self):
        self.current_music_service.current_service_name='music-heartmula'
        current_job_root=self.create_test_job('completed')
        (current_job_root/'status.json').write_text('{')
        with patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'):
            with self.assertRaisesRegex(ValueError,'작업 기록을 확인할 수 없습니다'):
                self.current_music_service.create_music_job({'action':'prepare'})
        self.current_launcher_mock.assert_not_called()

    def test_hidden_active_preparation_blocks_duplicate_before_gpu_queue(self):
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            for current_status_name in ('queued','running','paused'):
                with self.subTest(current_service_name=current_service_name,current_status_name=current_status_name):
                    self.current_music_service.current_service_name=current_service_name
                    current_job_root=self.create_test_job(current_status_name)
                    write_record_atomically(current_job_root/'request.json',build_music_request(current_service_name,{'action':'prepare'}))
                    (current_job_root/'.history-deleted').touch()
                    with patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'):
                        with self.assertRaisesRegex(ValueError,'이미 대기 중이거나 실행 중'):
                            self.current_music_service.create_music_job({'action':'prepare'})
                    self.current_launcher_mock.assert_not_called()
                    import shutil
                    shutil.rmtree(current_job_root)

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
        with patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
            with self.assertRaisesRegex(ValueError,'폐기'):
                self.current_music_service.execute_music_command('resume',{'id':current_job_root.name})
            current_resume_mock.assert_not_called()
        with patch('workflow.domains.music.generation.cancel_gpu_generation') as current_cancel_mock:
            self.current_music_service.execute_music_command('cancel',{'id':current_job_root.name})
            current_cancel_mock.assert_called_once_with(current_job_root)

    def test_resume_rejects_active_model_download_without_dispatch(self):
        current_job_root=self.create_test_job('failed')
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            self.current_music_service.current_service_name=current_service_name
            for current_resume_payload in ({'id':current_job_root.name},{'id':current_job_root.name,'expected_resume_fingerprint':'a'*64}):
                with self.subTest(current_service_name=current_service_name,current_resume_payload=current_resume_payload), patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='running'), patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
                    with self.assertRaisesRegex(ValueError,'다운로드가 진행 중'):
                        self.current_music_service.execute_music_command('resume',current_resume_payload)
                    current_resume_mock.assert_not_called()

    def test_music_preparation_check_does_not_treat_access_error_as_empty(self):
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'iterdir',side_effect=PermissionError('unreadable')):
            with self.assertRaises(PermissionError):
                self.current_music_service.ensure_no_active_music_preparation()
        with patch.object(Path,'iterdir',side_effect=FileNotFoundError('missing')):
            self.current_music_service.ensure_no_active_music_preparation()

    def test_unreadable_job_store_blocks_preparation_and_resume_review(self):
        self.current_music_service.current_service_name='music-heartmula'
        current_job_root=self.create_test_job('failed')
        write_record_atomically(current_job_root/'request.json',build_music_request('music-heartmula',{'action':'prepare'}))
        current_preview_record={'status':'failed','expected_resume_fingerprint':'a'*64}
        with patch.object(Path,'iterdir',side_effect=PermissionError('unreadable')),patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'),patch('workflow.common.gpu_job_queue.preview_gpu_resume_records',return_value=current_preview_record),patch('workflow.domains.music.generation.launch_gpu_process') as current_launch_mock,patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
            current_preview_value=self.current_music_service.execute_music_command('resume-preview',{'id':current_job_root.name})
            self.assertEqual(current_preview_value['resume_availability'],'unknown')
            with self.assertRaises(PermissionError):
                self.current_music_service.create_music_job({'action':'prepare'})
            current_launch_mock.assert_not_called()
            current_resume_mock.assert_not_called()

    def test_prepare_resume_excludes_itself_and_checks_other_hidden_preparation(self):
        self.current_music_service.current_service_name='music-heartmula'
        current_job_root=self.create_test_job('paused')
        write_record_atomically(current_job_root/'request.json',build_music_request('music-heartmula',{'action':'prepare'}))
        with patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'), patch('workflow.domains.music.generation.resume_gpu_generation',return_value={'status':'queued'}) as current_resume_mock:
            self.assertEqual(self.current_music_service.execute_music_command('resume',{'id':current_job_root.name})['status'],'queued')
            current_resume_mock.assert_called_once_with(current_job_root)
            current_resume_mock.reset_mock()
            current_other_root=self.create_test_job('queued')
            write_record_atomically(current_other_root/'request.json',build_music_request('music-heartmula',{'action':'prepare'}))
            (current_other_root/'.history-deleted').touch()
            with self.assertRaisesRegex(ValueError,'이미 대기 중이거나 실행 중'):
                self.current_music_service.execute_music_command('resume',{'id':current_job_root.name})
            current_resume_mock.assert_not_called()

    def test_music_resume_forwards_valid_fingerprint_without_weakening_legacy(self):
        current_job_root=self.create_test_job('failed')
        self.current_music_service.current_service_name='music-heartmula'
        current_review_fingerprint='a'*64
        with patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'),patch('workflow.domains.music.generation.verify_music_request'),patch('workflow.domains.music.generation.resume_gpu_generation',return_value={'status':'queued'}) as current_resume_mock:
            self.current_music_service.execute_music_command('resume',{'id':current_job_root.name,'expected_resume_fingerprint':current_review_fingerprint})
            current_resume_mock.assert_called_once_with(current_job_root,expected_resume_fingerprint=current_review_fingerprint,expected_resume_service='music-heartmula',expected_resume_command=self.current_music_service.build_music_worker_command(current_job_root))
            current_resume_mock.reset_mock()
            self.current_music_service.execute_music_command('resume',{'id':current_job_root.name})
            current_resume_mock.assert_called_once_with(current_job_root)
            for current_invalid_value in (None,'','A'*64,'a'*63,42):
                current_resume_mock.reset_mock()
                with self.subTest(current_invalid_value=current_invalid_value),self.assertRaises(ValueError):
                    self.current_music_service.execute_music_command('resume',{'id':current_job_root.name,'expected_resume_fingerprint':current_invalid_value})
                current_resume_mock.assert_not_called()

    def test_resume_preview_reports_current_download_and_other_preparation(self):
        self.current_music_service.current_service_name='music-heartmula'
        current_job_root=self.create_test_job('failed')
        write_record_atomically(current_job_root/'request.json',build_music_request('music-heartmula',{'action':'prepare'}))
        current_mock_preview={'status':'failed','expected_resume_fingerprint':'a'*64}
        with patch('workflow.common.gpu_job_queue.preview_gpu_resume_records',return_value=current_mock_preview), patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='running'), patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
            self.assertEqual(self.current_music_service.execute_music_command('resume-preview',{'id':current_job_root.name})['resume_availability'],'download_running')
            current_resume_mock.assert_not_called()
        current_other_root=self.create_test_job('queued')
        write_record_atomically(current_other_root/'request.json',build_music_request('music-heartmula',{'action':'prepare'}))
        with patch('workflow.common.gpu_job_queue.preview_gpu_resume_records',return_value=current_mock_preview), patch('workflow.common.model_prepare_process.inspect_registered_preparation',return_value='idle'):
            self.assertEqual(self.current_music_service.execute_music_command('resume-preview',{'id':current_job_root.name})['resume_availability'],'other_preparation')

    def test_resume_blocks_when_download_lock_cannot_be_inspected(self):
        from tempfile import TemporaryDirectory
        from workflow.domains.hermes_agent import audio_resume_operations
        self.current_music_service.current_service_name='music-heartmula'
        current_job_root=self.create_test_job('failed')
        current_mock_preview={'status':'failed','expected_resume_fingerprint':'a'*64}
        def route_current_audio_command(current_service_name,current_command_name,current_payload_record):
            self.assertEqual(current_service_name,'music-heartmula')
            return self.current_music_service.execute_music_command(current_command_name,current_payload_record)
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)),patch.object(audio_resume_operations,'call_hermes_audio_service',side_effect=route_current_audio_command),patch('workflow.common.gpu_job_queue.preview_gpu_resume_records',return_value=current_mock_preview),patch('workflow.common.model_prepare_process.inspect_registered_preparation',side_effect=PermissionError('lock unavailable')),patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
            current_preview_value=audio_resume_operations.preview_hermes_audio_resume('music-heartmula',current_job_root.name)
            self.assertEqual(current_preview_value['resume_availability'],'unknown')
            current_receipt_value=audio_resume_operations.submit_hermes_audio_resume_once('resume_lock_error_123','music-heartmula',current_job_root.name,'a'*64)
            self.assertEqual((current_receipt_value['state'],current_receipt_value['reason']),('blocked','unavailable'))
            self.assertEqual(audio_resume_operations.read_hermes_audio_resume_receipt('resume_lock_error_123'),{'state':'not_found','request_id':'resume_lock_error_123'})
            current_resume_mock.assert_not_called()

    def test_music_resume_preview_rechecks_records_without_dispatch(self):
        from workflow.common.management_gateway import identify_management_command
        current_job_root=self.create_test_job('failed')
        self.current_music_service.current_service_name='music-heartmula'
        write_record_atomically(current_job_root/'gpu-command.json',{'command':self.current_music_service.build_music_worker_command(current_job_root),'service':'music-heartmula'})
        current_payload_record={'id':current_job_root.name}
        self.assertEqual(resolve_management_command('music-heartmula','resume-preview',current_payload_record),('POST','/music-heartmula/resume/preview'))
        self.assertEqual(identify_management_command('/music-heartmula/resume/preview','POST',current_payload_record),('music-heartmula','resume-preview',current_payload_record))
        with patch('workflow.domains.music.generation.verify_music_request'),patch('workflow.domains.music.generation.resume_gpu_generation') as current_resume_mock:
            current_preview_record=self.current_music_service.execute_music_command('resume-preview',current_payload_record)
            self.assertEqual(current_preview_record['id'],current_job_root.name)
            self.assertEqual(current_preview_record['service'],'music-heartmula')
            self.assertEqual(len(current_preview_record['expected_resume_fingerprint']),64)
            self.assertNotIn('request',current_preview_record)
            write_record_atomically(current_job_root/'gpu-command.json',{'command':['wrong-worker'],'service':'music-heartmula'})
            with self.assertRaises(ValueError):self.current_music_service.execute_music_command('resume-preview',current_payload_record)
            write_record_atomically(current_job_root/'gpu-command.json',{'command':['worker'],'service':'sfx-dasheng-audiogen'})
            with self.assertRaises(ValueError):self.current_music_service.execute_music_command('resume-preview',current_payload_record)
            write_record_atomically(current_job_root/'gpu-command.json',{'command':self.current_music_service.build_music_worker_command(current_job_root),'service':'music-heartmula'})
            current_resume_mock.assert_not_called()
            write_record_atomically(current_job_root/'status.json',{'status':'running'})
            with self.assertRaises(ValueError):self.current_music_service.execute_music_command('resume-preview',current_payload_record)
            current_resume_mock.assert_not_called()

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
        for current_service_name in ('music-minimax',):
            with patch('workflow.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments(current_service_name,['generate','--prompt','soft flute','--duration-seconds','15','--seed','8','--loop-request','--detach'])
            current_command_arguments = current_command_mock.call_args.args
            self.assertEqual(current_command_arguments[:2],(current_service_name,'generate'))
            self.assertEqual(validate_music_request(current_service_name,current_command_arguments[2]),{'action':'generate','prompt':'soft flute','duration_seconds':15.0,'seed':8,'loop_request':True,'tag':''})

    def test_cli_token_limit_uses_shared_normalization(self):
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('music-minimax',['generate','--prompt','soft flute','--max-new-tokens','751','--detach'])
        current_command_payload = current_command_mock.call_args.args[2]
        self.assertEqual(current_command_payload['max_new_tokens'],751)
        self.assertNotIn('duration_seconds',current_command_payload)
        self.assertEqual(int(validate_music_request('music-minimax',current_command_payload)['duration_seconds']*25),751)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            execute_gateway_arguments('music-minimax',['generate','--prompt','soft flute','--max-new-tokens','750','--duration-seconds','30','--detach'])
        with self.assertRaisesRegex(ValueError,'폐기'):
            self.current_music_service.execute_music_command('generate',{'prompt':'soft flute','max_new_tokens':751})

    def test_music_source_logs_return_only_last_16000_bytes(self):
        current_job_root=self.create_test_job('completed')
        (current_job_root/'worker.log').write_bytes(b'A'*1000+b'B'*16000)
        current_log_record=self.current_music_service.execute_music_command('logs',{'id':current_job_root.name})
        self.assertEqual(current_log_record['log'],'B'*16000)
        self.current_launcher_mock.assert_not_called()

    def test_gateway_preserves_service_specific_log_scope(self):
        import threading
        from http.server import ThreadingHTTPServer
        from workflow.common.management_gateway import execute_management_command
        from workflow.domains.image.image_generation import ImageGenerationManager
        from workflow.gateway_server import create_gateway_request_handler
        current_music_job=self.create_test_job('completed')
        current_log_bytes=b'A'*1000+b'B'*16000
        (current_music_job/'worker.log').write_bytes(current_log_bytes)
        current_image_manager=ImageGenerationManager()
        current_image_manager.route_prefix_value='/flux-image-generator'
        current_image_manager.job_storage_root=self.current_test_root/'image-jobs'
        current_image_job=current_image_manager.job_storage_root/current_music_job.name
        current_image_job.mkdir(parents=True)
        (current_image_job/'worker.log').write_bytes(current_log_bytes)
        (current_image_job/'status.json').write_text('{"status":"completed"}')
        current_gateway_value=ManagementCommandGateway({'music-minimax':self.current_music_service.handle_music_request,'flux-image':current_image_manager.handle_image_request})
        current_server_value=ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_value.handle))
        current_server_value.emit_gateway_trace=lambda *current_values:None
        current_thread_value=threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_thread_value.start()
        try:
            current_gateway_origin='http://127.0.0.1:'+str(current_server_value.server_port)
            self.assertEqual(execute_management_command('music-minimax','logs',{'id':current_music_job.name},current_gateway_origin),'B'*16000)
            self.assertEqual(execute_management_command('flux-image','logs',{'id':current_image_job.name},current_gateway_origin),current_log_bytes.decode())
            current_image_status=execute_management_command('flux-image','status',{'id':current_image_job.name},current_gateway_origin)
            self.assertEqual(current_image_status['log'],'B'*12000)
            self.current_launcher_mock.assert_not_called()
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_thread_value.join(timeout=5)

    def test_gateway_envelope_and_http_security(self):
        current_gateway_manager = ManagementCommandGateway({'music-minimax':self.current_music_service.handle_music_request})
        current_request_bytes = json.dumps({'service':'music-minimax','command':'generate','payload':{'prompt':'soft flute'}}).encode()
        current_http_handler = SimpleNamespace(command='POST',path='/management/command',server=SimpleNamespace(server_port=9999),headers={'Host':'127.0.0.1:9999','Origin':'http://127.0.0.1:9999','Content-Type':'application/json','Content-Length':str(len(current_request_bytes))},rfile=io.BytesIO(current_request_bytes),wfile=io.BytesIO(),send_response=Mock(),send_header=Mock(),end_headers=Mock())
        self.assertTrue(current_gateway_manager.handle(current_http_handler))
        current_http_handler.send_response.assert_called_once_with(400)
        self.current_launcher_mock.assert_not_called()
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
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'id':'mock'}) as current_command_mock, contextlib.redirect_stdout(io.StringIO()):
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
        write_record_atomically(current_job_root/'request.json', build_music_request('music-heartmula', {'prompt':'piano','lyrics':'[Verse]\nHome'}))
        current_original_signals = {current_signal_number:signal.getsignal(current_signal_number) for current_signal_number in (signal.SIGTERM,signal.SIGINT)}
        try:
            for current_failure_error,current_expected_status in [(RuntimeError('CUDA OOM'),'failed'),(InterruptedError('cancel'),'cancelled')]:
                with patch('generators.music.worker.resolve_music_paths',return_value=(self.current_music_service.job_storage_root,self.current_test_root/'model',self.current_test_root/'python')), patch('generators.music.runtime.require_music_cuda',side_effect=current_failure_error), patch('workflow.common.generation_telemetry.GenerationTelemetryRecorder.sample_generation_memory'), self.assertRaises(type(current_failure_error)):
                    execute_music_worker('music-heartmula',current_job_root)
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
        import subprocess
        from workflow.common.history_summaries import audio_result_available,read_history_summary
        directory=self.create_test_job();attempt='a'*32
        write_record_atomically(directory/'result.json',{'attempt':attempt})
        audio=directory/'attempts'/attempt/'music.wav';audio.parent.mkdir(parents=True);audio.write_bytes(b'RIFF')
        self.assertTrue(audio_result_available(directory,'music-minimax'))
        summary=read_history_summary(directory);summary.update(duration_seconds=30,audio_available=True)
        root=Path(__file__).resolve().parents[2]
        script="""import {historyInputSummary} from './gui/historyInputSummary.mjs';
          const values=historyInputSummary(JSON.parse(process.argv[1]));
          if(!values.includes('WAV 오디오 결과') || !values.includes('길이 30초'))throw Error(JSON.stringify(values));"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(summary)],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        audio.unlink();audio.symlink_to(directory/'request.json')
        self.assertFalse(audio_result_available(directory,'music-minimax'))

    def test_stage_and_final_memory_samples_are_recorded(self):
        from workflow.common.generation_telemetry import GenerationTelemetryRecorder
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

    def test_audio_pages_share_model_and_history_controls(self):
        import os
        import subprocess
        from workflow.common.management_catalog import DEFAULT_PAGE_RECORDS, NATIVE_MANAGEMENT_APPLICATIONS
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={search:''};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),pages=require(process.argv[1]);
              for(const Page of [pages.HeartmulaPage,pages.default]){
                const html=server.renderToStaticMarkup(React.createElement(Page,{}));
                for(const label of ['모델 다운로드·준비','모델 준비 요청 검토','생성 이력'])if(!html.includes(label))throw Error(label);
              }"""
            result=subprocess.run(['node','-e',script,str(bundle)],cwd=gui,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(result.returncode,0,result.stderr)
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            self.assertIn(current_service_name,NATIVE_MANAGEMENT_APPLICATIONS)
            self.assertEqual(next(current_page_record for current_page_record in DEFAULT_PAGE_RECORDS if current_page_record['id']==current_service_name)['category'],'sound-management')


if __name__=='__main__':
    unittest.main()
