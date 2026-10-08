"""공식 파이프라인 BF16 VNCCS 실행과 별도 프로세스 메모리 감시."""
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from generators.image.vnccs_profile import validate_vnccs_profile, validate_vnccs_assets, VNCCS_QUALITY_WARNING_TEXT
from generators.image.qwen_21_runtime import validate_qwen_model_assets, QWEN_MODEL_IDENTIFIER, QWEN_MODEL_REVISION

VNCCS_HEARTBEAT_SECONDS = 5
VNCCS_STOP_TIMEOUT_SECONDS = 10


def build_vnccs_arguments(current_request_record, current_reference_images, current_cuda_generator, current_step_callback):
    validate_vnccs_profile(current_request_record)
    if len(current_reference_images) != 2:
        raise ValueError('VNCCS에는 아이덴티티·포즈 두 참조가 필요합니다.')
    return {'prompt': current_request_record['prompt'], 'image': [current_reference_images[1], current_reference_images[0]],
            'width': 512, 'height': 512, 'output_resolution': 512, 'num_inference_steps': 40,
            'true_cfg_scale': 1.0, 'use_kv_cache': True, 'generator': current_cuda_generator,
            'callback_on_step_end': current_step_callback}


def validate_vnccs_resources(current_available_bytes, current_process_rss, current_elapsed_seconds, current_execution_profile):
    if current_available_bytes < current_execution_profile['minimum_available_bytes']:
        raise RuntimeError('VNCCS 안전 중단: 시스템 메모리 여유가 12GiB 미만입니다.')
    if current_process_rss > current_execution_profile['maximum_rss_bytes']:
        raise RuntimeError('VNCCS 안전 중단: 작업 RSS가 42GiB를 초과했습니다.')
    if current_elapsed_seconds > current_execution_profile['maximum_seconds']:
        raise RuntimeError('VNCCS 안전 중단: GPU 실행이 20분을 초과했습니다.')


def execute_vnccs_generation(current_job_root, current_request_record):
    """공용 작업자의 GPU 잠금 안에서 실행한다. 자식도 같은 프로세스 그룹에 둔다."""
    import psutil
    validate_vnccs_profile(current_request_record)
    current_execution_profile = current_request_record['vnccs']
    validate_vnccs_resources(psutil.virtual_memory().available, 0, 0, current_execution_profile)
    current_started_time = time.monotonic()
    current_peak_rss = 0
    current_log_path = current_job_root / 'vnccs-pipeline.log'
    current_child_process = None
    try:
        with current_log_path.open('w') as current_log_stream:
            current_child_process = subprocess.Popen([sys.executable, '-m', 'generators.image.vnccs_runtime', str(current_job_root)], stdout=current_log_stream, stderr=subprocess.STDOUT)
            while current_child_process.poll() is None:
                try:
                    current_process_rss = psutil.Process(current_child_process.pid).memory_info().rss
                except psutil.NoSuchProcess:
                    current_child_process.wait()
                    break
                current_peak_rss = max(current_peak_rss, current_process_rss)
                current_available_bytes = psutil.virtual_memory().available
                current_elapsed_seconds = time.monotonic() - current_started_time
                current_recent_lines = current_log_path.read_text(errors='replace').splitlines()[-2:]
                print(f'{datetime.now().isoformat()}/vnccs/heartbeat rss={current_process_rss} available={current_available_bytes} elapsed={current_elapsed_seconds:.1f} log_bytes={current_log_path.stat().st_size} recent={current_recent_lines}', flush=True)
                validate_vnccs_resources(current_available_bytes, current_process_rss, current_elapsed_seconds, current_execution_profile)
                time.sleep(VNCCS_HEARTBEAT_SECONDS)
        if current_child_process.returncode:
            raise RuntimeError(f'VNCCS 파이프라인 실패: 종료 코드 {current_child_process.returncode}')
        print(f'{datetime.now().isoformat()}/vnccs/completed step=40/40 {VNCCS_QUALITY_WARNING_TEXT}', flush=True)
    except BaseException:
        if current_child_process is not None and current_child_process.poll() is None:
            current_child_process.terminate()
            try:
                current_child_process.wait(timeout=VNCCS_STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                current_child_process.kill()
                current_child_process.wait()
        if current_log_path.exists():
            print(current_log_path.read_text(errors='replace')[-6000:], flush=True)
        raise
    finally:
        (current_job_root / 'vnccs-resources.json').write_text(json.dumps({'peak_sampled_rss_bytes':current_peak_rss,'elapsed_seconds':time.monotonic()-current_started_time}, indent=2))


def run_vnccs_pipeline(current_job_root):
    import torch
    from PIL import Image
    from diffusers import QwenImage21Pipeline
    from tools.review.domains.image.three_reference_generation import verify_reference_snapshots, validate_three_reference_job_path
    from tools.review.domains.image.qwen_21_generation import verify_qwen_saved_request
    current_job_root = validate_three_reference_job_path(current_job_root)
    if current_job_root.parent.name != 'pose-transfer':
        raise ValueError('VNCCS 전용 포즈 변환 작업 경로가 필요합니다.')
    current_request_record = json.loads((current_job_root / 'request.json').read_text())
    validate_vnccs_profile(current_request_record)
    verify_reference_snapshots(current_job_root, current_request_record)
    verify_qwen_saved_request(current_job_root, current_request_record)
    if not torch.cuda.is_available():
        raise RuntimeError('VNCCS는 CUDA가 필요합니다. CPU 추론 대체 없음')
    current_lora_path = validate_vnccs_assets()
    current_model_root = validate_qwen_model_assets()
    current_progress_record = {'stage':'load','step':0,'total':40,'cuda_layer_calls':0}
    current_stop_event = threading.Event()

    def emit_vnccs_heartbeat():
        while not current_stop_event.wait(VNCCS_HEARTBEAT_SECONDS):
            print(f'{datetime.now().isoformat()}/vnccs/heartbeat {current_progress_record} cuda_bytes={torch.cuda.memory_allocated()}', flush=True)

    def record_vnccs_step(current_pipeline_value, current_step_index, current_timestep_value, current_callback_values):
        current_progress_record.update(stage='denoise', step=current_step_index+1)
        return current_callback_values

    def verify_vnccs_cuda(current_module_value, current_argument_values, current_output_value):
        if not isinstance(current_output_value, torch.Tensor) or current_output_value.device.type != 'cuda':
            raise RuntimeError('VNCCS 신경망 레이어 CUDA 출력 검증 실패')
        current_progress_record['cuda_layer_calls'] += 1

    print(f'{datetime.now().isoformat()}/vnccs/start output={current_job_root} model={current_model_root} lora={current_lora_path} inputs={current_request_record["references"]}', flush=True)
    threading.Thread(target=emit_vnccs_heartbeat, daemon=True).start()
    try:
        current_pipeline_value = QwenImage21Pipeline.from_pretrained(current_model_root, torch_dtype=torch.bfloat16, local_files_only=True, low_cpu_mem_usage=True)
        current_pipeline_value.load_lora_weights(str(current_lora_path))
        current_precision_record = {}
        for current_component_name in ('text_encoder','transformer','vae'):
            current_component_value = getattr(current_pipeline_value, current_component_name)
            current_dtype_values = {str(current_parameter.dtype) for current_parameter in current_component_value.parameters()}
            if current_dtype_values != {'torch.bfloat16'} or any('bitsandbytes' in type(current_module_value).__module__ for current_module_value in current_component_value.modules()):
                raise RuntimeError('VNCCS 비양자화 BF16 실행 계약 위반: '+current_component_name)
            current_precision_record[current_component_name] = sorted(current_dtype_values)
            for current_module_value in current_component_value.modules():
                if isinstance(current_module_value, (torch.nn.Linear,torch.nn.Conv2d,torch.nn.Conv3d)):
                    current_module_value.register_forward_hook(verify_vnccs_cuda)
        current_pipeline_value.enable_sequential_cpu_offload(device='cuda')
        current_reference_images = []
        for current_reference_name in current_request_record['references']:
            with Image.open(current_job_root / current_reference_name) as current_reference_image:
                current_reference_images.append(current_reference_image.convert('RGB'))
        current_progress_record['stage'] = 'inference'
        with torch.inference_mode():
            current_output_image = current_pipeline_value(**build_vnccs_arguments(current_request_record, current_reference_images, torch.Generator('cuda').manual_seed(current_request_record['seed']), record_vnccs_step)).images[0]
        if current_output_image.size != (512,512) or current_output_image.mode not in ('RGB','RGBA'):
            raise ValueError('VNCCS 출력 이미지 계약 불일치')
        current_output_image.save(current_job_root / 'result.png')
        current_result_record = {'model_id':QWEN_MODEL_IDENTIFIER,'revision':QWEN_MODEL_REVISION,'size':[512,512],'steps':40,'seed':current_request_record['seed'],'prompt':current_request_record['prompt'],'prompt_word_count':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'vnccs':current_request_record['vnccs'],'precision':current_precision_record,'peak_gpu_bytes':torch.cuda.max_memory_allocated(),'cuda_layer_calls':current_progress_record['cuda_layer_calls'],'quality_warnings':[VNCCS_QUALITY_WARNING_TEXT]}
        (current_job_root / 'result.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
        print(f'{datetime.now().isoformat()}/vnccs/completed {VNCCS_QUALITY_WARNING_TEXT}', flush=True)
    finally:
        current_stop_event.set()


if __name__ == '__main__':
    run_vnccs_pipeline(Path(sys.argv[1]))
