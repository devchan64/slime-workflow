"""Qwen 2511 실제 실행 함수의 공용 기록 연결을 GPU 없이 검증한다."""
import contextlib
import json
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from PIL import Image
from generators.animation.qwen_pose import runtime
from tools.review.common.queue_generation_telemetry import QueueGenerationTelemetry
from tools.review.common.worker_generation_progress import WorkerGenerationProgress


class QwenWorkerProgressTests(unittest.TestCase):
    def test_pipeline_progress_records_current_queue_attempt(self):
        self.verify_pipeline_progress_records(False)

    def test_failed_pipeline_preserves_progress_and_releases_lock(self):
        self.verify_pipeline_progress_records(True)

    def verify_pipeline_progress_records(self,current_failure_enabled):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'.tmp/job'
            current_job_path.mkdir(parents=True)
            current_model_path=current_root_path/'model'
            current_model_path.mkdir()
            (current_model_path/'model_index.json').write_text('{}')
            current_queue_recorder=QueueGenerationTelemetry(current_job_path,'isolated-qwen2511')
            current_observed_steps=[]
            current_inference_records=[]
            current_heartbeat_event=threading.Event()
            current_original_writer=WorkerGenerationProgress.record_worker_progress

            def record_observed_progress(current_writer_instance,current_progress_record):
                current_original_writer(current_writer_instance,current_progress_record)
                if current_progress_record['stage']=='inference' and current_progress_record['step']==0:
                    current_inference_records.append(json.loads((current_job_path/'worker-progress.json').read_text()))
                    if len(current_inference_records)>=2:
                        current_heartbeat_event.set()

            current_pipeline_module=types.ModuleType('diffusers.pipelines.qwenimage.pipeline_qwenimage_edit_plus')
            current_pipeline_module.VAE_IMAGE_SIZE=1024*1024

            class FakeImagePipeline:
                vae=types.SimpleNamespace(enable_slicing=lambda:None,enable_tiling=lambda:None)

                @classmethod
                def from_pretrained(cls,*current_argument_values,**current_keyword_values):
                    self.assertEqual(json.loads((current_job_path/'worker-progress.json').read_text())['stage'],'load')
                    return cls()

                def enable_sequential_cpu_offload(current_pipeline_self):
                    pass

                def __call__(current_pipeline_self,**current_input_values):
                    self.assertTrue(current_heartbeat_event.wait(8),'추론 대기 중 실제 heartbeat 기록이 필요합니다.')
                    for current_step_index in range(4):
                        current_input_values['callback_on_step_end'](current_pipeline_self,current_step_index,None,{})
                        current_queue_recorder.save_generation_metrics()
                        current_metrics_record=json.loads((current_queue_recorder.current_attempt_root/'metrics.json').read_text())
                        current_observed_steps.append(current_metrics_record['worker_progress']['step'])
                        if current_failure_enabled and current_step_index==1:
                            raise RuntimeError('격리 추론 실패')
                    return types.SimpleNamespace(images=[Image.new('RGB',(512,512))])

            current_torch_module=types.SimpleNamespace(__version__='isolated',cuda=types.SimpleNamespace(is_available=lambda:True),bfloat16='bf16',inference_mode=contextlib.nullcontext,Generator=lambda **current_generator_options:types.SimpleNamespace(manual_seed=lambda current_seed_value:None))
            current_diffusers_module=types.ModuleType('diffusers')
            current_diffusers_module.__version__='0.37.0'
            current_diffusers_module.QwenImageEditPlusPipeline=FakeImagePipeline
            current_diffusers_module.QwenImagePipeline=FakeImagePipeline
            current_qwen_module=types.ModuleType('diffusers.pipelines.qwenimage')
            current_qwen_module.pipeline_qwenimage_edit_plus=current_pipeline_module
            with patch.dict('sys.modules',{'torch':current_torch_module,'diffusers':current_diffusers_module,'diffusers.pipelines':types.ModuleType('diffusers.pipelines'),'diffusers.pipelines.qwenimage':current_qwen_module}),patch.object(runtime,'WORKFLOW_REPO_ROOT',current_root_path),patch.object(runtime,'FIXED_MODEL_DIRECTORY',current_model_path),patch.object(WorkerGenerationProgress,'record_worker_progress',record_observed_progress),patch.object(runtime.subprocess,'run',side_effect=OSError('격리 GPU 상태 조회 실패')):
                with self.assertRaisesRegex(RuntimeError,'격리 추론 실패') if current_failure_enabled else contextlib.nullcontext():
                    runtime.execute_pose_generation(trial_output_root=current_job_path,prompt_text_value='Change expression.',character_image_path='unused.png',pose_reference_kind='rig',enable_text_only_generation=True,selected_inference_steps=4)
            self.assertEqual(current_observed_steps,[1,2] if current_failure_enabled else [1,2,3,4])
            self.assertNotEqual(current_inference_records[0]['updated_at'],current_inference_records[1]['updated_at'])
            current_final_progress=json.loads((current_job_path/'worker-progress.json').read_text())
            self.assertEqual((current_final_progress['stage'],current_final_progress['step_total']),('inference' if current_failure_enabled else 'complete',4))
            self.assertEqual(current_final_progress['step'],2 if current_failure_enabled else 4)
            self.assertEqual((current_job_path/'result.png').exists(),not current_failure_enabled)
            self.assertEqual((current_job_path/'result.json').exists(),not current_failure_enabled)
            self.assertEqual(current_pipeline_module.VAE_IMAGE_SIZE,1024*1024)
            self.assertFalse(runtime.PIPELINE_EXECUTION_LOCK.locked())
