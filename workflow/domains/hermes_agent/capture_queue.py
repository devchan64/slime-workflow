"""검수 캡처 대기열 접수 기반. 운영 API에는 아직 등록하지 않는다."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import uuid

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.capture_delegation import prepare_capture_delegation_once

CAPTURE_QUEUE_SERVICE_NAME = 'review-capture'
CAPTURE_QUEUE_EXECUTION_VERIFIED = False  # 실제 GPU 사용량과 프로세스 정리가 검증되기 전에는 실행을 허용하지 않는다.


def submit_capture_queue_request(current_delegation_store, current_storage_root, current_request_identifier, current_service_name, current_request_payload, *, current_workflow_root=None):
    """검증된 자원 정책이 없으면 접수 기록이나 실행기를 만들지 않는다."""
    from workflow.common.gpu_job_queue import GPU_MEMORY_REQUIREMENTS, GPU_EXCLUSIVE_SERVICES, WORKFLOW_ROOT_DIRECTORY, launch_gpu_process
    if CAPTURE_QUEUE_EXECUTION_VERIFIED is not True:
        raise ValueError('검수 캡처의 GPU 실행과 종료 정리가 아직 검증되지 않았습니다.')
    current_memory_limit = GPU_MEMORY_REQUIREMENTS.get(CAPTURE_QUEUE_SERVICE_NAME)
    if type(current_memory_limit) is not int or current_memory_limit <= 0 or CAPTURE_QUEUE_SERVICE_NAME not in GPU_EXCLUSIVE_SERVICES:
        raise ValueError('검수 캡처의 GPU 자원 정책이 준비되지 않았습니다.')
    current_storage_root = Path(current_storage_root)
    current_expected_root = Path(current_workflow_root or WORKFLOW_ROOT_DIRECTORY) / '.tmp' / 'test' / 'review-capture'
    if current_storage_root != current_expected_root or not current_storage_root.is_absolute() or current_storage_root.is_symlink() or not current_storage_root.is_dir() or current_storage_root.resolve() != current_storage_root:
        raise ValueError('검수 캡처 작업 루트 오류')
    def submit_normalized_capture_job(current_capture_settings):
        current_job_identifier = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S-') + uuid.uuid4().hex[:8]
        current_job_directory = current_storage_root / current_job_identifier
        current_job_directory.mkdir(mode=0o700, exist_ok=False)
        write_record_atomically(current_job_directory/'request.json', {'request_id':current_request_identifier, 'service':current_service_name, 'settings':current_capture_settings})
        current_worker_command = [sys.executable, '-m', 'workflow.domains.hermes_agent.capture_worker', '--job-dir', str(current_job_directory)]
        with (current_job_directory/'worker.log').open('x', encoding='utf-8') as current_worker_log:
            launch_gpu_process(current_worker_command, current_job_directory, CAPTURE_QUEUE_SERVICE_NAME, stdout=current_worker_log, stderr=subprocess.STDOUT, start_new_session=True)
        return {'id':current_job_identifier}
    return prepare_capture_delegation_once(current_delegation_store, current_request_identifier, current_service_name, current_request_payload, submit_normalized_capture_job)
