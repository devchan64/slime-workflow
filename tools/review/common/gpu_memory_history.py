"""GPU 작업별 실측 최고 메모리 기록과 보수적 예약량 추정."""
import json
import fcntl
import os
from pathlib import Path
import subprocess
import time
from tools.review.common.generation_records import write_record_atomically

MODEL_OFFLOAD_WORKER_NAMES = {'run_qwen_2512.py', 'run_qwen_21_reference.py'}
IMAGE_MEMORY_WORKER_NAMES = {'run_qwen_2512.py', 'run_qwen_2511_three_reference.py', 'run_qwen_21_reference.py'}
WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
IMAGE_HISTORY_ROOT_PATHS = tuple(WORKFLOW_ROOT_DIRECTORY/current_relative_path for current_relative_path in ('.tmp/test/billboard-generator', '.tmp/test/prop-generator', '.tmp/test/vegetation-generator', '.tmp/test/building-generator', '.tmp/test/qwen-image-2512', '.tmp/test/qwen-image-2512/tile-map', '.tmp/test/qwen-image-2512/floor-tile', '.tmp/test/qwen-image-2511-three-reference', '.tmp/test/qwen-image-21', '.tmp/test/seamless-tile-generator'))

MEMORY_HISTORY_DIRECTORY = Path(__file__).resolve().parents[3]/'.tmp/gpu-memory-history'


def read_worker_memory(worker_pid, current_memory_domain='combined'):
    if current_memory_domain not in ('combined', 'gtt', 'vram'):
        raise ValueError('알 수 없는 GPU 메모리 영역입니다.')
    parent_process_map = {}
    for process_path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = process_path.read_text().rsplit(') ', 1)[1].split()
            parent_process_map[int(process_path.parent.name)] = int(fields[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    worker_process_ids = {worker_pid}
    while True:
        descendants = {pid for pid, parent in parent_process_map.items() if parent in worker_process_ids}
        if descendants <= worker_process_ids:
            break
        worker_process_ids.update(descendants)
    query_result = subprocess.run(['amd-smi', 'process', '--json'], capture_output=True, text=True, check=True, timeout=10)
    total_memory_mib = 0
    for current_device_record in json.loads(query_result.stdout):
        for current_process_record in current_device_record.get('process_list', []):
            current_process_values = current_process_record['process_info']
            if current_process_values == 'No running processes detected':
                continue
            if current_process_values['pid'] in worker_process_ids:
                try:
                    current_memory_records = current_process_values['memory_usage']
                    current_domain_names = ('vram','gtt') if current_memory_domain == 'combined' else (current_memory_domain,)
                    current_gpu_memory = [current_memory_records[f'{current_domain_name}_mem'] for current_domain_name in current_domain_names]
                    if any(current_memory_record['unit'] != 'B' or not isinstance(current_memory_record['value'], int) or current_memory_record['value'] < 0 for current_memory_record in current_gpu_memory):
                        raise ValueError('AMD 프로세스 GPU 메모리 값 오류')
                    total_memory_mib += (sum(current_memory_record['value'] for current_memory_record in current_gpu_memory) + 1048575) // 1048576
                except (KeyError, TypeError) as current_measurement_error:
                    raise ValueError('AMD 프로세스 GPU 메모리 정보를 읽을 수 없습니다.') from current_measurement_error
    return total_memory_mib


def load_recent_observations(service, command_identity_name=None):
    records = []
    for record_path in MEMORY_HISTORY_DIRECTORY.glob('[0-9]*.json'):
        try:
            record = json.loads(record_path.read_text())
        except FileNotFoundError:
            continue
        if record['service']==service and resolve_observation_identity(record)==command_identity_name:
            records.append((record_path, record))
    return sorted(records, key=lambda item:item[1]['observed_at_ns'], reverse=True)


def summarize_memory_observations(service, records):
    usable = [r for r in records if r['status']=='completed' and r['samples']>0 and r['peak_memory_mib']>0 and not r.get('measurement_error')]
    return {'service':service, 'updated_at_ns':time.time_ns(), 'retained_runs':len(records),
            'usable_runs':len(usable), 'peak_memory_mib':max((r['peak_memory_mib'] for r in usable), default=0),
            'average_peak_memory_mib':round(sum(r['peak_memory_mib'] for r in usable)/len(usable),1) if usable else None,
            'runs':records}


def save_memory_observation(service, job_path, peak_memory_mib, samples, status, error=None, command_identity_name=None):
    MEMORY_HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    observation_record = {'command_identity':command_identity_name, 'service':service, 'job_id':Path(job_path).name, 'observed_at_ns':time.time_ns(),
                          'peak_memory_mib':peak_memory_mib, 'samples':samples, 'status':status, 'measurement_error':error}
    with (MEMORY_HISTORY_DIRECTORY/'update.lock').open('a') as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
        record_path = MEMORY_HISTORY_DIRECTORY/f'{observation_record["observed_at_ns"]}-{os.getpid()}.json'
        write_record_atomically(record_path, observation_record)
        recent_records = load_recent_observations(service, command_identity_name)
        for expired_path, _ in recent_records[20:]:
            expired_path.unlink(missing_ok=True)
        summary_path = MEMORY_HISTORY_DIRECTORY/'summary.json'
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        summary[service if command_identity_name is None else f'{service}:{command_identity_name}'] = summarize_memory_observations(service, [record for _,record in recent_records[:20]])
        write_record_atomically(summary_path, summary)
    return observation_record


def estimate_required_memory(service, configured_floor_mib, command_identity_name=None):
    if service == 'image' and isinstance(command_identity_name, str) and command_identity_name.endswith(':offload=model-v1'):
        configured_floor_mib = max(configured_floor_mib, 32768)
    observations = [record for _,record in load_recent_observations(service, command_identity_name)[:20]]
    summary = summarize_memory_observations(service, observations)
    measured_peak_mib = summary['peak_memory_mib']
    # 안전 여유는 대기열이 GPU 전체에서 한 번만 차감한다.
    # 완료된 실측값이 없을 때만 초기 기준을 사용한다.
    required_memory_mib = measured_peak_mib if measured_peak_mib else configured_floor_mib
    return {'required_memory_mib':required_memory_mib, 'samples':summary['usable_runs'],
            'retained_runs':summary['retained_runs'], 'observed_peak_mib':measured_peak_mib, 'configured_floor_mib':configured_floor_mib,
            'command_identity':command_identity_name,
            'method':'recent-20-max-successful-peak' if measured_peak_mib else 'configured-initial-estimate'}


def identify_execution_command(command_argument_values, generation_job_directory=None, current_memory_domain=None):
    """이미지는 실행기·해상도·스텝·참조 개수까지 메모리 프로필로 구분한다."""
    if generation_job_directory is not None and len(command_argument_values)>1 and Path(command_argument_values[1]).parts[-2:] == ('wan_fun','worker.py'):
        current_request_record = json.loads((Path(generation_job_directory)/'request.json').read_text())
        current_profile_values = [current_request_record.get(current_field_name) for current_field_name in ('width','height','frames')]
        if any(type(current_profile_value) is not int or current_profile_value <= 0 for current_profile_value in current_profile_values):
            raise ValueError('Wan GPU 메모리 예측에 필요한 해상도·프레임 설정이 없습니다.')
        current_profile_name = f'wan-fun:worker.py:{current_profile_values[0]}x{current_profile_values[1]}:frames={current_profile_values[2]}'
        return current_profile_name + (f':domain={current_memory_domain}' if current_memory_domain else '')
    if generation_job_directory is not None and len(command_argument_values)>1 and Path(command_argument_values[1]).name in IMAGE_MEMORY_WORKER_NAMES:
        current_worker_name = Path(command_argument_values[1]).name
        current_profile_name = build_image_memory_identity(current_worker_name, Path(generation_job_directory))
        return current_profile_name + ':offload=model-v1' if current_worker_name in MODEL_OFFLOAD_WORKER_NAMES else current_profile_name
    if len(command_argument_values)>2 and command_argument_values[1]=='-m':
        return command_argument_values[2]
    if len(command_argument_values)>1 and command_argument_values[1].endswith('.py'):
        return Path(command_argument_values[1]).name
    return Path(command_argument_values[0]).name


def build_image_memory_identity(command_identity_name, generation_job_directory):
    saved_request_record = json.loads((generation_job_directory/'request.json').read_text())
    if saved_request_record.get('action') == 'prepare': return command_identity_name+':prepare'
    for request_field_name in ('width','height','steps'):
        if type(saved_request_record.get(request_field_name)) is not int or saved_request_record[request_field_name] <= 0:
            raise ValueError(f'GPU 메모리 예측에 필요한 {request_field_name} 설정이 없습니다: {generation_job_directory}')
    reference_image_count = len(saved_request_record.get('references',saved_request_record.get('images',[])))
    if 'seamless_tile' in saved_request_record:
        command_identity_name += f":seamless-v{saved_request_record['seamless_tile']['schema_version']}"
    if 'floor_separation' in saved_request_record:
        command_identity_name += f":floor-three-stage-v{saved_request_record['floor_separation']['version']}" if saved_request_record['floor_separation']['version'] in (2,3,4,5,6,7,8,9,10) else ':floor-two-stage-v1'
    return f"{command_identity_name}:{saved_request_record['width']}x{saved_request_record['height']}:steps={saved_request_record['steps']}:references={reference_image_count}"


def resolve_observation_identity(observation_record_value):
    """구형 측정값은 남아 있는 원본 요청으로 분류한다. 출처가 없으면 섞지 않는다."""
    command_identity_name = observation_record_value.get('command_identity')
    if command_identity_name not in IMAGE_MEMORY_WORKER_NAMES: return command_identity_name
    generation_job_identifier = observation_record_value.get('job_id','')
    if not generation_job_identifier or Path(generation_job_identifier).name != generation_job_identifier: return command_identity_name
    matching_request_paths = [current_root_path/generation_job_identifier for current_root_path in IMAGE_HISTORY_ROOT_PATHS if (current_root_path/generation_job_identifier/'request.json').is_file()]
    if len(matching_request_paths) != 1: return command_identity_name
    return build_image_memory_identity(command_identity_name,matching_request_paths[0])
