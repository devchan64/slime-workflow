"""격리 작업·모의 GPU 표본으로 공용 실행 기록을 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common.queue_generation_telemetry import QueueGenerationTelemetry,read_queue_generation_metrics
from tools.review.domains.image.image_generation import ImageGenerationManager
from tools.review.domains.anny.anny_attributes import read_anny_generation_status


class QueueGenerationTelemetryTests(unittest.TestCase):
    def test_different_worker_options_do_not_share_duration_samples(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)/'job';current_job_root.mkdir()
            (current_job_root/'attributes.json').write_text('{}')
            current_command_path=current_job_root/'gpu-command.json'
            current_command_path.write_text(json.dumps({'command':['python','worker.py','--preview',str(current_job_root)]}))
            with patch.object(QueueGenerationTelemetry,'capture_generation_memory'):
                current_preview_recorder=QueueGenerationTelemetry(current_job_root,'worker.py')
                current_preview_recorder.finish_generation_telemetry('completed')
                current_command_path.write_text(json.dumps({'command':['python','worker.py','--render',str(current_job_root)]}))
                current_render_recorder=QueueGenerationTelemetry(current_job_root,'worker.py')
            self.assertEqual(current_render_recorder.historical_duration_values,[])
            self.assertNotEqual(current_preview_recorder.current_run_state['input_signature'],current_render_recorder.current_run_state['input_signature'])

    def test_attempt_history_terminal_state_and_status_contract(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)/'job';current_job_root.mkdir()
            (current_job_root/'request.json').write_text('{"steps":40}')
            (current_job_root/'status.json').write_text('{"status":"running"}')
            with patch.object(QueueGenerationTelemetry,'capture_generation_memory'):
                current_first_recorder=QueueGenerationTelemetry(current_job_root,'test')
                current_first_recorder.start_generation_telemetry()
                current_first_recorder.finish_generation_telemetry('completed')
                current_first_path=current_first_recorder.current_attempt_root/'metrics.json'
                self.assertEqual(json.loads(current_first_path.read_text())['status'],'completed')
                current_next_recorder=QueueGenerationTelemetry(current_job_root,'test')
                self.assertEqual(len(current_next_recorder.historical_duration_values),1)
                current_next_recorder.start_generation_telemetry()
                current_next_recorder.finish_generation_telemetry('failed')
            self.assertNotEqual(current_first_recorder.current_attempt_root,current_next_recorder.current_attempt_root)
            self.assertTrue(current_first_path.exists())
            current_metrics_record=read_queue_generation_metrics(current_job_root)
            self.assertEqual(current_metrics_record['status'],'failed')
            current_status_record=ImageGenerationManager().read_generation_status_record(current_job_root)
            self.assertEqual(current_status_record['metrics'],current_metrics_record)
            self.assertEqual(read_anny_generation_status(current_job_root)['metrics'],current_metrics_record)
            (current_job_root/'status.json').write_text('{"status":"queued"}')
            self.assertNotIn('metrics',ImageGenerationManager().read_generation_status_record(current_job_root))
            self.assertNotIn('metrics',read_anny_generation_status(current_job_root))

    def test_unmeasured_gpu_is_not_zero_and_bad_attempt_path_rejected(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)
            current_recorder_value=QueueGenerationTelemetry(current_job_root,'test')
            with patch.object(current_recorder_value,'sample_generation_memory',side_effect=OSError('GPU 조회 불가')):
                current_recorder_value.capture_generation_memory()
            current_recorder_value.save_generation_metrics()
            current_metrics_record=read_queue_generation_metrics(current_job_root)
            self.assertEqual(current_metrics_record['gpu_observations'],{})
            self.assertIn('GPU 조회 불가',current_metrics_record['measurement_gaps'][0]['error'])
            (current_job_root/'queue-telemetry.json').write_text('{"attempt_id":"../outside"}')
            with self.assertRaises(ValueError):read_queue_generation_metrics(current_job_root)


class QueueExecutionTelemetryTests(unittest.TestCase):
    def test_executor_preserves_observations_for_terminal_states(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from tools.review.common import gpu_job_queue
        for current_status_name,current_exit_code in [('completed',0),('failed',1),('cancelled',0),('paused',0)]:
            with self.subTest(status=current_status_name),tempfile.TemporaryDirectory() as current_directory_name,ExitStack() as current_patch_stack:
                current_storage_root=Path(current_directory_name)
                current_job_root=current_storage_root/'job';current_job_root.mkdir()
                current_queue_root=current_storage_root/'queue'
                (current_job_root/'gpu-command.json').write_text(json.dumps({'service':'image','command':['mock-worker']}))
                (current_job_root/'request.json').write_text('{"steps":40}')
                def create_mock_worker(*current_argument_values,**current_keyword_values):
                    if current_status_name=='cancelled':(current_job_root/'cancel.request').touch()
                    if current_status_name=='paused':(current_job_root/'stage-pause.json').write_text('{}')
                    return SimpleNamespace(pid=999999,returncode=current_exit_code,poll=lambda:current_exit_code)
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root))
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'read_gpu_memory',return_value=(8192,8192)))
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'estimate_required_memory',return_value={'required_memory_mib':1,'samples':0}))
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'select_runnable_ticket',side_effect=lambda *_:next(current_queue_root.glob('*.json'))))
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'reload_waiting_executor'))
                current_patch_stack.enter_context(patch.object(gpu_job_queue.subprocess,'Popen',side_effect=create_mock_worker))
                current_patch_stack.enter_context(patch.object(gpu_job_queue,'save_memory_observation',return_value={'samples':0}))
                current_patch_stack.enter_context(patch('signal.signal'))
                current_patch_stack.enter_context(patch.object(QueueGenerationTelemetry,'capture_generation_memory'))
                self.assertEqual(gpu_job_queue.execute_queued_generation(current_job_root),current_exit_code)
                self.assertEqual(read_queue_generation_metrics(current_job_root)['status'],current_status_name)
                self.assertEqual(list((current_queue_root/'active').glob('*.json')),[])
