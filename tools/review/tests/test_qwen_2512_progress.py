"""Qwen 2512 추론 관측과 실패 시 마지막 진행 기록을 GPU 없이 검증한다."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from PIL import Image
from generators.image import qwen_2512
from tools.review.common.worker_generation_progress import WorkerGenerationProgress


class QwenProgressContractTests(unittest.TestCase):
    def test_inference_progress_and_failure_record(self):
        for current_failure_enabled in (False, True):
            with self.subTest(failure=current_failure_enabled), tempfile.TemporaryDirectory() as current_root_name:
                current_root_path = Path(current_root_name)
                current_output_path = current_root_path / '.tmp/test/job'
                current_output_path.mkdir(parents=True)
                current_progress_writer = WorkerGenerationProgress(current_output_path)
                current_observed_records = []

                def record_worker_observation(current_progress_record):
                    current_progress_writer.record_worker_progress(current_progress_record)
                    current_observed_records.append(dict(current_progress_record))

                class FakeImagePipeline:
                    @classmethod
                    def from_pretrained(cls, *current_argument_values, **current_keyword_values):
                        return cls()

                    def load_lora_weights(self, *current_argument_values, **current_keyword_values):
                        pass

                    def enable_sequential_cpu_offload(self):
                        pass

                    def __call__(self, **current_keyword_values):
                        for current_step_index in range(4):
                            current_keyword_values['callback_on_step_end'](self, current_step_index, None, {})
                            if current_failure_enabled and current_step_index == 1:
                                raise RuntimeError('격리 추론 실패')
                        return types.SimpleNamespace(images=[Image.new('RGB', (256,256))])

                current_torch_module = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True),bfloat16='bf16',Generator=lambda **kwargs:types.SimpleNamespace(manual_seed=lambda value:None))
                with patch.object(qwen_2512,'WORKFLOW_REPOSITORY_ROOT',current_root_path), patch.object(qwen_2512,'validate_qwen_2512_assets',return_value=(current_root_path/'model',current_root_path/'adapter')), patch.dict('sys.modules',{'torch':current_torch_module,'diffusers':types.SimpleNamespace(QwenImagePipeline=FakeImagePipeline)}):
                    current_input_values = dict(output_directory=current_output_path,prompt_text='A field.',width=256,height=256,worker_progress_callback=record_worker_observation)
                    if current_failure_enabled:
                        with self.assertRaisesRegex(RuntimeError,'격리 추론 실패'):
                            qwen_2512.generate_qwen_2512_lightning_image(**current_input_values)
                    else:
                        qwen_2512.generate_qwen_2512_lightning_image(**current_input_values)
                current_saved_record = json.loads((current_output_path/'worker-progress.json').read_text())
                self.assertEqual(current_saved_record['stage'],'inference' if current_failure_enabled else 'postprocess')
                self.assertEqual(current_saved_record['step'],2 if current_failure_enabled else 4)
                self.assertEqual(current_saved_record['step_total'],4)
                self.assertEqual([value['step'] for value in current_observed_records if value['stage']=='inference'],[0,1,2] if current_failure_enabled else [0,1,2,3,4])
                self.assertEqual((current_output_path/'result.png').exists(),not current_failure_enabled)

    def test_worker_heartbeat_failure_and_lock_release(self):
        import importlib.util
        import threading
        from generators.image import worker_lock
        current_worker_path = Path(qwen_2512.__file__).with_name('run_qwen_2512.py')
        current_module_spec = importlib.util.spec_from_file_location('isolated_qwen_worker',current_worker_path)
        current_worker_module = importlib.util.module_from_spec(current_module_spec)
        with patch.dict('sys.modules',{'qwen_2512':qwen_2512,'worker_lock':worker_lock}):
            current_module_spec.loader.exec_module(current_worker_module)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path = Path(current_root_name)
            current_job_path = current_root_path/'.tmp/test/qwen-image-2512/job'
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps(dict(action='generate',prompt='Field.',width=256,height=256,steps=4)))
            current_observed_records = []
            current_heartbeat_ready = threading.Event()
            current_original_writer = WorkerGenerationProgress.record_worker_progress
            current_lock_handles = []

            def observe_worker_progress(current_writer_instance,current_progress_record):
                current_original_writer(current_writer_instance,current_progress_record)
                current_observed_records.append(json.loads((current_job_path/'worker-progress.json').read_text()))
                if len([value for value in current_observed_records if value['stage']=='inference']) >= 2:
                    current_heartbeat_ready.set()

            def simulate_worker_inference(**current_keyword_values):
                current_keyword_values['worker_progress_callback']({'stage':'inference','step':2,'total':4})
                self.assertTrue(current_heartbeat_ready.wait(8),'5초 heartbeat 미수신')
                raise RuntimeError('격리 작업자 실패')

            def observe_worker_lock(current_lock_handle,current_wait_stage):
                current_lock_handles.append(current_lock_handle)
                self.assertEqual(current_wait_stage,'waiting-gpu')

            with patch.object(current_worker_module,'WORKFLOW_REPOSITORY_ROOT',current_root_path), patch.object(current_worker_module,'generate_qwen_2512_lightning_image',simulate_worker_inference), patch.object(current_worker_module,'acquire_worker_lock',observe_worker_lock), patch.object(WorkerGenerationProgress,'record_worker_progress',observe_worker_progress), patch.dict('sys.modules',{'torch':types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True))}), patch('sys.argv',['worker','--job-dir',str(current_job_path)]):
                with self.assertRaisesRegex(RuntimeError,'격리 작업자 실패'):
                    current_worker_module.execute_image_worker()
            self.assertTrue(current_lock_handles[0].closed)
            self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')
            self.assertEqual(current_observed_records[-1]['stage'],'inference')
            self.assertEqual(current_observed_records[-1]['step'],2)
            current_inference_records = [value for value in current_observed_records if value['stage']=='inference']
            self.assertNotEqual(current_inference_records[0]['updated_at'],current_inference_records[-1]['updated_at'])

    def test_worker_lock_setup_failure_is_recorded(self):
        import importlib.util
        from generators.image import worker_lock
        current_worker_path = Path(qwen_2512.__file__).with_name('run_qwen_2512.py')
        current_module_spec = importlib.util.spec_from_file_location('isolated_qwen_setup_worker', current_worker_path)
        current_worker_module = importlib.util.module_from_spec(current_module_spec)
        with patch.dict('sys.modules', {'qwen_2512': qwen_2512, 'worker_lock': worker_lock}):
            current_module_spec.loader.exec_module(current_worker_module)
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path = Path(current_root_name)
            current_job_path = current_root_path / '.tmp/test/qwen-image-2512/job'
            current_job_path.mkdir(parents=True)
            (current_job_path / 'request.json').write_text(json.dumps(dict(action='generate', steps=4)))
            (current_root_path / '.local').write_text('잠금 디렉터리 생성 실패를 재현하는 파일')
            with patch.object(current_worker_module, 'WORKFLOW_REPOSITORY_ROOT', current_root_path), patch.object(current_worker_module.threading, 'Thread') as current_thread_factory, patch('sys.argv', ['worker', '--job-dir', str(current_job_path)]):
                with self.assertRaises(FileExistsError):
                    current_worker_module.execute_image_worker()
                current_thread_factory.assert_not_called()
            current_status_record = json.loads((current_job_path / 'status.json').read_text())
            self.assertEqual(current_status_record['status'], 'failed')
            self.assertIn('.local', current_status_record['error'])
            self.assertEqual(json.loads((current_job_path / 'worker-progress.json').read_text())['stage'], 'cuda-check')

    def test_prepare_worker_completion_and_download_failure(self):
        import importlib.util
        from generators.image import worker_lock
        current_worker_path = Path(qwen_2512.__file__).with_name('run_qwen_2512.py')
        current_module_spec = importlib.util.spec_from_file_location('isolated_qwen_prepare_worker', current_worker_path)
        current_worker_module = importlib.util.module_from_spec(current_module_spec)
        with patch.dict('sys.modules', {'qwen_2512': qwen_2512, 'worker_lock': worker_lock}):
            current_module_spec.loader.exec_module(current_worker_module)
        for current_failure_enabled in (False, True):
            with self.subTest(failure=current_failure_enabled), tempfile.TemporaryDirectory() as current_root_name:
                current_root_path = Path(current_root_name)
                current_job_path = current_root_path / '.tmp/test/qwen-image-2512/job'
                current_job_path.mkdir(parents=True)
                (current_job_path / 'request.json').write_text(json.dumps({'action': 'prepare'}))
                current_download_calls = []
                current_lock_handles = []

                def simulate_snapshot_download(*current_arguments, **current_keywords):
                    current_download_calls.append('model')
                    if current_failure_enabled:
                        raise RuntimeError('격리 모델 다운로드 실패')

                def simulate_adapter_download(*current_arguments, **current_keywords):
                    current_download_calls.append('adapter')

                def capture_prepare_lock(current_lock_handle, current_wait_stage):
                    self.assertEqual(current_wait_stage, 'waiting-download')
                    current_lock_handles.append(current_lock_handle)

                current_fake_modules = {
                    'torch': types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True)),
                    'huggingface_hub': types.SimpleNamespace(snapshot_download=simulate_snapshot_download, hf_hub_download=simulate_adapter_download),
                }
                with patch.object(current_worker_module, 'WORKFLOW_REPOSITORY_ROOT', current_root_path), patch.object(current_worker_module, 'acquire_worker_lock', capture_prepare_lock), patch.object(current_worker_module, 'validate_qwen_2512_assets') as current_validate_assets, patch.object(current_worker_module, 'generate_qwen_2512_lightning_image') as current_generate_image, patch.dict('sys.modules', current_fake_modules), patch('sys.argv', ['worker', '--job-dir', str(current_job_path)]):
                    if current_failure_enabled:
                        with self.assertRaisesRegex(RuntimeError, '격리 모델 다운로드 실패'):
                            current_worker_module.execute_image_worker()
                        current_validate_assets.assert_not_called()
                    else:
                        current_worker_module.execute_image_worker()
                        current_validate_assets.assert_called_once_with()
                    current_generate_image.assert_not_called()
                self.assertTrue(current_lock_handles[0].closed)
                self.assertEqual(current_download_calls, ['model'] if current_failure_enabled else ['model', 'adapter'])
                self.assertEqual(json.loads((current_job_path / 'status.json').read_text())['status'], 'failed' if current_failure_enabled else 'completed')
                self.assertEqual(json.loads((current_job_path / 'worker-progress.json').read_text())['stage'], 'download-model' if current_failure_enabled else 'complete')
