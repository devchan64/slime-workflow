"""Phantom R2V 입력·게이트웨이·이력·관측 계약 검증."""
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
from generators.phantom.contracts import validate_phantom_request, verify_phantom_request
from tools.review.domains.phantom.generation import PhantomGenerationManager
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
from tools.review.common.management_gateway import ManagementCommandGateway, execute_gateway_cli, resolve_management_command
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


class PhantomGenerationContractTests(unittest.TestCase):
    def test_restore_phantom_inputs_verifies_every_snapshot(self):
        import gradio as gr
        from tools.review.ui.gradio import phantom_app
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_storage_directory = Path(current_temporary_directory)
            current_generation_identifier = '2026-10-15_13-00-00-1234abcd'
            current_job_directory = current_storage_directory/current_generation_identifier
            current_job_directory.mkdir()
            current_saved_record = self.create_saved_request(current_job_directory)
            current_history_record = {'id': current_generation_identifier, 'request': current_saved_record}
            with patch.object(phantom_app, 'PHANTOM_JOB_STORAGE_ROOT', current_storage_directory):
                current_restored_values = phantom_app.restore_phantom_inputs(current_history_record)
                self.assertEqual(current_restored_values[0].size, (64, 64))
                self.assertEqual(current_restored_values[1:4], (None, None, None))
                self.assertEqual(current_restored_values[4], current_saved_record['prompt'])
                (current_job_directory/'reference-1.png').write_bytes(b'changed')
                with self.assertRaisesRegex(gr.Error, '해시 불일치'):
                    phantom_app.restore_phantom_inputs(current_history_record)

    def create_phantom_payload(self):
        current_image_buffer=io.BytesIO()
        Image.new('RGBA',(64,64),(20,40,60,100)).save(current_image_buffer,format='PNG')
        return {'action':'generate','prompt':'A character walks in place.','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'frames':65,'seed':42}

    def create_saved_request(self,current_job_root):
        current_request_record=validate_phantom_request(self.create_phantom_payload())
        current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
        (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
        return current_saved_record

    def test_r2v_contract_rejects_video_mask_model(self):
        for current_forbidden_field in ('video','mask','model','first_frame'):
            with self.subTest(field=current_forbidden_field),self.assertRaises(ValueError):
                validate_phantom_request({**self.create_phantom_payload(),current_forbidden_field:None})
        current_valid_record=validate_phantom_request(self.create_phantom_payload())
        self.assertIsNone(current_valid_record['phantom']['video'])
        self.assertIsNone(current_valid_record['phantom']['mask'])
        self.assertEqual(current_valid_record['frames'],65)

    def test_invalid_frames_seed_reference_rejected(self):
        for current_field_name,current_field_value in [('frames',64),('frames',True),('seed',-1),('seed',True),('images',[]),('images',['bad']),('width',768),('steps',101)]:
            with self.subTest(field=current_field_name,value=current_field_value),self.assertRaises(ValueError):
                validate_phantom_request({**self.create_phantom_payload(),current_field_name:current_field_value})

    def test_parameter_rules_and_legacy_resume(self):
        for current_frame_count in (1,5,17,33,81,97,161):
            current_payload_record={**self.create_phantom_payload(),'frames':current_frame_count,'width':832,'height':480,'steps':50,'flow_shift':16.0,'guidance_scale':6.0,'conditioning_scale':0.8}
            self.assertEqual(validate_phantom_request(current_payload_record)['phantom']['flow_shift'],16.0)
        for current_field_name,current_field_value in [('frames',0),('frames',165),('steps',True),('flow_shift',float('nan')),('guidance_scale',0),('conditioning_scale',21)]:
            with self.assertRaises(ValueError):
                validate_phantom_request({**self.create_phantom_payload(),current_field_name:current_field_value})
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_request_record=validate_phantom_request({**self.create_phantom_payload(),'width':832,'height':480,'steps':50})
            current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            self.assertEqual(verify_phantom_request(current_job_root)['steps'],50)

    def test_multiple_reference_save_restore_order(self):
        current_image_values=[]
        for current_color_value in ('red','green','blue','white'):
            current_image_buffer=io.BytesIO()
            Image.new('RGB',(64,64),current_color_value).save(current_image_buffer,format='PNG')
            current_image_values.append(base64.b64encode(current_image_buffer.getvalue()).decode())
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_request_record=validate_phantom_request({**self.create_phantom_payload(),'images':current_image_values})
            current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            self.assertEqual(len(verify_phantom_request(current_job_root)['references']),4)
            self.assertEqual(Image.open(current_job_root/'reference-1.png').getpixel((0,0))[:3],(255,0,0))
            current_saved_record['references'].reverse()
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            with self.assertRaises(ValueError):verify_phantom_request(current_job_root)
        with self.assertRaises(ValueError):
            validate_phantom_request({**self.create_phantom_payload(),'images':current_image_values+[current_image_values[0]]})

    def test_negative_prompt_saved_and_validated(self):
        for current_negative_value in (None, 1, 'a'*8001):
            with self.assertRaises(ValueError):
                validate_phantom_request({**self.create_phantom_payload(),'negative_prompt':current_negative_value})
        for current_negative_text in ('', 'treadmill, exercise machine'):
            with tempfile.TemporaryDirectory() as current_temporary_path:
                current_job_root=Path(current_temporary_path)
                current_request_record=validate_phantom_request({**self.create_phantom_payload(),'negative_prompt':current_negative_text})
                current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_job_root,current_request_record)}
                (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
                self.assertEqual(verify_phantom_request(current_job_root)['phantom']['negative_prompt'],current_negative_text)
                current_saved_record['negative_prompt']='changed'
                (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
                with self.assertRaises(ValueError):verify_phantom_request(current_job_root)

    def test_saved_request_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_saved_record=self.create_saved_request(current_job_root)
            verify_phantom_request(current_job_root)
            current_saved_record['phantom']['mask']='bad'
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            with self.assertRaises(ValueError):verify_phantom_request(current_job_root)

    def test_reference_hash_checked_on_resume(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            self.create_saved_request(current_job_root)
            (current_job_root/'reference-1.png').write_bytes(b'bad')
            with self.assertRaises(ValueError):verify_phantom_request(current_job_root)

    def test_history_delete_removes_files_and_stays_hidden(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_manager_value=PhantomGenerationManager()
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
            current_manager_value=PhantomGenerationManager()
            current_manager_value.job_storage_root=Path(current_temporary_path)
            current_job_identifier='2026-10-11_00-00-00-12345678'
            current_job_root=Path(current_temporary_path)/current_job_identifier
            current_job_root.mkdir()
            for current_status_name in ('queued','running'):
                (current_job_root/'status.json').write_text(json.dumps({'status':current_status_name}))
                with self.assertRaises(ValueError):current_manager_value.delete_generation_history(current_job_identifier)

    def test_gateway_routes_and_cli_payload(self):
        self.assertEqual(resolve_management_command('phantom','generate',self.create_phantom_payload())[1],'/phantom/jobs')
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_reference_path=Path(current_temporary_path)/'reference.png'
            current_reference_path.write_bytes(base64.b64decode(self.create_phantom_payload()['images'][0]))
            with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'test','status':'queued'}) as current_command_mock,contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_cli(['command','phantom','generate','--reference',str(current_reference_path),'--prompt','A character walks in place.','--frames','65','--seed','42','--detach'])
            current_payload_record=current_command_mock.call_args.args[2]
            self.assertEqual(validate_phantom_request(current_payload_record),validate_phantom_request({**self.create_phantom_payload(),'width':832,'height':480,'steps':50,'flow_shift':5.0,'guidance_scale':7.5,'conditioning_scale':5.0}))

    def test_status_keeps_attempt_metrics_for_failed_and_resumed_jobs(self):
        with tempfile.TemporaryDirectory() as current_temporary_path:
            current_job_root=Path(current_temporary_path)
            current_attempt_root=current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'current-attempt.json').write_text(json.dumps({'id':'a'*32}))
            (current_attempt_root/'metrics.json').write_text(json.dumps({'stage':'failed','step':4,'estimate':{'remaining':None},'gpu_observations':{'gpu':{'process_peak_mib':4000}}}))
            current_manager_value=PhantomGenerationManager()
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
