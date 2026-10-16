"""공용 상태 표시는 서비스 값을 유지하며 미측정과 0을 구분한다."""
import unittest
from tools.review.common.generation_status_display import describe_generation_status


class GenerationStatusDisplayTests(unittest.TestCase):
    def test_video_duration_rejects_empty_and_invalid_frame_counts(self):
        from tools.review.common.gradio_video_results import describe_video_frame_duration
        for current_frame_count in (None, '', True, 0, 2, 162, 5.5, float('nan'), float('inf')):
            with self.subTest(frames=current_frame_count):
                self.assertIn('입력하세요', describe_video_frame_duration(current_frame_count))
        self.assertEqual(describe_video_frame_duration(81), '81프레임 · 약 5.06초 · 16fps')
        self.assertEqual(describe_video_frame_duration(37.0), '37프레임 · 약 2.31초 · 16fps')

    def test_measurement_failure_persists_and_displays_previous_peak(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_attempt_root=Path(current_directory_name)
            current_recorder_value=GenerationTelemetryRecorder(current_attempt_root,0,[])
            with patch('tools.review.common.generation_telemetry.os.getpid',return_value=100), patch('tools.review.common.generation_telemetry.Path.glob',return_value=[]), patch('tools.review.common.generation_telemetry.subprocess.check_output',side_effect=['GPU-A, 500','GPU-A, 100, 200','GPU-A, 600','GPU-A, 100, 300\nGPU-A, 100, 300']):
                current_recorder_value.capture_generation_memory()
                current_recorder_value.finish_generation_telemetry('failed')
            current_saved_metrics=json.loads((current_attempt_root/'metrics.json').read_text())
            self.assertEqual(current_saved_metrics['status'],'failed')
            current_display_text=describe_generation_status({'status':'failed','metrics':current_saved_metrics})
            for current_expected_text in ('현재 미측정','관측 피크 200 MiB','장치·PID가 중복','미측정 구간','순간 피크'):
                self.assertIn(current_expected_text,current_display_text)
            self.assertNotIn('600 MiB',current_display_text)
            self.assertNotIn('현재 0 MiB',current_display_text)

    def test_missing_media_result_matches_terminal_status(self):
        from tools.review.common.gradio_audio_results import render_audio_generation_result
        from tools.review.common.gradio_video_results import render_video_generation_result
        for current_renderer_function in (render_audio_generation_result,render_video_generation_result):
            for current_status_name in ('completed','failed','cancelled','interrupted'):
                with self.subTest(renderer=current_renderer_function.__name__,status=current_status_name):
                    current_result_text=current_renderer_function('job-a',{'status':current_status_name},'http://localhost')
                    self.assertIn('실행 로그를 확인',current_result_text)
                    self.assertNotIn('생성 완료 후',current_result_text)
                    self.assertNotIn('<video',current_result_text)
                    self.assertNotIn('<audio',current_result_text)
            self.assertIn('생성 완료 후',current_renderer_function('job-a',{'status':'queued'},'http://localhost'))
        self.assertIn('모델 준비가 완료',render_audio_generation_result('job-a',{'status':'completed','result':{'prepared':True}},'http://localhost'))

    def test_queue_worker_progress_preserves_terminal_stage(self):
        current_worker_progress = {'stage': 'inference', 'step': 12, 'total': 40, 'updated_at': '2026-10-15T13:00:00+09:00'}
        current_status_record = {'status': 'failed', 'metrics': {'stage': 'failed', 'worker_progress': current_worker_progress}}
        current_status_text = describe_generation_status(current_status_record)
        for current_expected_text in ('단계: failed', '작업자 마지막 관측: inference', '12/40', '전체 예상 진행률과 별개', current_worker_progress['updated_at']):
            self.assertIn(current_expected_text, current_status_text)
        self.assertNotIn('30%', current_status_text)
        current_worker_progress['scope'] = '완료한 파이프라인 단계 수'
        self.assertIn('관측 범위: 완료한 파이프라인 단계 수', describe_generation_status(current_status_record))
        current_status_record['progress'] = {'stage': 'saving', 'step': 1, 'total': 2}
        self.assertNotIn('작업자 마지막 관측', describe_generation_status(current_status_record))

    def test_audio_and_video_share_missing_memory_and_failure_display(self):
        from tools.review.common.gradio_audio_results import describe_audio_generation_status
        from tools.review.common.gradio_video_results import describe_video_generation_status
        current_status_record={'status':'failed','error':'작업 실패','progress':{'total':40},'metrics':{'step':12,'gpu_observations':{'gpu':{'process_current_mib':None,'process_peak_mib':250,'scope':'자식 포함'}}}}
        for current_display_function in (describe_audio_generation_status,describe_video_generation_status):
            current_display_text=current_display_function(current_status_record)
            for current_expected_text in ('현재 미측정','250 MiB','순간 피크','작업 실패','12/40'):
                self.assertIn(current_expected_text,current_display_text)
            self.assertNotIn('None MiB',current_display_text)


    def test_running_preserves_service_estimate(self):
        current_status_text = describe_generation_status({'status':'running','estimate':{'remaining':23,'completion':'2026-10-15T12:00:00+09:00','total_seconds':100,'estimated_progress':77,'sample_count':3,'basis':'같은 설정','scope':'전체'},'progress':{'step':2,'total':40}})
        for current_expected_text in ('23초','77%','3개','같은 설정','12:00:00','2/40','전체 예상 진행률과 별개'):
            self.assertIn(current_expected_text,current_status_text)

    def test_terminal_none_error_and_missing_metrics(self):
        for current_status_name in ('completed','cancelled','failed'):
            current_status_text = describe_generation_status({'status':current_status_name,'error':None})
            self.assertIn('예상 시간 갱신 종료',current_status_text)
            self.assertIn('측정 자료 없음',current_status_text)
            self.assertNotIn('None',current_status_text)

    def test_zero_memory_and_missing_memory_are_distinct(self):
        current_status_text = describe_generation_status({'status':'failed','error':'CUDA out of memory','metrics':{'gpu_observations':{'gpu':{'process_current_mib':0,'process_peak_mib':None,'scope':'작업자'}},'measurement_gaps':[{'error':'측정 실패'}]}})
        for current_expected_text in ('현재 0 MiB','관측 피크 미측정','작업자','미측정 구간','CUDA out of memory'):
            self.assertIn(current_expected_text,current_status_text)

    def test_queued_has_no_fabricated_estimate(self):
        current_status_text = describe_generation_status({'status':'queued'})
        self.assertIn('계산 중',current_status_text)
        self.assertNotIn('100%',current_status_text)

    def test_tile_estimate_uses_common_schema_without_request_mtime(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.review.domains.tile.tile_generation import TileGenerationManager
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_job_directory = Path(current_temporary_root)
            (current_job_directory / 'request.json').write_text(json.dumps({}))
            current_service_instance = TileGenerationManager()
            with patch.object(current_service_instance, 'list_generation_history', return_value=[]):
                current_status_record = current_service_instance.enrich_generation_status(current_job_directory, {'status':'running'})
            self.assertIsNone(current_status_record['estimate']['remaining'])
            self.assertIsNone(current_status_record['estimate']['completion'])
            self.assertIn('실행 시작 시각', current_status_record['estimate']['basis'])

    def test_worker_stage_does_not_replace_full_job_memory_and_eta(self):
        from tools.review.common.queue_generation_telemetry import merge_generation_worker_metrics
        current_queue_metrics = {'started_at':'2026-10-15T12:00:00+09:00', 'stage':'worker', 'gpu_observations':{'gpu':{'process_current_mib':300,'process_peak_mib':900,'scope':'실행기와 모든 자식'}}, 'estimate':{'remaining':23,'basis':'전체 작업'}}
        current_worker_metrics = {'started_at':'2026-10-15T12:00:01+09:00', 'stage':'inference','step':2,'step_total':40,'gpu_observations':{'gpu':{'process_peak_mib':400}},'estimate':{'remaining':12}}
        current_status_record = {'status':'running','metrics':current_queue_metrics,'estimate':current_queue_metrics['estimate'],'progress':{'stage':'inference','step':2,'total':40}}
        self.assertTrue(merge_generation_worker_metrics(current_status_record, current_worker_metrics))
        self.assertIs(current_status_record['metrics'], current_queue_metrics)
        self.assertIs(current_status_record['worker_metrics'], current_worker_metrics)
        current_status_text = describe_generation_status(current_status_record)
        for current_expected_text in ('단계: inference','2/40','관측 피크 900 MiB','23초','실행기와 모든 자식'):
            self.assertIn(current_expected_text,current_status_text)
        self.assertNotIn('400 MiB',current_status_text)
        self.assertNotIn('단계: worker',current_status_text)

    def test_video_current_worker_inference_keeps_overall_estimate(self):
        from tools.review.common.gradio_video_results import describe_video_generation_status
        from tools.review.common.queue_generation_telemetry import merge_generation_worker_metrics
        current_queue_metrics = {'started_at':'2026-10-15T12:00:00+09:00', 'estimate':{'remaining':23,'scope':'전체 작업'}, 'inference_estimate':{'remaining':None}}
        current_worker_metrics = {'started_at':'2026-10-15T12:00:01+09:00', 'estimate':{}, 'inference_estimate':{'remaining':7,'scope':'추론 종료까지', 'sample_count':5}}
        current_status_record = {'status':'running','metrics':current_queue_metrics,'estimate':current_queue_metrics['estimate']}
        self.assertTrue(merge_generation_worker_metrics(current_status_record, current_worker_metrics))
        current_status_text = describe_video_generation_status(current_status_record)
        for current_expected_text in ('23초','7초','추론 종료까지의 참고 추정','5개'):
            self.assertIn(current_expected_text, current_status_text)
        current_status_record['status'] = 'completed'
        self.assertNotIn('7초', describe_video_generation_status(current_status_record))
        current_status_record.pop('worker_metrics')
        current_status_record['status'] = 'running'
        current_worker_metrics['started_at'] = '2026-10-15T11:00:00+09:00'
        self.assertFalse(merge_generation_worker_metrics(current_status_record, current_worker_metrics))
        self.assertNotIn('7초', describe_video_generation_status(current_status_record))
