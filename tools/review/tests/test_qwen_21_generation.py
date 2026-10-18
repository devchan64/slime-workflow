"""2.1 입력 원문·참조 10장·기록 검증·CLI 계약 회귀 검사."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request, verify_qwen_saved_request, QwenPlainGenerationManager
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs, validate_three_reference_request
from tools.review.common.management_gateway import execute_gateway_arguments


class QwenPlainGenerationTests(unittest.TestCase):
    def create_reference_request(self, reference_image_count=0):
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (16, 16), 'red').save(current_image_buffer, format='PNG')
        return {'action':'generate','prompt':'  붉은 사과.\n흰 배경.  ','images':[base64.b64encode(current_image_buffer.getvalue()).decode()]*reference_image_count,
            'width':512,'height':512,'steps':40,'seed':10107}

    def test_runtime_publishes_progress_without_gpu_execution(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from generators.image import qwen_21_runtime
        current_torch_module = MagicMock()
        current_torch_module.cuda.is_available.return_value = True
        current_torch_module.cuda.max_memory_allocated.return_value = 0
        current_pipeline_mock = MagicMock()
        current_observed_steps = []
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            def execute_mock_pipeline(**current_pipeline_arguments):
                for current_step_index in (0, 39):
                    current_pipeline_arguments['callback_on_step_end'](None, current_step_index, None, {})
                    current_observed_steps.append(json.loads((current_job_root/'worker-progress.json').read_text())['step'])
                return SimpleNamespace(images=[Image.new('RGB', (512,512))])
            current_pipeline_mock.side_effect = execute_mock_pipeline
            current_diffusers_module = SimpleNamespace(QwenImage21Pipeline=SimpleNamespace(from_pretrained=MagicMock(return_value=current_pipeline_mock)))
            with patch.dict('sys.modules', {'torch': current_torch_module, 'diffusers': current_diffusers_module}), patch.object(qwen_21_runtime, 'validate_qwen_model_assets', return_value=current_job_root), patch.object(qwen_21_runtime.threading, 'Thread'):
                qwen_21_runtime.execute_qwen_reference_generation(current_job_root, {'prompt':'A tree.', 'steps':40,'width':512,'height':512,'seed':1}, [])
            current_progress_record = json.loads((current_job_root/'worker-progress.json').read_text())
            self.assertEqual(current_observed_steps, [1,40])
            self.assertEqual(current_progress_record['stage'], 'postprocess')
            self.assertEqual(current_progress_record['step_total'], 40)
            self.assertTrue((current_job_root/'result.png').is_file())

    def test_idle_inference_heartbeat_updates_persisted_timestamp(self):
        from datetime import datetime
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        import threading
        from generators.image import qwen_21_runtime
        from tools.review.common.worker_generation_progress import WorkerGenerationProgress
        current_heartbeat_observed = threading.Event()
        current_inference_records = []
        current_original_writer = WorkerGenerationProgress.record_worker_progress
        current_torch_module = MagicMock()
        current_torch_module.cuda.is_available.return_value = True
        current_torch_module.cuda.max_memory_allocated.return_value = 0
        current_pipeline_mock = MagicMock()
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            def record_observed_progress(current_writer_instance, current_progress_record):
                current_original_writer(current_writer_instance, current_progress_record)
                if current_progress_record['stage'] == 'inference':
                    current_inference_records.append(json.loads((current_job_root/'worker-progress.json').read_text()))
                    if len(current_inference_records) >= 2:
                        current_heartbeat_observed.set()
            def execute_waiting_pipeline(**current_pipeline_arguments):
                self.assertTrue(current_heartbeat_observed.wait(8), '실제 heartbeat가 추론 대기 중 기록을 갱신해야 함')
                return SimpleNamespace(images=[Image.new('RGB', (512,512))])
            current_pipeline_mock.side_effect = execute_waiting_pipeline
            current_diffusers_module = SimpleNamespace(QwenImage21Pipeline=SimpleNamespace(from_pretrained=MagicMock(return_value=current_pipeline_mock)))
            with patch.dict('sys.modules', {'torch':current_torch_module,'diffusers':current_diffusers_module}), patch.object(qwen_21_runtime,'validate_qwen_model_assets',return_value=current_job_root), patch.object(WorkerGenerationProgress,'record_worker_progress',record_observed_progress):
                qwen_21_runtime.execute_qwen_reference_generation(current_job_root, {'prompt':'A tree.','steps':40,'width':512,'height':512,'seed':1}, [])
            self.assertEqual([current_record['step'] for current_record in current_inference_records], [0,0])
            current_elapsed_seconds = (datetime.fromisoformat(current_inference_records[1]['updated_at'])-datetime.fromisoformat(current_inference_records[0]['updated_at'])).total_seconds()
            self.assertGreater(current_elapsed_seconds, 4)
            self.assertLess(current_elapsed_seconds, 7)
            self.assertEqual(json.loads((current_job_root/'worker-progress.json').read_text())['stage'], 'postprocess')

    def test_small_output_resolution_boundary(self):
        from tools.review.domains.image.three_reference_generation import validate_three_reference_request
        current_request_record = self.create_reference_request()
        current_request_record.update(width=256,height=256)
        self.assertEqual(validate_qwen_plain_request(current_request_record)['width'],256)
        with self.assertRaises(ValueError):
            validate_three_reference_request({**current_request_record,'steps':4})
        for invalid_output_size in (240,257):
            with self.assertRaises(ValueError):
                validate_qwen_plain_request({**current_request_record,'width':invalid_output_size})

    def test_transparent_reference_gui_service_and_resume(self):
        from tools.review.ui.gradio.qwen_2511_app import prepare_reference_image_bytes
        current_reference_image = Image.new('RGBA', (3, 1), (255, 0, 0, 0))
        current_reference_image.putpixel((1, 0), (255, 0, 0, 128))
        current_reference_image.putpixel((2, 0), (255, 0, 0, 255))
        current_image_buffer = io.BytesIO()
        current_reference_image.save(current_image_buffer, format='PNG')
        current_request_record = self.create_reference_request()
        current_request_record['images'] = [base64.b64encode(current_image_buffer.getvalue()).decode()]
        validated_request_record = validate_qwen_plain_request(current_request_record)
        normalized_reference_bytes = base64.b64decode(validated_request_record['images'][0])
        self.assertEqual(prepare_reference_image_bytes([current_reference_image], composite_transparent_background=True), [normalized_reference_bytes])
        with Image.open(io.BytesIO(normalized_reference_bytes)) as normalized_reference_image:
            self.assertEqual(normalized_reference_image.mode, 'RGB')
            self.assertEqual(list(normalized_reference_image.getdata()), [(255,255,255),(255,127,127),(255,0,0)])
        self.assertEqual(current_reference_image.getpixel((0,0)), (255,0,0,0))
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root = Path(temporary_directory_name)
            saved_request_record = {**validated_request_record, **save_three_reference_inputs(current_job_root, validated_request_record)}
            saved_request_record.pop('images')
            verify_qwen_saved_request(current_job_root, saved_request_record)

    def test_selectable_inference_steps(self):
        for selected_step_count in (20, 30, 40, 50):
            current_request_record = self.create_reference_request()
            current_request_record['steps'] = selected_step_count
            self.assertEqual(validate_qwen_plain_request(current_request_record)['steps'], selected_step_count)
        for selected_step_count in (0, 10, 60):
            with self.assertRaises(ValueError):
                validate_qwen_plain_request({**self.create_reference_request(), 'steps': selected_step_count})

    def test_original_prompt_is_unchanged(self):
        current_request_record = self.create_reference_request()
        validated_request_record = validate_qwen_plain_request(current_request_record)
        self.assertEqual(validated_request_record['prompt'], current_request_record['prompt'])
        self.assertEqual(validated_request_record['qwen21']['additional_prompt'], '')
        self.assertEqual(validated_request_record['qwen21']['prompt_sha256'],hashlib.sha256(current_request_record['prompt'].encode()).hexdigest())
        self.assertEqual(validated_request_record['images'], [])

    def test_ten_references_and_invalid_inputs(self):
        self.assertEqual(len(validate_qwen_plain_request(self.create_reference_request(10))['images']),10)
        for invalid_request_record in (self.create_reference_request(11), {**self.create_reference_request(),'steps':4}, {**self.create_reference_request(),'prompt':'word '*100}, {**self.create_reference_request(),'model':'other'}):
            with self.assertRaises(ValueError):
                validate_qwen_plain_request(invalid_request_record)
        with self.assertRaises(ValueError):
            validate_three_reference_request({**self.create_reference_request(4),'steps':4})

    def test_snapshot_ten_resume_and_prompt_tampering(self):
        current_request_record = validate_qwen_plain_request(self.create_reference_request(10))
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root = Path(temporary_directory_name)
            saved_request_record = {**current_request_record, **save_three_reference_inputs(current_job_root,current_request_record)}
            saved_request_record.pop('images')
            self.assertTrue((current_job_root/'reference-10.png').is_file())
            verify_qwen_saved_request(current_job_root,saved_request_record)
            saved_request_record['prompt'] += ' 변경'
            with self.assertRaises(ValueError):
                verify_qwen_saved_request(current_job_root,saved_request_record)

    def test_cli_raw_prompt_and_ten_references(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_reference_path = Path(temporary_directory_name)/'input.png'
            current_reference_path.write_bytes(base64.b64decode(self.create_reference_request(1)['images'][0]))
            current_prompt_text = self.create_reference_request()['prompt']
            current_command_values=['generate','--prompt',current_prompt_text,'--detach']
            for current_reference_index in range(10):
                current_command_values += ['--reference',str(current_reference_path)]
            with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'test'}) as gateway_call_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments('qwen-21',current_command_values)
            current_payload_record=gateway_call_mock.call_args.args[2]
            self.assertEqual(current_payload_record['prompt'],current_prompt_text)
            self.assertEqual(current_payload_record['steps'],40)
            self.assertEqual(len(current_payload_record['images']),10)
            validate_qwen_plain_request(current_payload_record)

    def test_history_and_runner_are_separate(self):
        current_service_manager=QwenPlainGenerationManager()
        self.assertEqual(current_service_manager.history_storage_path().name,'qwen-21')
        self.assertEqual(current_service_manager.job_storage_root.name,'qwen-image-21')
        self.assertTrue(current_service_manager.select_generation_runner().endswith('run_qwen_21_reference.py'))

    def test_prompt_options_and_saved_replay(self):
        current_request_record = validate_qwen_plain_request({**self.create_reference_request(), 'common_style': True, 'transparent_background': True})
        self.assertIn('large crisp defining details', current_request_record['prompt'])
        self.assertNotIn('hand-painted', current_request_record['prompt'])
        self.assertIn('Output RGBA', current_request_record['prompt'])
        self.assertLess(current_request_record['qwen21']['prompt_word_count'], 100)
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            current_saved_record = {**current_request_record, **save_three_reference_inputs(current_job_root, current_request_record)}
            current_saved_record.pop('images')
            verify_qwen_saved_request(current_job_root, current_saved_record)
            current_saved_record['qwen21']['prompt_options']['transparent_background'] = False
            with self.assertRaises(ValueError):
                verify_qwen_saved_request(current_job_root, current_saved_record)
        for current_invalid_options in ({'common_style': 'true'}, {'transparent_background': 1}, {'common_style': True, 'prompt': 'word '*90}):
            with self.assertRaises(ValueError):
                validate_qwen_plain_request({**self.create_reference_request(), **current_invalid_options})

    def test_cli_prompt_options(self):
        with patch('tools.review.common.management_gateway.execute_management_command', return_value={'id':'test'}) as current_gateway_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('qwen-21',['generate','--detach','--prompt','One tree.','--common-style','--transparent-background'])
        current_payload_record = current_gateway_mock.call_args.args[2]
        self.assertTrue(current_payload_record['common_style'])
        self.assertTrue(current_payload_record['transparent_background'])
        self.assertIn('Output RGBA',validate_qwen_plain_request(current_payload_record)['prompt'])
