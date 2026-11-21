"""폐기된 Qwen 실행 차단과 기존 공용 진행 기록 보존을 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest

from generators.animation.qwen_pose import runtime
from tools.management.common.queue_generation_telemetry import QueueGenerationTelemetry
from tools.management.common.worker_generation_progress import WorkerGenerationProgress


class QwenWorkerProgressTests(unittest.TestCase):
    def test_retired_generation_preserves_historical_progress(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_path = Path(temporary_directory_name) / 'job'
            current_job_path.mkdir()
            current_progress_writer = WorkerGenerationProgress(current_job_path)
            current_progress_writer.record_worker_progress({'stage': 'inference', 'step': 2, 'total': 4})
            current_progress_path = current_job_path / 'worker-progress.json'
            original_progress_bytes = current_progress_path.read_bytes()
            with self.assertRaisesRegex(RuntimeError, '폐기'):
                runtime.execute_pose_generation(trial_output_root=current_job_path, prompt_text_value='test', character_image_path='unused.png', pose_reference_kind='rig')
            self.assertEqual(current_progress_path.read_bytes(), original_progress_bytes)
            self.assertFalse((current_job_path / 'result.png').exists())
            self.assertFalse((current_job_path / 'result.json').exists())
            self.assertFalse(runtime.PIPELINE_EXECUTION_LOCK.locked())

    def test_shared_recorder_reads_worker_progress(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_path = Path(temporary_directory_name) / 'job'
            current_job_path.mkdir()
            current_queue_recorder = QueueGenerationTelemetry(current_job_path, 'isolated-qwen2511')
            current_progress_writer = WorkerGenerationProgress(current_job_path)
            for current_step_number in (1, 2, 3, 4):
                current_progress_writer.record_worker_progress({'stage': 'inference', 'step': current_step_number, 'total': 4})
                current_queue_recorder.save_generation_metrics()
                current_metrics_record = json.loads((current_queue_recorder.current_attempt_root / 'metrics.json').read_text())
                self.assertEqual(current_metrics_record['worker_progress']['step'], current_step_number)
                self.assertEqual(current_metrics_record['worker_progress']['total'], 4)
