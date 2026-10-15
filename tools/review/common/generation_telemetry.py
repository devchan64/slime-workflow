"""별도 GPU 작업자의 5초 heartbeat·단계 ETA·장치별 관측 기록."""
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from pathlib import Path
import subprocess
import threading
import time
from tools.review.common.generation_estimates import calculate_generation_estimate
from tools.review.common.generation_records import write_record_atomically

GENERATION_SAMPLE_INTERVAL = 5


class GenerationTelemetryRecorder:
    def __init__(self, current_attempt_root, current_step_total, historical_duration_values):
        self.current_attempt_root = current_attempt_root
        self.current_step_total = current_step_total
        self.historical_duration_values = historical_duration_values
        self.current_stop_event = threading.Event()
        self.current_state_lock = threading.RLock()
        self.current_start_clock = time.monotonic()
        self.current_step_clock = None
        self.current_step_samples = []
        self.current_run_state = {'status':'running','stage':'prepare','step':0,'started_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'gpu_observations':{},'measurement_gaps':[]}
        self.current_worker_thread = threading.Thread(target=self.run_telemetry_heartbeat,daemon=True)

    def start_generation_telemetry(self):
        self.current_worker_thread.start()

    def update_generation_stage(self, current_stage_name):
        with self.current_state_lock:
            self.current_run_state['stage'] = current_stage_name
            if current_stage_name=='inference':
                self.current_step_clock = time.monotonic()
        self.capture_generation_memory()
        self.save_generation_metrics()

    def record_generation_step(self, current_step_number):
        with self.current_state_lock:
            current_clock_value = time.monotonic()
            self.current_step_samples.append(current_clock_value-self.current_step_clock)
            self.current_step_clock = current_clock_value
            self.current_run_state['step'] = current_step_number
        self.save_generation_metrics()

    def sample_generation_memory(self):
        current_process_ids = {os.getpid()}
        current_parent_records = {}
        for current_stat_path in Path('/proc').glob('[0-9]*/stat'):
            try:
                current_parent_records[int(current_stat_path.parent.name)] = int(current_stat_path.read_text().rsplit(')',1)[1].split()[1])
            except (OSError,ValueError,IndexError):
                continue
        while True:
            current_child_ids = {current_pid_value for current_pid_value,current_parent_value in current_parent_records.items() if current_parent_value in current_process_ids}
            if current_child_ids <= current_process_ids:
                break
            current_process_ids.update(current_child_ids)
        current_device_text = subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.used','--format=csv,noheader,nounits'],text=True,timeout=2)
        current_process_text = subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits'],text=True,timeout=2)
        current_usage_records = {}
        for current_process_line in current_process_text.splitlines():
            current_uuid_value,current_pid_text,current_usage_text = map(str.strip,current_process_line.split(','))
            if int(current_pid_text) in current_process_ids:
                current_usage_records[current_uuid_value] = current_usage_records.get(current_uuid_value,0)+int(current_usage_text)
        with self.current_state_lock:
            for current_device_line in current_device_text.splitlines():
                current_uuid_value,current_usage_text = map(str.strip,current_device_line.split(','))
                current_device_record = self.current_run_state['gpu_observations'].setdefault(current_uuid_value,{'process_peak_mib':None,'device_peak_mib':None,'sample_count':0,'method':'nvidia-smi','unit':'MiB','interval_seconds':5,'scope':'작업자 및 자식 프로세스; 장치 전체 값은 다른 작업 포함; 샘플 사이 순간 피크 누락 가능'})
                current_process_usage = current_usage_records.get(current_uuid_value)
                current_device_record.update(process_current_mib=current_process_usage,device_current_mib=int(current_usage_text),updated_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat())
                current_device_record['device_peak_mib'] = max(current_device_record['device_peak_mib'] or 0,int(current_usage_text))
                if current_process_usage is not None:
                    current_device_record['process_peak_mib'] = max(current_device_record['process_peak_mib'] or 0,current_process_usage)
                current_device_record['measurement_reason'] = None if current_process_usage is not None else 'GPU 프로세스 표본 없음; 0으로 간주하지 않음'
                current_device_record['sample_count'] += 1

    def save_generation_metrics(self):
        with self.current_state_lock:
            current_elapsed_seconds = time.monotonic()-self.current_start_clock
            self.current_run_state['elapsed_seconds'] = current_elapsed_seconds
            self.current_run_state['estimate'] = calculate_generation_estimate(self.current_run_state,self.historical_duration_values,'같은 설정의 성공 실행 총시간; 표본 없으면 계산 중','GPU 대기 제외; 모델 준비·인코딩·추론·디코딩·저장 전체')
            current_step_samples = self.current_step_samples[1:][-5:]
            current_estimated_totals = [current_elapsed_seconds+(self.current_step_total-self.current_run_state['step'])*current_step_duration for current_step_duration in current_step_samples] if self.current_run_state['stage']=='inference' and self.current_run_state['step'] < self.current_step_total else []
            self.current_run_state['inference_estimate'] = calculate_generation_estimate(self.current_run_state,current_estimated_totals,'최근 최대 5개 추론 스텝; 첫 스텝 제외','시작부터 추론 종료까지만; 디코딩·저장 제외')
            self.current_run_state['updated_at'] = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
            write_record_atomically(self.current_attempt_root/'metrics.json',self.current_run_state)
            print(f"{self.current_run_state['updated_at']}/generation/{self.current_run_state['stage']} step={self.current_run_state['step']}/{self.current_step_total} elapsed={current_elapsed_seconds:.1f}s",flush=True)

    def capture_generation_memory(self):
        try:
            self.sample_generation_memory()
        except (OSError,ValueError,subprocess.SubprocessError) as current_measurement_error:
            with self.current_state_lock:
                self.current_run_state['measurement_gaps'].append({'at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'error':str(current_measurement_error)})

    def run_telemetry_heartbeat(self):
        while not self.current_stop_event.is_set():
            current_heartbeat_clock = time.monotonic()
            self.capture_generation_memory()
            self.save_generation_metrics()
            self.current_stop_event.wait(max(0,GENERATION_SAMPLE_INTERVAL-(time.monotonic()-current_heartbeat_clock)))

    def finish_generation_telemetry(self, current_status_name):
        self.current_stop_event.set()
        # 시작 단계에서 실패해도 확보한 관측 기록을 종료 상태로 저장한다.
        if self.current_worker_thread.ident is not None:
            self.current_worker_thread.join(timeout=6)
        self.capture_generation_memory()
        self.current_run_state.update(status=current_status_name,stage=current_status_name)
        self.save_generation_metrics()
