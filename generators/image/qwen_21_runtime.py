"""관리도구가 공유하는 고정 Qwen Image 2.1 GPU 실행 모듈."""
import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
QWEN_MODEL_IDENTIFIER = 'Qwen/Qwen-Image-2.1'
QWEN_MODEL_REVISION = 'd26bb61231c349cf6b7896fa83353113880e1ba3'
QWEN_MODEL_DIRECTORY = WORKFLOW_ROOT_PATH / '.model/qwen-image-2.1' / QWEN_MODEL_REVISION
QWEN_INFERENCE_STEPS = 40
QWEN_ALLOWED_INFERENCE_STEPS = (20, 30, 40, 50)


def validate_qwen_model_assets():
    for required_component_name in ('model_index.json', 'transformer/config.json', 'vae/config.json', 'text_encoder/config.json'):
        if not (QWEN_MODEL_DIRECTORY / required_component_name).is_file():
            raise FileNotFoundError(f'Qwen 2.1 모델 준비 필요: {QWEN_MODEL_IDENTIFIER}, {QWEN_MODEL_DIRECTORY}, 누락 {required_component_name}')
    for required_component_name in ('transformer', 'text_encoder'):
        current_component_root = QWEN_MODEL_DIRECTORY / required_component_name
        current_index_paths = list(current_component_root.glob('*.safetensors.index.json'))
        if len(current_index_paths) != 1:
            raise ValueError(f'Qwen 2.1 가중치 인덱스 누락 또는 중복: {current_component_root}')
        current_weight_index = json.loads(current_index_paths[0].read_text())
        for current_shard_name in set(current_weight_index['weight_map'].values()):
            if not (current_component_root / current_shard_name).is_file():
                raise FileNotFoundError(f'Qwen 2.1 가중치 누락: {current_component_root / current_shard_name}')
    if not (QWEN_MODEL_DIRECTORY / 'vae/diffusion_pytorch_model.safetensors').is_file():
        raise FileNotFoundError(f'Qwen 2.1 VAE 가중치 누락: {QWEN_MODEL_DIRECTORY}')
    return QWEN_MODEL_DIRECTORY


def execute_qwen_reference_generation(current_job_root, current_request_record, reference_image_paths):
    """로컬 모델만 로드하며 실패 시 다른 모델로 대체하지 않는다."""
    import torch
    from PIL import Image
    from diffusers import QwenImage21Pipeline

    if not torch.cuda.is_available():
        raise RuntimeError('Qwen 2.1 추론에 CUDA GPU가 필요합니다.')
    selected_inference_steps = current_request_record['steps']
    if type(selected_inference_steps) is not int or selected_inference_steps not in QWEN_ALLOWED_INFERENCE_STEPS:
        raise ValueError('Qwen 2.1 스텝은 20·30·40·50 중 선택해야 합니다.')
    if not 0 < len(current_request_record['prompt'].split()) < 100:
        raise ValueError('Qwen 2.1 프롬프트는 1~99단어여야 합니다.')
    current_model_root = validate_qwen_model_assets()
    current_progress_record = {'stage': 'loading', 'step': 0, 'total': selected_inference_steps}
    heartbeat_stop_event = threading.Event()

    def emit_generation_heartbeat():
        while not heartbeat_stop_event.wait(5):
            print(f'{datetime.now().isoformat()}/qwen21/heartbeat {current_progress_record}', flush=True)

    def record_inference_progress(current_pipeline_value, current_step_index, current_timestep_value, current_callback_values):
        current_progress_record['step'] = current_step_index + 1
        return current_callback_values

    threading.Thread(target=emit_generation_heartbeat, daemon=True).start()
    try:
        print(f'{datetime.now().isoformat()}/qwen21/load {current_model_root}', flush=True)
        current_pipeline_model = QwenImage21Pipeline.from_pretrained(current_model_root, torch_dtype=torch.bfloat16, local_files_only=True)
        current_pipeline_model.enable_sequential_cpu_offload()
        current_pipeline_model.vae.enable_tiling()
        reference_image_values = []
        for reference_image_path in reference_image_paths:
            with Image.open(reference_image_path) as current_reference_image:
                reference_image_values.append(current_reference_image.convert('RGB'))
        current_progress_record['stage'] = 'inference'
        with torch.inference_mode():
            generated_output_image = current_pipeline_model(
                image=reference_image_values or None, prompt=current_request_record['prompt'],
                width=current_request_record['width'], height=current_request_record['height'],
                num_inference_steps=selected_inference_steps,
                generator=torch.Generator('cuda').manual_seed(current_request_record['seed']),
                callback_on_step_end=record_inference_progress,
            ).images[0]
        if generated_output_image.size != (current_request_record['width'], current_request_record['height']):
            raise ValueError(f'Qwen 2.1 출력 크기 불일치: {generated_output_image.size}')
        generated_output_image.save(current_job_root / 'result.png')
        current_result_record = {
            'model_id': QWEN_MODEL_IDENTIFIER, 'revision': QWEN_MODEL_REVISION,
            'size': list(generated_output_image.size), 'steps': selected_inference_steps,
            'seed': current_request_record['seed'], 'prompt': current_request_record['prompt'],
            'prompt_word_count': len(current_request_record['prompt'].split()),
            'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),
            'peak_gpu_bytes': torch.cuda.max_memory_allocated(), 'quality_warnings': [],
        }
        (current_job_root / 'result.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
        print(f'{datetime.now().isoformat()}/qwen21/complete 결과 저장', flush=True)
    finally:
        heartbeat_stop_event.set()
