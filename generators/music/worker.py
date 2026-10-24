"""음악 모델 준비·생성을 공용 GPU 실행기 아래에서 수행한다."""
import argparse
import os
from pathlib import Path
import signal
import sys
import traceback
import uuid

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from generators.music.contracts import AUDIO_SERVICE_NAMES, read_music_record, resolve_music_paths, resolve_music_profile, verify_music_request, validate_music_identifier
from generators.music.runtime import prepare_music_model, execute_music_inference, calculate_music_checksum
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


def handle_music_signal(current_signal_number,current_stack_frame):
    raise InterruptedError(f'음악 작업 종료 신호 {current_signal_number}')


def collect_music_durations(current_storage_root,current_request_record,current_device_name):
    current_duration_samples = []
    current_runtime_path = WORKFLOW_ROOT_DIRECTORY/('generators/sound_effects/runtime.py' if current_request_record['service']=='sfx-dasheng-audiogen' else 'generators/music/runtime.py')
    if current_request_record['service'] == 'music-magenta':
        current_runtime_path = WORKFLOW_ROOT_DIRECTORY/'generators/music/magenta/runtime.py'
    if current_request_record['service'] == 'music-heartmula':
        current_runtime_path = WORKFLOW_ROOT_DIRECTORY/'generators/music/heartmula/runtime.py'
    current_condition_fields = ('action','model_id','duration_seconds','min_duration_seconds','lyrics','defaults_sha256')
    for current_result_path in current_storage_root.glob('*/attempts/*/result.json'):
        current_previous_request = read_music_record(current_result_path.parent/'request.json')
        current_previous_metrics = read_music_record(current_result_path.parent/'metrics.json')
        current_previous_result = read_music_record(current_result_path)
        if current_previous_result.get('included_download') or current_previous_result.get('runtime_sha256') != calculate_music_checksum(current_runtime_path):
            continue
        if current_previous_metrics['status'] == 'completed' and current_previous_metrics.get('gpu_name') == current_device_name and all(current_previous_request.get(current_field_name)==current_request_record.get(current_field_name) for current_field_name in current_condition_fields):
            current_duration_samples.append(current_previous_metrics['elapsed_seconds'])
    return current_duration_samples[-20:]


def execute_music_worker(current_service_name,current_job_root):
    current_prepare_callback = prepare_music_model
    from generators.music.structured_inputs import execute_structured_inference
    current_inference_callback = execute_structured_inference
    from generators.music.runtime import require_music_cuda
    current_cuda_callback = require_music_cuda
    if current_service_name == 'sfx-dasheng-audiogen':
        from generators.sound_effects.runtime import prepare_effects_model, execute_effects_inference, require_effects_cuda
        current_prepare_callback = prepare_effects_model
        current_inference_callback = execute_effects_inference
        current_cuda_callback = require_effects_cuda
    if current_service_name == 'music-magenta':
        from generators.music.magenta.runtime import prepare_magenta_model, execute_magenta_inference, require_magenta_cuda
        current_prepare_callback = prepare_magenta_model
        current_inference_callback = execute_magenta_inference
        current_cuda_callback = require_magenta_cuda
    if current_service_name == 'music-heartmula':
        from generators.music.heartmula.runtime import prepare_heartmula_model, execute_heartmula_inference
        current_prepare_callback = prepare_heartmula_model
        current_inference_callback = execute_heartmula_inference
    current_storage_root,_,_ = resolve_music_paths(current_service_name)
    if current_job_root.parent.resolve() != current_storage_root.resolve() or current_job_root.is_symlink():
        raise ValueError('음악 작업 경로 오류')
    validate_music_identifier(current_job_root.name)
    current_attempt_root = current_job_root/'attempts'/uuid.uuid4().hex
    current_attempt_root.mkdir(parents=True)
    write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_root.name})
    current_metrics_recorder = GenerationTelemetryRecorder(current_attempt_root,1,[])
    current_metrics_recorder.current_run_state.update(attempt=current_attempt_root.name,generation_id=current_job_root.name,service=current_service_name)
    current_metrics_recorder.start_generation_telemetry()
    current_final_status = 'failed'
    signal.signal(signal.SIGTERM,handle_music_signal)
    signal.signal(signal.SIGINT,handle_music_signal)
    try:
        current_request_record = verify_music_request(current_service_name,read_music_record(current_job_root/'request.json'))
        write_record_atomically(current_attempt_root/'request.json',current_request_record)
        current_torch_module = current_cuda_callback()
        if current_service_name == 'music-magenta':
            current_device_name = current_torch_module
        else:
            current_torch_module.cuda.reset_peak_memory_stats()
            current_device_name = current_torch_module.cuda.get_device_name()
        current_metrics_recorder.current_run_state['gpu_name'] = current_device_name
        # 준비 다운로드 시간은 조건이 일정하지 않으므로 추정 표본으로 쓰지 않는다.
        current_model_ready = (resolve_music_paths(current_service_name)[1]/'prepared.json').exists()
        if current_model_ready and current_request_record['action']=='generate':
            current_metrics_recorder.historical_duration_values = collect_music_durations(current_storage_root,current_request_record,current_device_name)
        current_prepared_record = current_prepare_callback(current_service_name,current_metrics_recorder,current_request_record['action']=='prepare')
        write_record_atomically(current_attempt_root/'model-manifest.json',current_prepared_record)
        if current_request_record['action']=='prepare':
            current_result_record = {'attempt':current_attempt_root.name,'prepared':True,'model_id':current_request_record['model_id']}
        else:
            if current_request_record.get('min_duration_seconds',0):
                from generators.music.minimum_duration import apply_minimax_minimum_duration
                current_control_checksum = calculate_music_checksum(WORKFLOW_ROOT_DIRECTORY/'generators/music/minimum_duration.py')
                write_record_atomically(current_attempt_root/'duration-control.json',{'min_duration_seconds':current_request_record['min_duration_seconds'],'control_sha256':current_control_checksum})
                with apply_minimax_minimum_duration(current_request_record['min_duration_seconds']):
                    current_result_record = current_inference_callback(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder)
                current_result_record['duration_control_sha256'] = current_control_checksum
                current_result_record['min_duration_seconds'] = current_request_record['min_duration_seconds']
            else:
                current_result_record = current_inference_callback(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder)
        current_result_record['included_download'] = not current_model_ready
        write_record_atomically(current_attempt_root/'result.json',current_result_record)
        write_record_atomically(current_job_root/'result.json',current_result_record)
        current_final_status = 'completed'
    except BaseException as current_worker_error:
        current_final_status = 'cancelled' if isinstance(current_worker_error,(InterruptedError,KeyboardInterrupt)) else 'failed'
        _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
        print(f"model_id={resolve_music_profile(current_service_name)['model_id']} model_root={current_model_root} model_path={current_model_root} binary_path={current_python_path}",flush=True)
        write_record_atomically(current_attempt_root/'error.json',{'error':str(current_worker_error),'traceback':traceback.format_exc()})
        traceback.print_exc()
        raise
    finally:
        current_metrics_recorder.finish_generation_telemetry(current_final_status)
        write_record_atomically(current_job_root/'status.json',{'status':current_final_status,'attempt':current_attempt_root.name})


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--service',choices=AUDIO_SERVICE_NAMES,required=True)
    current_argument_parser.add_argument('--job-dir',type=Path,required=True)
    current_argument_values = current_argument_parser.parse_args()
    if current_argument_values.service == 'music-magenta' and os.environ.get('MAGENTA_CUDA_LIBRARIES_READY') != '1':
        current_library_root = Path(sys.prefix)/f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/nvidia'
        current_library_paths = ':'.join(str(current_library_path.resolve()) for current_library_path in sorted(current_library_root.glob('*/lib')))
        current_previous_paths = os.environ.get('LD_LIBRARY_PATH','')
        current_runtime_environment = dict(os.environ,LD_LIBRARY_PATH=current_library_paths+(':'+current_previous_paths if current_previous_paths else ''),MAGENTA_CUDA_LIBRARIES_READY='1')
        os.execve(sys.executable,[sys.executable,*sys.argv],current_runtime_environment)
    execute_music_worker(current_argument_values.service,current_argument_values.job_dir)
