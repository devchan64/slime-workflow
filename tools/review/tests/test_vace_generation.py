"""VACE R2V 입력·게이트웨이·이력·관측 계약 검증."""
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
from generators.vace.contracts import validate_vace_request, verify_vace_request
from tools.review.domains.vace.generation import VaceGenerationManager
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_cli, resolve_management_command
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


class VaceGenerationContractTests(unittest.TestCase):
    def test_completed_video_files_are_verified_before_publication(self):
        from tools.review.domains.phantom.generation import PhantomGenerationManager
        for current_manager_class in (VaceGenerationManager, PhantomGenerationManager):
            with self.subTest(service=current_manager_class.__name__), tempfile.TemporaryDirectory() as current_temporary_directory:
                current_job_root = Path(current_temporary_directory) / 'job'
                current_attempt_root = current_job_root / 'attempts' / ('a' * 32)
                current_attempt_root.mkdir(parents=True)
                current_result_path = current_job_root / 'result.json'
                current_result_path.write_text(json.dumps({'attempt': 'a' * 32}))
                current_service_instance = object.__new__(current_manager_class)
                current_service_instance.route_prefix_value = '/isolated'
                for current_file_name in ('preview.mp4', 'frames.zip', 'output-000.png'):
                    current_missing_status = current_service_instance.enrich_generation_status(current_job_root, {'status': 'completed', 'video': '/stale'})
                    self.assertIn(current_file_name, current_missing_status['result_error'])
                    self.assertEqual(current_missing_status['status'], 'completed')
                    self.assertNotIn('video', current_missing_status)
                    (current_attempt_root / current_file_name).write_bytes(b'fixture')
                current_status_record = current_service_instance.enrich_generation_status(current_job_root, {'status': 'completed'})
                self.assertTrue(current_status_record['video'].endswith('/preview.mp4'))
                self.assertTrue(current_status_record['download'].endswith('/frames.zip'))
                self.assertTrue(current_status_record['image'].endswith('/output-000.png'))
                (current_attempt_root / 'preview.mp4').unlink()
                current_external_path = Path(current_temporary_directory) / 'external.mp4'
                current_external_path.write_bytes(b'preserve')
                (current_attempt_root / 'preview.mp4').symlink_to(current_external_path)
                self.assertIn('벗어났습니다', current_service_instance.enrich_generation_status(current_job_root, {'status': 'completed'})['result_error'])
                self.assertEqual(current_external_path.read_bytes(), b'preserve')
                current_result_path.write_text(json.dumps({'attempt': '../outside'}))
                self.assertIn('시도 ID', current_service_instance.enrich_generation_status(current_job_root, {'status': 'completed'})['result_error'])
                self.assertEqual(current_service_instance.enrich_generation_status(current_job_root, {'status': 'queued'}), {'status': 'queued'})

    def test_missing_result_keeps_history_and_status_available(self):
        from tools.review.domains.phantom.generation import PhantomGenerationManager
        from tools.review.common.gradio_video_results import render_video_generation_result
        for current_manager_class in (VaceGenerationManager, PhantomGenerationManager):
            with self.subTest(service=current_manager_class.__name__), tempfile.TemporaryDirectory() as current_temporary_directory:
                current_service_instance=object.__new__(current_manager_class)
                current_service_instance.route_prefix_value='/isolated'
                current_service_instance.job_storage_root=Path(current_temporary_directory)
                current_history_records=[]
                for current_job_identifier in ('missing-result','intact-result'):
                    current_job_root=Path(current_temporary_directory)/current_job_identifier
                    current_attempt_root=current_job_root/'attempts'/('a'*32)
                    current_attempt_root.mkdir(parents=True)
                    (current_job_root/'status.json').write_text('{"status":"completed"}')
                    (current_job_root/'result.json').write_text(json.dumps({'attempt':'a'*32}))
                    if current_job_identifier=='intact-result':
                        for current_file_name in ('preview.mp4','frames.zip','output-000.png'):
                            (current_attempt_root/current_file_name).write_bytes(b'fixture')
                    current_history_records.append({'id':current_job_identifier})
                with patch('tools.review.domains.image.image_generation.load_generation_history_records',return_value=current_history_records):
                    current_history_output=current_service_instance.list_generation_history()
                self.assertEqual(len(current_history_output),2)
                current_missing_status=current_history_output[0]['status']
                self.assertEqual(current_missing_status['status'],'completed')
                self.assertIn('preview.mp4',current_missing_status['result_error'])
                self.assertIsNone(current_history_output[0]['image'])
                self.assertTrue(current_history_output[1]['image'].endswith('output-000.png'))
                current_result_markup=render_video_generation_result('missing-result',current_missing_status,'')
                self.assertIn('결과 조회 불가',current_result_markup)
                self.assertNotIn('<video',current_result_markup)
                self.assertEqual(json.loads((Path(current_temporary_directory)/'missing-result/status.json').read_text()),{'status':'completed'})

    def test_video_result_error_matches_gui_cli_http_and_recovers(self):
        import threading
        from http.server import ThreadingHTTPServer
        from tools.review.gateway_server import create_gateway_request_handler
        from tools.review.common.management_client import execute_remote_management_command
        from tools.review.domains.phantom.generation import PhantomGenerationManager
        for current_service_name,current_manager_class,current_route_prefix in (('wan21-vace',VaceGenerationManager,'/wan21-vace'),('phantom',PhantomGenerationManager,'/phantom')):
            with self.subTest(service=current_service_name), tempfile.TemporaryDirectory() as current_temporary_directory:
                current_job_identifier='2026-10-15_00-00-00-12345678'
                current_job_root=Path(current_temporary_directory)/current_job_identifier
                current_attempt_root=current_job_root/'attempts'/('a'*32)
                current_attempt_root.mkdir(parents=True)
                (current_job_root/'status.json').write_text('{"status":"completed"}')
                (current_job_root/'result.json').write_text(json.dumps({'attempt':'a'*32}))
                current_service_instance=object.__new__(current_manager_class)
                current_service_instance.job_storage_root=Path(current_temporary_directory)
                current_service_instance.route_prefix_value=current_route_prefix
                current_gateway_instance=ManagementCommandGateway({current_service_name:current_service_instance.handle_image_request})
                with ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(current_gateway_instance.handle)) as current_http_server:
                    current_http_server.emit_gateway_trace=lambda *current_trace_values:None
                    current_server_thread=threading.Thread(target=current_http_server.serve_forever,daemon=True)
                    current_server_thread.start()
                    current_server_address=f'http://127.0.0.1:{current_http_server.server_port}'
                    try:
                        for current_result_ready in (False,True):
                            if current_result_ready:
                                for current_file_name in ('preview.mp4','frames.zip','output-000.png'):
                                    (current_attempt_root/current_file_name).write_bytes(b'fixture')
                            with patch.dict('os.environ',{'SLIME_MANAGEMENT_GATEWAY_URL':current_server_address}):
                                current_gui_response=execute_remote_management_command(current_service_name,'status',{'id':current_job_identifier})
                            current_cli_output=io.StringIO()
                            with contextlib.redirect_stdout(current_cli_output):
                                self.assertEqual(execute_gateway_cli(['command',current_service_name,'--server-url',current_server_address,'status',current_job_identifier]),0)
                            current_cli_response=json.loads(current_cli_output.getvalue())
                            # 각 HTTP 조회에서 갱신되는 ETA 시각은 결과 계약 비교 대상이 아니다.
                            for current_field_name in ('status','result_error','video','download','image','log_url'):
                                self.assertEqual(current_cli_response.get(current_field_name),current_gui_response.get(current_field_name))
                                self.assertEqual(current_field_name in current_cli_response,current_field_name in current_gui_response)
                            self.assertEqual(current_gui_response['status'],'completed')
                            if current_result_ready:
                                self.assertNotIn('result_error',current_gui_response)
                                self.assertTrue(current_gui_response['video'].endswith('/preview.mp4'))
                            else:
                                self.assertIn('preview.mp4',current_gui_response['result_error'])
                                for current_field_name in ('video','download','image'):
                                    self.assertNotIn(current_field_name,current_gui_response)
                    finally:
                        current_http_server.shutdown()
                        current_server_thread.join(timeout=5)

    def create_vace_payload(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGBA',(64,64),(20,40,60,100)).save(current_image_buffer,format='PNG')
        return {'action':'generate','prompt':'A character walks in place.','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'frames':65,'seed':42}

    def create_saved_request(self,current_job_root):
        current_request_record=validate_vace_request(self.create_vace_payload())
        current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
        (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
        return current_saved_record

    def test_r2v_contract_rejects_video_mask_model(self):
        for current_forbidden_field in ('video','mask','model','first_frame'):
            with self.subTest(field=current_forbidden_field),self.assertRaises(ValueError):
                validate_vace_request({**self.create_vace_payload(),current_forbidden_field:None})
        current_valid_record=validate_vace_request(self.create_vace_payload())
        self.assertIsNone(current_valid_record['vace']['video'])
        self.assertIsNone(current_valid_record['vace']['mask'])
        self.assertEqual(current_valid_record['frames'],65)

    def test_invalid_frames_seed_reference_rejected(self):
        for current_field_name,current_field_value in [('frames',64),('frames',True),('seed',-1),('seed',True),('images',[]),('images',['bad']),('width',768),('steps',101)]:
            with self.subTest(field=current_field_name,value=current_field_value),self.assertRaises(ValueError):
                validate_vace_request({**self.create_vace_payload(),current_field_name:current_field_value})

    def test_parameter_rules_and_legacy_resume(self):
        for current_frame_count in (1,5,17,33,81,97,161):
            current_payload_record={**self.create_vace_payload(),'frames':current_frame_count,'width':832,'height':480,'steps':50,'flow_shift':16.0,'guidance_scale':6.0,'conditioning_scale':0.8}
            self.assertEqual(validate_vace_request(current_payload_record)['vace']['flow_shift'],16.0)
        for current_field_name,current_field_value in [('frames',0),('frames',165),('steps',True),('flow_shift',float('nan')),('guidance_scale',0),('conditioning_scale',3)]:
            with self.assertRaises(ValueError):
                validate_vace_request({**self.create_vace_payload(),current_field_name:current_field_value})
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_request_record=validate_vace_request({**self.create_vace_payload(),'width':512,'height':512,'steps':30})
            current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            self.assertEqual(verify_vace_request(current_job_root)['steps'],30)

    def test_negative_prompt_saved_and_validated(self):
        for current_negative_value in (None, 1, 'a'*8001):
            with self.assertRaises(ValueError):
                validate_vace_request({**self.create_vace_payload(),'negative_prompt':current_negative_value})
        for current_negative_text in ('', 'treadmill, exercise machine'):
            with tempfile.TemporaryDirectory() as current_temporary_path:
                current_job_root=Path(current_temporary_path)
                current_request_record=validate_vace_request({**self.create_vace_payload(),'negative_prompt':current_negative_text})
                current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
                (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
                self.assertEqual(verify_vace_request(current_job_root)['vace']['negative_prompt'],current_negative_text)
                current_saved_record['negative_prompt']='changed'
                (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
                with self.assertRaises(ValueError):verify_vace_request(current_job_root)

    def test_saved_request_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_saved_record=self.create_saved_request(current_job_root)
            verify_vace_request(current_job_root)
            current_saved_record['vace']['mask']='bad'
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            with self.assertRaises(ValueError):verify_vace_request(current_job_root)

    def test_reference_hash_checked_on_resume(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            self.create_saved_request(current_job_root)
            (current_job_root/'reference-1.png').write_bytes(b'bad')
            with self.assertRaises(ValueError):verify_vace_request(current_job_root)

    def test_history_delete_removes_files_and_stays_hidden(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_manager_value=VaceGenerationManager()
            current_manager_value.job_storage_root=Path(current_temporary_path)/'jobs'
            current_history_root=Path(current_temporary_path)/'history'
            current_job_identifier='2026-10-11_00-00-00-12345678'
            current_job_root=current_manager_value.job_storage_root/current_job_identifier
            current_job_root.mkdir(parents=True)
            self.create_saved_request(current_job_root)
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            with patch.object(current_manager_value,'history_storage_path',return_value=current_history_root):
                self.assertEqual(len(current_manager_value.list_generation_history()),1)
                self.assertFalse(current_manager_value.delete_generation_history(current_job_identifier)['files_preserved'])
                self.assertFalse(current_job_root.exists())
                self.assertEqual(current_manager_value.list_generation_history(),[])

    def test_active_history_delete_rejected(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_manager_value=VaceGenerationManager()
            current_manager_value.job_storage_root=Path(current_temporary_path)
            current_job_identifier='2026-10-11_00-00-00-12345678'
            current_job_root=Path(current_temporary_path)/current_job_identifier
            current_job_root.mkdir()
            for current_status_name in ('queued','running'):
                (current_job_root/'status.json').write_text(json.dumps({'status':current_status_name}))
                with self.assertRaises(ValueError):current_manager_value.delete_generation_history(current_job_identifier)

    def test_gateway_routes_and_cli_payload(self):
        with self.assertRaisesRegex(ValueError,'운영 중지'):
            resolve_management_command('wan21-vace','generate',self.create_vace_payload())
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_reference_path=Path(current_temporary_path)/'reference.png'
            current_reference_path.write_bytes(base64.b64decode(self.create_vace_payload()['images'][0]))
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'test','status':'queued'}) as current_command_mock,contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_cli(['command','wan21-vace','generate','--reference',str(current_reference_path),'--prompt','A character walks in place.','--frames','65','--seed','42','--detach'])
            current_payload_record=current_command_mock.call_args.args[2]
            self.assertEqual(validate_vace_request(current_payload_record),validate_vace_request({**self.create_vace_payload(),'width':832,'height':480,'steps':50,'flow_shift':5.0,'guidance_scale':5.0,'conditioning_scale':1.0}))

    def test_status_keeps_attempt_metrics_for_failed_and_resumed_jobs(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_attempt_root=current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'current-attempt.json').write_text(json.dumps({'id':'a'*32}))
            (current_attempt_root/'metrics.json').write_text(json.dumps({'stage':'failed','step':4,'estimate':{'remaining':None},'gpu_observations':{'gpu':{'process_peak_mib':4000}}}))
            current_manager_value=VaceGenerationManager()
            for current_status_name in ('failed','cancelled'):
                (current_job_root/'status.json').write_text(json.dumps({'status':current_status_name}))
                current_status_record=current_manager_value.read_generation_status_record(current_job_root)
                self.assertEqual(current_status_record['metrics']['gpu_observations']['gpu']['process_peak_mib'],4000)
            (current_job_root/'status.json').write_text('{"status":"queued"}')
            current_status_record=current_manager_value.read_generation_status_record(current_job_root)
            self.assertNotIn('metrics',current_status_record)
            self.assertTrue((current_attempt_root/'metrics.json').exists())

    def test_gpu_sampling_separates_device_and_process(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            import os
            current_recorder_value=GenerationTelemetryRecorder(Path(current_temporary_path),30,[])
            with patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=['gpu-one, 6000\n',f'gpu-one, {os.getpid()}, 4000\n']):
                current_recorder_value.sample_generation_memory()
            current_memory_record=current_recorder_value.current_run_state['gpu_observations']['gpu-one']
            self.assertEqual(current_memory_record['process_peak_mib'],4000)
            self.assertEqual(current_memory_record['device_peak_mib'],6000)
            with patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=['gpu-one, 2000\n','']):
                current_recorder_value.sample_generation_memory()
            self.assertIsNone(current_memory_record['process_current_mib'])
            self.assertEqual(current_memory_record['process_peak_mib'],4000)

    def test_telemetry_unknown_delay_and_termination(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_recorder_value=GenerationTelemetryRecorder(Path(current_temporary_path),30,[])
            with contextlib.redirect_stdout(io.StringIO()):
                current_recorder_value.save_generation_metrics()
                self.assertIsNone(current_recorder_value.current_run_state['estimate']['remaining'])
                current_recorder_value.update_generation_stage('inference')
                current_recorder_value.record_generation_step(1)
                current_recorder_value.record_generation_step(2)
                self.assertIsNotNone(current_recorder_value.current_run_state['inference_estimate']['remaining'])
                current_recorder_value.current_run_state['status']='failed'
                current_recorder_value.save_generation_metrics()
            self.assertIsNone(current_recorder_value.current_run_state['estimate']['estimated_progress'])
            self.assertEqual(json.loads((Path(current_temporary_path)/'metrics.json').read_text())['status'],'failed')


if __name__=='__main__':unittest.main()
