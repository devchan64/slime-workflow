"""모델 작업자의 단계 관측을 공용 실행기에 원자적으로 전달한다."""
from datetime import datetime, timezone
from pathlib import Path
import threading

from tools.review.common.generation_records import write_record_atomically


class WorkerGenerationProgress:
    def __init__(self, current_job_directory):
        self.current_progress_path = Path(current_job_directory) / 'worker-progress.json'
        self.current_started_timestamp = datetime.now(timezone.utc).isoformat()
        self.current_progress_lock = threading.Lock()

    def record_worker_progress(self, current_progress_record):
        with self.current_progress_lock:
            current_progress_scope = current_progress_record.get('scope', '작업자 추론 단계; 전체 작업 진행률과 구분')
            if not isinstance(current_progress_scope, str) or not current_progress_scope.strip():
                raise ValueError('작업자 진행 범위는 비어 있지 않은 문자열이어야 합니다.')
            current_stage_name = current_progress_record.get('stage')
            current_step_number = current_progress_record.get('step')
            current_step_total = current_progress_record.get('total')
            if not isinstance(current_stage_name, str) or not current_stage_name.strip():
                raise ValueError('작업자 진행 단계는 비어 있지 않은 문자열이어야 합니다.')
            if (type(current_step_number) is not int or type(current_step_total) is not int
                    or not 0 <= current_step_number <= current_step_total or current_step_total <= 0):
                raise ValueError('작업자 진행 수치는 0 ≤ 완료 수 ≤ 전체 수인 정수여야 합니다.')
            write_record_atomically(self.current_progress_path, {
                'started_at': self.current_started_timestamp,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'stage': current_stage_name, 'step': current_step_number,
                'step_total': current_step_total,
                'scope': current_progress_scope,
            })
