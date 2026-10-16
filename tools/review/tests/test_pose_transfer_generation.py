"""포즈 변환 입력 수·역할·해상도·CLI 계약 검증."""
import base64
import ast
from pathlib import Path
import io
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.domains.image.pose_transfer_generation import PoseTransferGenerationManager, load_pose_transfer_prompt
from tools.review.common import management_gateway


class PoseTransferContractTests(unittest.TestCase):

    def test_vnccs_pipeline_publishes_worker_progress_without_gpu(self):
        import json
        import threading
        from datetime import datetime
        from tools.review.common.worker_generation_progress import WorkerGenerationProgress
        import tempfile
        from types import SimpleNamespace
        from contextlib import ExitStack
        from unittest.mock import MagicMock
        from generators.image import vnccs_runtime
        from tools.review.common.queue_generation_telemetry import QueueGenerationTelemetry, read_queue_generation_metrics
        current_torch_module = MagicMock()
        current_torch_module.cuda.is_available.return_value = True
        current_torch_module.cuda.max_memory_allocated.return_value = 0
        current_pipeline_mock = MagicMock()
        for current_component_name in ('text_encoder', 'transformer', 'vae'):
            getattr(current_pipeline_mock, current_component_name).parameters.return_value = [SimpleNamespace(dtype='torch.bfloat16')]
            getattr(current_pipeline_mock, current_component_name).modules.return_value = []
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)/'pose-transfer'/'sample'
            current_job_root.mkdir(parents=True)
            current_request_record = {'references':['reference-1.png','reference-2.png'], 'steps':40, 'seed':1, 'prompt':'Match pose.', 'vnccs':{}}
            (current_job_root/'request.json').write_text(json.dumps(current_request_record))
            for current_reference_name in current_request_record['references']:
                Image.new('RGB',(512,512)).save(current_job_root/current_reference_name)
            current_queue_recorder = QueueGenerationTelemetry(current_job_root, 'vnccs')
            current_observed_steps = []
            current_heartbeat_observed = threading.Event()
            current_inference_records = []
            current_original_writer = WorkerGenerationProgress.record_worker_progress
            def record_observed_progress(current_writer_instance, current_progress_record):
                current_original_writer(current_writer_instance, current_progress_record)
                if current_progress_record['stage'] == 'inference':
                    current_inference_records.append(json.loads((current_job_root/'worker-progress.json').read_text()))
                    if len(current_inference_records) >= 2:
                        current_heartbeat_observed.set()
            def execute_mock_pipeline(**current_pipeline_arguments):
                self.assertTrue(current_heartbeat_observed.wait(8), "추론 대기 중 VNCCS heartbeat 기록 필요")
                for current_step_index in (0,39):
                    current_pipeline_arguments['callback_on_step_end'](None,current_step_index,None,{})
                    current_queue_recorder.save_generation_metrics()
                    current_worker_progress = read_queue_generation_metrics(current_job_root)['worker_progress']
                    current_observed_steps.append((current_worker_progress['stage'],current_worker_progress['step']))
                return SimpleNamespace(images=[Image.new('RGB',(512,512))])
            current_pipeline_mock.side_effect = execute_mock_pipeline
            current_diffusers_module = SimpleNamespace(QwenImage21Pipeline=SimpleNamespace(from_pretrained=MagicMock(return_value=current_pipeline_mock)))
            with ExitStack() as current_patch_stack:
                current_patch_stack.enter_context(patch.dict('sys.modules', {'torch':current_torch_module,'diffusers':current_diffusers_module}))
                for current_function_name in ('validate_vnccs_profile','validate_vnccs_assets','validate_qwen_model_assets'):
                    current_patch_stack.enter_context(patch.object(vnccs_runtime,current_function_name,return_value=current_job_root))
                current_patch_stack.enter_context(patch.object(vnccs_runtime,'collect_vnccs_adapter_state',return_value={'layer_count':1}))
                current_patch_stack.enter_context(patch.object(WorkerGenerationProgress,'record_worker_progress',record_observed_progress))
                current_patch_stack.enter_context(patch('tools.review.domains.image.three_reference_generation.validate_three_reference_job_path',return_value=current_job_root))
                current_patch_stack.enter_context(patch('tools.review.domains.image.qwen_21_generation.verify_qwen_saved_request'))
                vnccs_runtime.run_vnccs_pipeline(current_job_root)
            current_queue_recorder.save_generation_metrics()
            self.assertEqual([current_record['step'] for current_record in current_inference_records], [0,0])
            current_elapsed_seconds = (datetime.fromisoformat(current_inference_records[1]['updated_at'])-datetime.fromisoformat(current_inference_records[0]['updated_at'])).total_seconds()
            self.assertGreater(current_elapsed_seconds, 4)
            self.assertLess(current_elapsed_seconds, 7)
            self.assertEqual(current_observed_steps,[('denoise',1),('denoise',40)])
            self.assertEqual(read_queue_generation_metrics(current_job_root)['stage'],'postprocess')
            self.assertEqual(read_queue_generation_metrics(current_job_root)['step_total'],0)
            self.assertTrue((current_job_root/'result.png').is_file())

    def test_gui_new_submission_validation(self):
        from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request
        current_source_path = Path(__file__).resolve().parents[1] / 'ui/gradio/qwen_2511_app.py'
        current_source_tree = ast.parse(current_source_path.read_text())
        current_validation_call = next(current_ast_node for current_ast_node in ast.walk(current_source_tree) if isinstance(current_ast_node, ast.Call) and isinstance(current_ast_node.func, ast.Name) and current_ast_node.func.id == 'validate_qwen_plain_request')
        current_call_code = compile(ast.Expression(current_validation_call), str(current_source_path), 'eval')
        for current_step_value in (25, 40):
            current_request_record = {**self.create_request_record(), 'steps': current_step_value}
            current_validated_record = eval(current_call_code, {'validate_qwen_plain_request':validate_qwen_plain_request, 'generation_request_value':current_request_record, 'vnccs_transfer_enabled':True})
            self.assertEqual(current_validated_record['steps'], current_step_value)
        with self.assertRaises(ValueError):
            eval(current_call_code, {'validate_qwen_plain_request':validate_qwen_plain_request, 'generation_request_value':{**self.create_request_record(), 'steps':25}, 'vnccs_transfer_enabled':False})

    def create_request_record(self):
        image_output_buffer = io.BytesIO()
        Image.new('RGB', (32,32), 'white').save(image_output_buffer, format='PNG')
        encoded_image_value = base64.b64encode(image_output_buffer.getvalue()).decode()
        return {'action':'generate','prompt':load_pose_transfer_prompt(),'images':[encoded_image_value,encoded_image_value],'width':512,'height':512,'steps':40,'seed':10107,'tag':''}

    def test_sizes_and_steps(self):
        for selected_size_value in (512,):
            for selected_step_value in (25,40):
                current_request_record = self.create_request_record()
                current_request_record.update(width=selected_size_value,height=selected_size_value,steps=selected_step_value)
                validated_request_record = PoseTransferGenerationManager().validate_generation_request(current_request_record)
                self.assertEqual(validated_request_record['steps'],selected_step_value)
                self.assertEqual(validated_request_record['vnccs']['dtype'],'bfloat16')
                self.assertEqual(validated_request_record['vnccs']['reference_order'],['pose','identity'])

    def test_invalid_inputs_fail(self):
        for changed_field_values in ({'images':[]},{'images':['one']},{'images':['one','two','three']},{'width':1024,'height':1024},{'width':768,'height':768},{'width':512,'height':768},{'steps':4},{'steps':20},{'steps':30},{'steps':50}):
            with self.assertRaises(ValueError):
                PoseTransferGenerationManager().validate_generation_request({**self.create_request_record(),**changed_field_values})

    def test_cli_requires_exactly_two_references(self):
        with self.assertRaisesRegex(ValueError,'두 번'):
            management_gateway.execute_gateway_cli(['command','pose-transfer','generate','--detach'])

    def test_history_storage_is_separate(self):
        manager_instance_value = PoseTransferGenerationManager()
        self.assertEqual(manager_instance_value.job_storage_root.name,'pose-transfer')
        self.assertEqual(manager_instance_value.history_storage_path().name,'pose-transfer')
