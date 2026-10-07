"""별도 프로세스에서 GPU 메모리와 공용 실행 잠금을 기다리는 영속 작업 대기열."""
import argparse
import hashlib
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
# HY-Motion의 초기 예약은 실측 전 보수적 값이며 완료 후 공용 이력의 peak로 갱신한다.
GPU_MEMORY_REQUIREMENTS['hy-motion'] = 7000
GPU_POLL_INTERVAL = 2
# 실측 프로세스 최대 사용량과 현재 여유를 직접 비교한다.
# 고정 여유분 추가 차감은 단독 실행이 가능한 작업도 무기한 차단한다.


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
        if generation_status_record['status'] not in ('failed', 'cancelled', 'paused'):
            raise ValueError('일시정지·취소·실패 작업만 재개할 수 있습니다.')
        generation_command_record = json.loads((generation_job_path/'gpu-command.json').read_text())
        (generation_job_path/'cancel.request').unlink(missing_ok=True)
        (generation_job_path/'pause.request').unlink(missing_ok=True)
        (generation_job_path/'stage-pause.json').unlink(missing_ok=True)
        write_record_atomically(generation_job_path/'status.json', {'status':'queued', 'message':'GPU 실행 대기'})
        with (generation_job_path/'worker.log').open('a') as generation_log_handle:
            launch_gpu_process(generation_command_record['command'], generation_job_path, generation_command_record['service'], stdout=generation_log_handle, stderr=subprocess.STDOUT, start_new_session=True)
    return {'id':generation_job_path.name, 'status':'queued'}


def cancel_gpu_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    with (generation_job_path/'resume.lock').open('a') as resume_lock_handle:
        fcntl.flock(resume_lock_handle, fcntl.LOCK_EX)
        generation_status_record = json.loads((generation_job_path/'status.json').read_text())
        if generation_status_record['status'] not in ('running', 'queued', 'paused'):
            raise ValueError('대기·실행·검수 대기 작업만 중지할 수 있습니다.')
        (generation_job_path/'cancel.request').touch()
        if generation_status_record['status'] == 'paused':
            generation_status_record = {'status':'cancelled','message':'사용자가 중지했습니다. 완료한 단계 결과는 유지됩니다.'}
            write_record_atomically(generation_job_path/'status.json', generation_status_record)
    return {'status':generation_status_record['status'], 'cancel_requested':True}


def select_runnable_ticket(available_memory_mib):
    """잠금 안에서 접수 순서대로 확인해 메모리가 맞는 첫 작업을 선택한다."""
    for waiting_ticket_path in sorted(GPU_QUEUE_DIRECTORY.glob('*.json')):
        try:
            waiting_ticket_record = json.loads(waiting_ticket_path.read_text())
            os.kill(waiting_ticket_record['pid'], 0)
            waiting_job_directory = Path(waiting_ticket_record['path'])
            if (waiting_job_directory/'cancel.request').exists():
                continue
            waiting_command_record = json.loads((waiting_job_directory/'gpu-command.json').read_text())
        except (FileNotFoundError, ProcessLookupError):
            continue
        waiting_memory_estimate = estimate_required_memory(
            waiting_command_record['service'], GPU_MEMORY_REQUIREMENTS[waiting_command_record['service']],
            identify_execution_command(waiting_command_record['command'], waiting_job_directory))
        if waiting_memory_estimate['required_memory_mib'] <= available_memory_mib:
            return waiting_ticket_path
    return None


def calculate_queue_revision():
    """실행기와 메모리 추정 코드의 변경을 감지한다."""
    source_file_paths = [Path(__file__), Path(__file__).with_name('gpu_memory_history.py')]
    return hashlib.sha256(b''.join(source_file_path.read_bytes() for source_file_path in source_file_paths)).hexdigest()


def reload_waiting_executor(queue_ticket_path, initial_source_revision):
    """대기 중에만 동일 PID로 교체하여 부모 감시와 접수 순서를 유지한다."""
    if calculate_queue_revision() == initial_source_revision:
        return
    replacement_environment_values = dict(os.environ, SLIME_GPU_QUEUE_TICKET=str(queue_ticket_path.resolve()))
    os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], replacement_environment_values)


def execute_queued_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    generation_command_record = json.loads((generation_job_path/'gpu-command.json').read_text())
    GPU_QUEUE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    initial_source_revision = calculate_queue_revision()
    inherited_ticket_value = os.environ.pop('SLIME_GPU_QUEUE_TICKET', None)
    queue_ticket_path = Path(inherited_ticket_value) if inherited_ticket_value else GPU_QUEUE_DIRECTORY/f'{time.time_ns():020d}-{os.getpid()}.json'
    if inherited_ticket_value:
        inherited_ticket_record = json.loads(queue_ticket_path.read_text())
        if queue_ticket_path.resolve().parent != GPU_QUEUE_DIRECTORY.resolve() or inherited_ticket_record != {'pid':os.getpid(), 'path':str(generation_job_path)}:
            raise ValueError('대기열 갱신 티켓이 현재 작업과 일치하지 않습니다.')
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
                if (generation_job_path/'pause.request').exists():
                    write_record_atomically(generation_job_path/'status.json', {'status':'paused','message':'대기 중 일시정지'})
                    return 0
                reload_waiting_executor(queue_ticket_path, initial_source_revision)
                # 죽은 대기 프로세스의 표만 제거한다. 생성 기록은 보존한다.
                for previous_ticket_path in GPU_QUEUE_DIRECTORY.glob('*.json'):
                    try: os.kill(json.loads(previous_ticket_path.read_text())['pid'], 0)
                    except ProcessLookupError: previous_ticket_path.unlink(missing_ok=True)
                    except FileNotFoundError: pass
                queued_ticket_values = sorted(GPU_QUEUE_DIRECTORY.glob('*.json'))
                queue_position_value = queued_ticket_values.index(queue_ticket_path)+1
                memory_total_value, memory_free_value = read_gpu_memory()
                memory_estimate_record = estimate_required_memory(generation_command_record['service'], GPU_MEMORY_REQUIREMENTS[generation_command_record['service']], identify_execution_command(generation_command_record['command'], generation_job_path))
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
                            # 구형 실행기의 고정 예약도 완료된 동일 명령 측정값으로 갱신한다.
                            reservation_job_directory = Path(reservation_record['path']) if 'path' in reservation_record else None
                            if reservation_job_directory and (reservation_job_directory/'gpu-command.json').exists():
                                reservation_command_record = json.loads((reservation_job_directory/'gpu-command.json').read_text())
                                reservation_memory_estimate = estimate_required_memory(reservation_command_record['service'], GPU_MEMORY_REQUIREMENTS[reservation_command_record['service']], identify_execution_command(reservation_command_record['command'], reservation_job_directory))
                                if reservation_memory_estimate['samples']:
                                    reservation_record['required_memory_mib'] = reservation_memory_estimate['required_memory_mib']
                                    write_record_atomically(reservation_path, reservation_record)
                            # 실측 여유에는 이미 사용 중인 메모리가 반영되어 있다.
                            try:
                                measured_reservation_mib = read_worker_memory(reservation_record['pid'])
                            except (OSError, ValueError, subprocess.SubprocessError):
                                measured_reservation_mib = 0
                            reserved_memory_value += max(0, reservation_record['required_memory_mib']-measured_reservation_mib)
                        # 아직 사용하지 않은 예약분만 차감해 모델 로딩 여유를 확보한다.
                        memory_total_value, memory_free_value = read_gpu_memory()
                        available_memory_value = max(0, memory_free_value-reserved_memory_value)
                        if select_runnable_ticket(available_memory_value) == queue_ticket_path:
                            write_record_atomically(active_reservation_path, {'pid':os.getpid(), 'path':str(generation_job_path), 'required_memory_mib':required_memory_value})
                            queue_ticket_path.unlink(missing_ok=True)
                            break
                    finally:
                        fcntl.flock(gpu_execution_handle, fcntl.LOCK_UN)
                queue_status_record = {'status':'queued', 'queue_position':queue_position_value, 'free_memory_mib':memory_free_value, 'required_memory_mib':required_memory_value, 'reserved_memory_mib':reserved_memory_value, 'available_memory_mib':available_memory_value, 'memory_estimate':memory_estimate_record, 'message':'GPU 메모리 여유 또는 실행 가능한 앞선 작업 대기'}
                write_record_atomically(generation_job_path/'status.json', queue_status_record)
                print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/gpu-queue/wait {queue_status_record}', flush=True)
                time.sleep(GPU_POLL_INTERVAL)
            queue_ticket_path.unlink(missing_ok=True)
            write_record_atomically(generation_job_path/'status.json', {'status':'running', 'memory_estimate':memory_estimate_record})
            generation_worker_process = subprocess.Popen(generation_command_record['command'], start_new_session=True, env=dict(os.environ, SLIME_GPU_RESERVATION_PATH=str(active_reservation_path.resolve())))
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
            elif generation_exit_value == 0 and (generation_job_path/'stage-pause.json').exists():
                generation_status_record = {'status':'paused','message':'단계 결과를 확인한 뒤 다음 단계로 진행하세요.'}
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
            observation_record = save_memory_observation(generation_command_record['service'], generation_job_path, peak_memory_mib, memory_sample_count, final_status, memory_measurement_error, identify_execution_command(generation_command_record['command'], generation_job_path))
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
