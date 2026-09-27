"""별도 프로세스에서 GPU 메모리와 공용 실행 잠금을 기다리는 영속 작업 대기열."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_memory_history import read_worker_memory, save_memory_observation, estimate_required_memory, identify_execution_command
GPU_QUEUE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/gpu-queue'
GPU_MEMORY_REQUIREMENTS = {'momask': 4096, 'character-animation': 6144, 'image': 6144, 'anny': 2048}
GPU_POLL_INTERVAL = 2
GPU_MEMORY_MARGIN_MIB = 512


def read_gpu_memory():
    memory_query_result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.free', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True, timeout=5)
    memory_total_value, memory_free_value = map(int, memory_query_result.stdout.splitlines()[0].split(','))
    return memory_total_value, memory_free_value


def launch_gpu_process(command_argument_values, generation_job_path, generation_service_name, **process_option_values):
    generation_job_path = Path(generation_job_path).resolve()
    generation_request_record = {'command': command_argument_values, 'service': generation_service_name}
    write_record_atomically(generation_job_path/'gpu-command.json', generation_request_record)
    write_record_atomically(generation_job_path/'status.json', {'status':'queued', 'message':'GPU 실행 대기'})
    try:
        return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--job-dir', str(generation_job_path)], **process_option_values)
    except Exception as process_launch_error:
        write_record_atomically(generation_job_path/'status.json', {'status':'failed', 'error':str(process_launch_error)})
        raise


def resume_gpu_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    with (generation_job_path/'resume.lock').open('a') as resume_lock_handle:
        fcntl.flock(resume_lock_handle, fcntl.LOCK_EX)
        generation_status_record = json.loads((generation_job_path/'status.json').read_text())
        if generation_status_record['status'] not in ('failed', 'cancelled'):
            raise ValueError('취소·실패 작업만 재개할 수 있습니다.')
        generation_command_record = json.loads((generation_job_path/'gpu-command.json').read_text())
        (generation_job_path/'cancel.request').unlink(missing_ok=True)
        write_record_atomically(generation_job_path/'status.json', {'status':'queued', 'message':'GPU 실행 대기'})
        with (generation_job_path/'worker.log').open('a') as generation_log_handle:
            launch_gpu_process(generation_command_record['command'], generation_job_path, generation_command_record['service'], stdout=generation_log_handle, stderr=subprocess.STDOUT, start_new_session=True)
    return {'id':generation_job_path.name, 'status':'queued'}


def cancel_gpu_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    generation_status_record = json.loads((generation_job_path/'status.json').read_text())
    if generation_status_record['status'] not in ('running', 'queued'):
        raise ValueError('대기·실행 중인 작업만 중지할 수 있습니다.')
    (generation_job_path/'cancel.request').touch()
    return {'status':generation_status_record['status'], 'cancel_requested':True}


def execute_queued_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    generation_command_record = json.loads((generation_job_path/'gpu-command.json').read_text())
    GPU_QUEUE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    queue_ticket_path = GPU_QUEUE_DIRECTORY/f'{time.time_ns():020d}-{os.getpid()}.json'
    write_record_atomically(queue_ticket_path, {'pid':os.getpid(), 'path':str(generation_job_path)})
    active_reservation_directory = GPU_QUEUE_DIRECTORY/'active'
    active_reservation_directory.mkdir(exist_ok=True)
    active_reservation_path = active_reservation_directory/queue_ticket_path.name
    peak_memory_mib = 0
    memory_sample_count = 0
    memory_measurement_error = None
    last_memory_sample_time = 0
    generation_worker_process = None
    import signal
    signal.signal(signal.SIGTERM, lambda *_: (generation_job_path/"cancel.request").touch())
    try:
        with (GPU_QUEUE_DIRECTORY/'execution.lock').open('a') as gpu_execution_handle:
            while True:
                if (generation_job_path/'cancel.request').exists():
                    write_record_atomically(generation_job_path/'status.json', {'status':'cancelled'})
                    return 0
                # 죽은 대기 프로세스의 표만 제거한다. 생성 기록은 보존한다.
                for previous_ticket_path in GPU_QUEUE_DIRECTORY.glob('*.json'):
                    try: os.kill(json.loads(previous_ticket_path.read_text())['pid'], 0)
                    except ProcessLookupError: previous_ticket_path.unlink(missing_ok=True)
                    except FileNotFoundError: pass
                queued_ticket_values = sorted(GPU_QUEUE_DIRECTORY.glob('*.json'))
                queue_position_value = queued_ticket_values.index(queue_ticket_path)+1
                memory_total_value, memory_free_value = read_gpu_memory()
                memory_estimate_record = estimate_required_memory(generation_command_record['service'], GPU_MEMORY_REQUIREMENTS[generation_command_record['service']], identify_execution_command(generation_command_record['command']))
                required_memory_value = memory_estimate_record['required_memory_mib']
                if memory_total_value < required_memory_value:
                    raise ValueError(f'GPU 전체 메모리 {memory_total_value} MiB: 요구량 {required_memory_value} MiB보다 작습니다.')
                execution_lock_acquired = False
                available_memory_value = 0
                reserved_memory_value = 0
                try:
                    fcntl.flock(gpu_execution_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    execution_lock_acquired = True
                except BlockingIOError:
                    pass
                if execution_lock_acquired:
                    try:
                        for reservation_path in active_reservation_directory.glob('*.json'):
                            try:
                                reservation_record = json.loads(reservation_path.read_text())
                            except FileNotFoundError:
                                continue
                            try:
                                os.kill(reservation_record['pid'], 0)
                            except ProcessLookupError:
                                reservation_path.unlink(missing_ok=True)
                                continue
                            reserved_memory_value += reservation_record['required_memory_mib']
                        # 실측 여유에서 예약도 차감해 모델 로딩 전 동시 접수의 과다 실행을 막는다.
                        memory_total_value, memory_free_value = read_gpu_memory()
                        available_memory_value = max(0, memory_free_value-reserved_memory_value-GPU_MEMORY_MARGIN_MIB)
                        if queue_position_value == 1 and available_memory_value >= required_memory_value:
                            write_record_atomically(active_reservation_path, {'pid':os.getpid(), 'path':str(generation_job_path), 'required_memory_mib':required_memory_value})
                            queue_ticket_path.unlink(missing_ok=True)
                            break
                    finally:
                        fcntl.flock(gpu_execution_handle, fcntl.LOCK_UN)
                queue_status_record = {'status':'queued', 'queue_position':queue_position_value, 'free_memory_mib':memory_free_value, 'required_memory_mib':required_memory_value, 'reserved_memory_mib':reserved_memory_value, 'available_memory_mib':available_memory_value, 'memory_estimate':memory_estimate_record, 'message':'GPU 메모리 예약 여유 또는 앞선 요청 접수 대기'}
                write_record_atomically(generation_job_path/'status.json', queue_status_record)
                print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/gpu-queue/wait {queue_status_record}', flush=True)
                time.sleep(GPU_POLL_INTERVAL)
            queue_ticket_path.unlink(missing_ok=True)
            write_record_atomically(generation_job_path/'status.json', {'status':'running', 'memory_estimate':memory_estimate_record})
            generation_worker_process = subprocess.Popen(generation_command_record['command'], start_new_session=True)
            while generation_worker_process.poll() is None:
                if (generation_job_path/'cancel.request').exists():
                    import signal
                    os.killpg(generation_worker_process.pid, signal.SIGTERM)
                    try: generation_worker_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(generation_worker_process.pid, signal.SIGKILL)
                        generation_worker_process.wait()
                    break
                if time.monotonic()-last_memory_sample_time >= GPU_POLL_INTERVAL:
                    last_memory_sample_time = time.monotonic()
                    try:
                        peak_memory_mib = max(peak_memory_mib, read_worker_memory(generation_worker_process.pid))
                        memory_sample_count += 1
                    except (OSError, ValueError, subprocess.SubprocessError) as measurement_error:
                        memory_measurement_error = str(measurement_error)
                time.sleep(.25)
            generation_exit_value = generation_worker_process.returncode
            generation_status_record = json.loads((generation_job_path/'status.json').read_text())
            if (generation_job_path/'cancel.request').exists(): generation_status_record = {'status':'cancelled'}
            elif generation_status_record['status'] in ('running','queued'):
                generation_status_record = {'status':'completed' if generation_exit_value == 0 else 'failed', 'exit_code':generation_exit_value}
            write_record_atomically(generation_job_path/'status.json', generation_status_record)
            return generation_exit_value
    except Exception as generation_error_value:
        write_record_atomically(generation_job_path/'status.json', {'status':'failed', 'error':str(generation_error_value)})
        print(f'GPU 대기 실행 실패: {generation_error_value}', flush=True)
        return 1
    finally:
        queue_ticket_path.unlink(missing_ok=True)
        if generation_worker_process is not None and generation_worker_process.poll() is None:
            import signal
            os.killpg(generation_worker_process.pid, signal.SIGKILL)
            generation_worker_process.wait()
        active_reservation_path.unlink(missing_ok=True)
        if generation_worker_process is not None:
            final_status = json.loads((generation_job_path/'status.json').read_text())['status']
            observation_record = save_memory_observation(generation_command_record['service'], generation_job_path, peak_memory_mib, memory_sample_count, final_status, memory_measurement_error, identify_execution_command(generation_command_record['command']))
            write_record_atomically(generation_job_path/'gpu-memory.json', observation_record)

if __name__ == '__main__':
    queue_argument_parser = argparse.ArgumentParser()
    queue_argument_parser.add_argument('--job-dir', required=True)
    sys.exit(execute_queued_generation(queue_argument_parser.parse_args().job_dir))


def list_waiting_gpu_jobs():
    """살아 있는 대기 실행기의 작업 목록만 읽는다."""
    waiting_job_records=[]
    for waiting_ticket_path in sorted(GPU_QUEUE_DIRECTORY.glob('*.json')):
        try:
            waiting_ticket_record=json.loads(waiting_ticket_path.read_text())
            os.kill(waiting_ticket_record['pid'],0)
            waiting_job_directory=Path(waiting_ticket_record['path'])
            if not waiting_job_directory.resolve().is_relative_to(WORKFLOW_ROOT_DIRECTORY/'.tmp'):continue
            waiting_status_record=json.loads((waiting_job_directory/'status.json').read_text())
            if waiting_status_record['status']!='queued':continue
            waiting_command_record=json.loads((waiting_job_directory/'gpu-command.json').read_text())
            waiting_job_records.append({'id':waiting_job_directory.name,'service':waiting_command_record['service']})
        except (FileNotFoundError,ProcessLookupError):continue
    return {'jobs':waiting_job_records}
