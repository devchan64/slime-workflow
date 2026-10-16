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
    def test_structured_worker_progress_persists_without_attempt_pointer(self):
        from tools.review.common.worker_generation_progress import WorkerGenerationProgress
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            current_queue_recorder = QueueGenerationTelemetry(current_job_root, 'qwen')
            current_progress_writer = WorkerGenerationProgress(current_job_root)
            for current_stage_name, current_step_number in (('loading', 0), ('inference', 7), ('postprocess', 40)):
                current_progress_writer.record_worker_progress({'stage': current_stage_name, 'step': current_step_number, 'total': 40})
                current_queue_recorder.save_generation_metrics()
                current_saved_metrics = read_queue_generation_metrics(current_job_root)
                self.assertEqual(current_saved_metrics['stage'], current_stage_name)
                self.assertEqual(current_saved_metrics['worker_progress']['step'], current_step_number)
                self.assertEqual(current_saved_metrics['worker_progress']['total'], 40)
                self.assertEqual(current_saved_metrics['step_total'], 0)
            current_next_recorder = QueueGenerationTelemetry(current_job_root, 'qwen')
            current_next_recorder.save_generation_metrics()
            self.assertNotIn('worker_progress', read_queue_generation_metrics(current_job_root))
            self.assertEqual(read_queue_generation_metrics(current_job_root)['stage'], 'worker')
            current_previous_bytes = (current_job_root/'worker-progress.json').read_bytes()
            for current_invalid_record in ({'stage':'', 'step':0,'total':40}, {'stage':'inference','step':True,'total':40}, {'stage':'inference','step':41,'total':40}):
                with self.assertRaises(ValueError):
                    current_progress_writer.record_worker_progress(current_invalid_record)
                self.assertEqual((current_job_root/'worker-progress.json').read_bytes(), current_previous_bytes)

    def test_failed_sample_invalidates_current_values_but_preserves_peak(self):
        from tools.review.common.generation_status_display import describe_generation_status
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_recorder_value=QueueGenerationTelemetry(Path(current_directory_name),'test')
            current_recorder_value.current_run_state['gpu_observations']={'GPU-A':{'process_current_mib':120,'device_current_mib':400,'process_peak_mib':200,'device_peak_mib':500,'sample_count':2}}
            with patch.object(current_recorder_value,'sample_generation_memory',side_effect=OSError('GPU 조회 권한 오류')):
                current_recorder_value.capture_generation_memory()
            current_recorder_value.save_generation_metrics()
            current_metrics_record=read_queue_generation_metrics(Path(current_directory_name))
            current_device_record=current_metrics_record['gpu_observations']['GPU-A']
            self.assertIsNone(current_device_record['process_current_mib'])
            self.assertIsNone(current_device_record['device_current_mib'])
            self.assertEqual(current_device_record['process_peak_mib'],200)
            self.assertEqual(current_device_record['device_peak_mib'],500)
            self.assertEqual(current_device_record['sample_count'],2)
            current_display_text=describe_generation_status({'status':'running','metrics':current_metrics_record})
            self.assertIn('현재 미측정 · 관측 피크 200 MiB',current_display_text)
            self.assertIn('GPU 조회 권한 오류',current_display_text)
            import os
            with patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=['GPU-A, 300',f'GPU-A, {os.getpid()}, 80']):
                current_recorder_value.sample_generation_memory()
            current_device_record=current_recorder_value.current_run_state['gpu_observations']['GPU-A']
            self.assertEqual(current_device_record['process_current_mib'],80)
            self.assertEqual(current_device_record['process_peak_mib'],200)
            self.assertIsNone(current_device_record['measurement_reason'])
            self.assertEqual(current_device_record['sample_count'],3)
            self.assertEqual(len(current_recorder_value.current_run_state['measurement_gaps']),1)


    def test_empty_device_sample_records_measurement_gap(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_recorder_value=QueueGenerationTelemetry(Path(current_directory_name),'test')
            with patch('tools.review.common.generation_telemetry.subprocess.check_output',return_value=''):
                current_recorder_value.capture_generation_memory()
            self.assertEqual(current_recorder_value.current_run_state['gpu_observations'],{})
            self.assertIn('장치 표본이 비어',current_recorder_value.current_run_state['measurement_gaps'][0]['error'])

    def test_nested_worker_stage_requires_current_execution(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            current_recorder_value = QueueGenerationTelemetry(current_job_root, 'hy-motion')
            current_worker_status = {'status': 'running', 'started_at': '2000-01-01T00:00:00+00:00', 'stage': 'old-export', 'progress': {'stage': 'render'}}
            current_status_path = current_job_root/'status.json'
            current_status_path.write_text(json.dumps(current_worker_status))
            current_recorder_value.save_generation_metrics()
            self.assertEqual(read_queue_generation_metrics(current_job_root)['stage'], 'worker')
            current_worker_status['started_at'] = current_recorder_value.current_run_state['started_at']
            for current_stage_name in ('inference', 'render', 'export'):
                current_worker_status['progress']['stage'] = current_stage_name
                current_status_path.write_text(json.dumps(current_worker_status))
                current_recorder_value.save_generation_metrics()
                current_metrics_record = read_queue_generation_metrics(current_job_root)
                self.assertEqual(current_metrics_record['stage'], current_stage_name)
                self.assertEqual(current_metrics_record['step_total'], 0)
            with patch.object(current_recorder_value, 'capture_generation_memory'):
                current_recorder_value.finish_generation_telemetry('cancelled')
            self.assertEqual(read_queue_generation_metrics(current_job_root)['stage'], 'cancelled')

    def test_worker_stage_tracks_only_current_attempt(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            current_recorder_value = QueueGenerationTelemetry(current_job_root, 'test')
            current_attempt_root = current_job_root/'attempts'/('a'*32)
            current_attempt_root.mkdir(parents=True)
            (current_job_root/'current-attempt.json').write_text(json.dumps({'id': 'a'*32}))
            current_worker_record = {'started_at': '2000-01-01T00:00:00+00:00', 'stage': 'inference', 'step': 12, 'step_total': 40, 'updated_at': '2000-01-01T00:01:00+00:00'}
            current_metrics_path = current_attempt_root/'metrics.json'
            current_metrics_path.write_text(json.dumps(current_worker_record))
            current_recorder_value.save_generation_metrics()
            self.assertNotIn('worker_progress', read_queue_generation_metrics(current_job_root))
            current_worker_record['started_at'] = current_recorder_value.current_run_state['started_at']
            current_worker_record['updated_at'] = current_worker_record['started_at']
            current_metrics_path.write_text(json.dumps(current_worker_record))
            current_recorder_value.save_generation_metrics()
            current_queue_record = read_queue_generation_metrics(current_job_root)
            self.assertEqual(current_queue_record['stage'], 'inference')
            self.assertEqual(current_queue_record['worker_progress']['step'], 12)
            self.assertEqual(current_queue_record['worker_progress']['total'], 40)
            self.assertEqual(current_queue_record['step_total'], 0)
            for current_stage_name in ('model-load', 'export'):
                current_worker_record.update(stage=current_stage_name, step=0, step_total=1)
                current_metrics_path.write_text(json.dumps(current_worker_record))
                current_recorder_value.save_generation_metrics()
                current_stage_record = read_queue_generation_metrics(current_job_root)
                self.assertEqual(current_stage_record['worker_progress']['stage'], current_stage_name)
                self.assertEqual(current_stage_record['worker_progress']['scope'], '작업자 현재 단계; 전체 작업 진행률과 구분')
                self.assertEqual(current_stage_record['step_total'], 0)
            with patch.object(current_recorder_value, 'capture_generation_memory'):
                current_recorder_value.finish_generation_telemetry('failed')
            self.assertEqual(read_queue_generation_metrics(current_job_root)['stage'], 'failed')

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
                current_record_writer = gpu_job_queue.write_record_atomically
                def verify_running_publication(current_record_path, current_record_value):
                    if current_record_path == current_job_root / 'status.json' and current_record_value['status'] == 'running':
                        current_metrics_record = read_queue_generation_metrics(current_job_root)
                        self.assertIsNotNone(current_metrics_record)
                        self.assertEqual(current_metrics_record['status'], 'running')
                    current_record_writer(current_record_path, current_record_value)
                current_patch_stack.enter_context(patch.object(gpu_job_queue, 'write_record_atomically', side_effect=verify_running_publication))
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


class GenerationMemoryScopeTests(unittest.TestCase):
    def test_missing_device_preserves_peak_and_recovers_independently(self):
        import os
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_recorder_value=GenerationTelemetryRecorder(Path(current_directory_name),0,[])
            current_process_number=os.getpid()
            current_mock_samples=['GPU-A, 900\nGPU-B, 700',f'GPU-A, {current_process_number}, 100\nGPU-B, {current_process_number}, 200',
                'GPU-A, 800',f'GPU-A, {current_process_number}, 90',
                'GPU-A, 850\nGPU-B, 650',f'GPU-A, {current_process_number}, 95\nGPU-B, {current_process_number}, 180']
            with patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=current_mock_samples):
                current_recorder_value.sample_generation_memory()
                current_recorder_value.sample_generation_memory()
                current_device_records=current_recorder_value.current_run_state['gpu_observations']
                self.assertEqual(current_device_records['GPU-A']['process_current_mib'],90)
                self.assertIsNone(current_device_records['GPU-B']['process_current_mib'])
                self.assertIsNone(current_device_records['GPU-B']['device_current_mib'])
                self.assertEqual(current_device_records['GPU-B']['process_peak_mib'],200)
                self.assertEqual(current_device_records['GPU-B']['sample_count'],1)
                self.assertIn('GPU-B',current_recorder_value.current_run_state['measurement_gaps'][0]['error'])
                current_recorder_value.sample_generation_memory()
                self.assertEqual(current_device_records['GPU-B']['process_current_mib'],180)
                self.assertEqual(current_device_records['GPU-B']['process_peak_mib'],200)
                self.assertEqual(current_device_records['GPU-B']['sample_count'],2)
                self.assertIsNone(current_device_records['GPU-B']['measurement_reason'])

    def test_invalid_device_snapshot_does_not_commit_partial_peaks(self):
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            for current_invalid_snapshot in ('GPU-A, 100\nGPU-B, N/A','GPU-A, 100\nGPU-A, 200','GPU-A, -1',', 100'):
                with self.subTest(snapshot=current_invalid_snapshot):
                    current_recorder_value=GenerationTelemetryRecorder(Path(current_directory_name),0,[])
                    with patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=[current_invalid_snapshot,'']):
                        current_recorder_value.capture_generation_memory()
                    self.assertEqual(current_recorder_value.current_run_state['gpu_observations'],{})
                    self.assertEqual(len(current_recorder_value.current_run_state['measurement_gaps']),1)

    def test_invalid_process_usage_preserves_previous_peak(self):
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            for current_process_snapshot in ('GPU-A, 100, -1', ', 100, 20', 'GPU-A, 100, N/A', 'GPU-A, 100, 300\nGPU-A, 100, 300', 'GPU-B, 100, 300'):
                with self.subTest(snapshot=current_process_snapshot):
                    current_recorder_value=GenerationTelemetryRecorder(Path(current_directory_name),0,[])
                    with patch('tools.review.common.generation_telemetry.os.getpid',return_value=100), patch('tools.review.common.generation_telemetry.Path.glob',return_value=[]), patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=['GPU-A, 500','GPU-A, 100, 200','GPU-A, 600',current_process_snapshot]):
                        current_recorder_value.sample_generation_memory()
                        current_recorder_value.capture_generation_memory()
                    current_device_record=current_recorder_value.current_run_state['gpu_observations']['GPU-A']
                    self.assertIsNone(current_device_record['process_current_mib'])
                    self.assertEqual(current_device_record['process_peak_mib'],200)
                    self.assertEqual(current_device_record['device_peak_mib'],500)
                    self.assertEqual(current_device_record['sample_count'],1)
                    self.assertEqual(len(current_recorder_value.current_run_state['measurement_gaps']),1)

    def test_descendants_and_devices_keep_separate_observed_peaks(self):
        """별도 렌더 자손은 포함하고 타 작업과 장치 피크 합산은 제외한다."""
        from types import SimpleNamespace
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        current_process_records = [
            SimpleNamespace(parent=SimpleNamespace(name=str(current_process_number)),
                            read_text=lambda current_parent_number=current_parent_number: f'0 (render worker) S {current_parent_number} 0')
            for current_process_number, current_parent_number in ((101, 100), (102, 101), (200, 1))
        ]
        current_gpu_samples = [
            'GPU-A, 900\nGPU-B, 700',
            'GPU-A, 100, 10\nGPU-A, 101, 20\nGPU-A, 102, 30\nGPU-A, 200, 800\nGPU-B, 102, 40',
            'GPU-A, 850\nGPU-B, 950',
            'GPU-A, 100, 5\nGPU-A, 101, 10\nGPU-B, 102, 80\nGPU-B, 200, 870',
        ]
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_recorder_value = GenerationTelemetryRecorder(Path(current_directory_name), 0, [])
            with patch('tools.review.common.generation_telemetry.os.getpid', return_value=100), \
                 patch('tools.review.common.generation_telemetry.Path.glob', return_value=current_process_records), \
                 patch('tools.review.common.generation_telemetry.subprocess.check_output', side_effect=current_gpu_samples):
                current_recorder_value.sample_generation_memory()
                current_recorder_value.sample_generation_memory()
            current_gpu_observations = current_recorder_value.current_run_state['gpu_observations']
            self.assertEqual(current_gpu_observations['GPU-A']['process_current_mib'], 15)
            self.assertEqual(current_gpu_observations['GPU-A']['process_peak_mib'], 60)
            self.assertEqual(current_gpu_observations['GPU-A']['device_peak_mib'], 900)
            self.assertEqual(current_gpu_observations['GPU-B']['process_current_mib'], 80)
            self.assertEqual(current_gpu_observations['GPU-B']['process_peak_mib'], 80)
            self.assertEqual(current_gpu_observations['GPU-B']['device_peak_mib'], 950)
            self.assertTrue(all(current_gpu_record['sample_count'] == 2 for current_gpu_record in current_gpu_observations.values()))
            current_recorder_value.save_generation_metrics()
            current_saved_record = json.loads((Path(current_directory_name) / 'metrics.json').read_text())
            self.assertEqual(current_saved_record['gpu_observations'], current_gpu_observations)


class WorkerStepTelemetryTests(unittest.TestCase):
    def test_step_denominator_survives_stage_and_terminal_changes(self):
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root = Path(current_directory_name)
            current_recorder_value = GenerationTelemetryRecorder(current_attempt_root, 40, [])
            with patch.object(current_recorder_value, 'capture_generation_memory'):
                current_recorder_value.update_generation_stage('inference')
                current_recorder_value.record_generation_step(20)
                current_metrics_record = json.loads((current_attempt_root / 'metrics.json').read_text())
                self.assertEqual((current_metrics_record['step'], current_metrics_record['step_total']), (20, 40))
                self.assertEqual(current_metrics_record['stage'], 'inference')
                current_recorder_value.update_generation_stage('saving')
                current_recorder_value.finish_generation_telemetry('failed')
            current_metrics_record = json.loads((current_attempt_root / 'metrics.json').read_text())
            self.assertEqual((current_metrics_record['step'], current_metrics_record['step_total']), (20, 40))
            self.assertEqual(current_metrics_record['status'], 'failed')


class WorkerAttemptStatusTests(unittest.TestCase):
    def test_resumed_service_ignores_previous_worker_metrics(self):
        from tools.review.domains.vace.generation import VaceGenerationManager
        from tools.review.domains.phantom.generation import PhantomGenerationManager
        for current_manager_type in (VaceGenerationManager, PhantomGenerationManager):
            with self.subTest(service=current_manager_type.__name__), tempfile.TemporaryDirectory() as current_directory_name:
                current_job_root = Path(current_directory_name)
                current_attempt_root = current_job_root / 'attempts' / ('a' * 32)
                current_attempt_root.mkdir(parents=True)
                (current_job_root / 'status.json').write_text('{"status":"running"}')
                (current_job_root / 'request.json').write_text('{"steps":40}')
                (current_job_root / 'current-attempt.json').write_text(json.dumps({'id': 'a' * 32}))
                current_queue_metrics = {'started_at': '2026-10-15T12:00:00+09:00', 'stage': 'worker', 'estimate': {'remaining': None}}
                current_worker_metrics = {'started_at': '2026-10-15T11:00:00+09:00', 'stage': 'completed', 'step': 40, 'estimate': {'remaining': 0}}
                with patch('tools.review.common.queue_generation_telemetry.read_queue_generation_metrics', return_value=current_queue_metrics):
                    for current_started_value in (None, '2026-10-15T11:00:00+09:00', '2026-10-15T03:00:01+00:00'):
                        current_worker_metrics['started_at'] = current_started_value
                        (current_attempt_root / 'metrics.json').write_text(json.dumps(current_worker_metrics))
                        current_status_record = current_manager_type().read_generation_status_record(current_job_root)
                        if current_started_value == '2026-10-15T03:00:01+00:00':
                            self.assertEqual(current_status_record['worker_metrics'], current_worker_metrics)
                            self.assertEqual(current_status_record['metrics'], current_queue_metrics)
                            self.assertEqual(current_status_record['estimate'], current_queue_metrics['estimate'])
                        else:
                            self.assertEqual(current_status_record['metrics'], current_queue_metrics)
                            self.assertIsNone(current_status_record['estimate']['remaining'])
                self.assertTrue((current_attempt_root / 'metrics.json').exists())


class TelemetryHeartbeatCadenceTests(unittest.TestCase):
    def test_sampling_duration_is_subtracted_from_heartbeat_wait(self):
        from unittest.mock import Mock, call
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_recorder_value = GenerationTelemetryRecorder(Path(current_directory_name), 0, [])
            current_stop_event = Mock()
            current_stop_event.is_set.side_effect = [False, False, False, True]
            current_recorder_value.current_stop_event = current_stop_event
            with patch.object(current_recorder_value, 'capture_generation_memory') as current_capture_mock, \
                 patch.object(current_recorder_value, 'save_generation_metrics') as current_save_mock, \
                 patch('tools.review.common.generation_telemetry.time.monotonic', side_effect=[0, 2, 5, 9, 10, 16]):
                current_recorder_value.run_telemetry_heartbeat()
            self.assertEqual(current_stop_event.wait.call_args_list, [call(3), call(1), call(0)])
            self.assertEqual(current_capture_mock.call_count, 3)
            self.assertEqual(current_save_mock.call_count, 3)
