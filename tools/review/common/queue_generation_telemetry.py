"""공용 GPU 실행기의 시도별 전체 작업 관측 기록."""
import hashlib
from datetime import datetime
import json
from pathlib import Path
import re
import time
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


class QueueGenerationTelemetry(GenerationTelemetryRecorder):
    def __init__(self,current_job_root,current_command_identity):
        self.current_job_root=Path(current_job_root)
        current_request_path=self.current_job_root/'request.json'
        current_attribute_path=self.current_job_root/'attributes.json'
        current_input_bytes=current_request_path.read_bytes() if current_request_path.is_file() else current_attribute_path.read_bytes() if current_attribute_path.is_file() else b''
        current_command_path=self.current_job_root/'gpu-command.json'
        current_command_arguments=json.loads(current_command_path.read_text())['command'] if current_command_path.is_file() else []
        current_normalized_arguments=[str(current_argument_value).replace(str(self.current_job_root),'{job_root}') for current_argument_value in current_command_arguments]
        current_execution_identity=json.dumps([current_command_identity,current_normalized_arguments],ensure_ascii=False).encode()
        current_input_signature=hashlib.sha256(current_input_bytes+current_execution_identity).hexdigest()
        current_attempt_identifier=str(time.time_ns())
        current_attempt_root=self.current_job_root/'queue-telemetry'/current_attempt_identifier
        current_attempt_root.mkdir(parents=True)
        current_history_durations=[]
        if current_input_bytes:
            for current_metrics_path in sorted(self.current_job_root.parent.glob('*/queue-telemetry/*/metrics.json'),key=lambda current_record_path:current_record_path.parent.name):
                current_metrics_record=json.loads(current_metrics_path.read_text())
                if current_metrics_record.get('input_signature')==current_input_signature and current_metrics_record.get('status')=='completed':
                    current_history_durations.append(current_metrics_record['elapsed_seconds'])
        super().__init__(current_attempt_root,0,current_history_durations[-20:])
        self.current_run_state.update(job_id=self.current_job_root.name,attempt_id=current_attempt_identifier,input_signature=current_input_signature,stage='worker')
        write_record_atomically(self.current_job_root/'queue-telemetry.json',{'attempt_id':current_attempt_identifier})

    def save_generation_metrics(self):
        with self.current_state_lock:
            if self.current_run_state['status']=='running':
                current_status_path=self.current_job_root/'status.json'
                if current_status_path.is_file():
                    current_worker_status=json.loads(current_status_path.read_text())
                    self.current_run_state['stage']=current_worker_status.get('stage') or 'worker'
                current_worker_metrics = read_current_worker_metrics(self.current_job_root)
                if current_worker_metrics and matches_current_queue_attempt(self.current_run_state, current_worker_metrics):
                    self.current_run_state['stage'] = current_worker_metrics['stage']
                    self.current_run_state['worker_progress'] = {
                        'stage': current_worker_metrics['stage'],
                        'step': current_worker_metrics['step'],
                        'total': current_worker_metrics['step_total'],
                        'updated_at': current_worker_metrics['updated_at'],
                        'scope': '작업자 추론 단계; 전체 작업 진행률과 구분',
                    }
            super().save_generation_metrics()


def read_current_worker_metrics(current_job_root):
    """작업자 시도 포인터가 제공되는 생성기의 현재 관측을 읽는다."""
    current_pointer_path = Path(current_job_root)/'current-attempt.json'
    if not current_pointer_path.is_file():
        return None
    current_attempt_identifier = json.loads(current_pointer_path.read_text())['id']
    if not isinstance(current_attempt_identifier, str) or not re.fullmatch(r'[a-f0-9]{32}', current_attempt_identifier):
        raise ValueError('작업자 관측 실행 시도 ID 형식 오류')
    current_metrics_path = Path(current_job_root)/'attempts'/current_attempt_identifier/'metrics.json'
    return json.loads(current_metrics_path.read_text()) if current_metrics_path.is_file() else None


def read_queue_generation_metrics(current_job_root):
    current_pointer_path=current_job_root/'queue-telemetry.json'
    if not current_pointer_path.is_file():return None
    current_pointer_record=json.loads(current_pointer_path.read_text())
    current_attempt_identifier=current_pointer_record['attempt_id']
    if not isinstance(current_attempt_identifier,str) or not current_attempt_identifier.isdecimal():
        raise ValueError('GPU 관측 실행 시도 ID 형식 오류')
    current_metrics_path=current_job_root/'queue-telemetry'/current_attempt_identifier/'metrics.json'
    return json.loads(current_metrics_path.read_text()) if current_metrics_path.is_file() else None


def matches_current_queue_attempt(current_queue_metrics, current_worker_metrics):
    """이전 작업자 기록을 새 실행기의 현재 상태로 합치지 않는다."""
    if not current_queue_metrics:
        return True
    current_queue_started = current_queue_metrics.get('started_at')
    current_worker_started = current_worker_metrics.get('started_at')
    if not current_queue_started or not current_worker_started:
        return False
    return datetime.fromisoformat(current_worker_started) >= datetime.fromisoformat(current_queue_started)


def merge_generation_worker_metrics(current_status_record, current_worker_metrics):
    """전체 작업 관측을 유지하고 작업자 관측은 별도 범위로 보존한다."""
    if not matches_current_queue_attempt(current_status_record.get('metrics'), current_worker_metrics):
        return False
    current_status_record['worker_metrics'] = current_worker_metrics
    current_status_record.setdefault('metrics', current_worker_metrics)
    current_status_record.setdefault('estimate', current_worker_metrics['estimate'])
    return True
