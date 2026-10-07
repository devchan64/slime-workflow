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
        if 'circular_vae' in current_request_record:
            from generators.image.qwen_21_circular import apply_circular_decoder, install_circular_halo_decode, CIRCULAR_SELECTABLE_CONFIGURATIONS, CIRCULAR_TANGENT_ONE_SELECTABLE_CONFIGURATIONS, CIRCULAR_PREVIOUS_SELECTABLE_CONFIGURATIONS, CIRCULAR_VAE_CONFIGURATION, CIRCULAR_TANGENT_ONE_CONFIGURATION, CIRCULAR_PREVIOUS_VAE_CONFIGURATION, CIRCULAR_CORNER_CONFIGURATION, CIRCULAR_DOUBLE_STRIP_CONFIGURATION, CIRCULAR_SINGLE_STRIP_CONFIGURATION, CIRCULAR_VERTICAL_CONFIGURATION, CIRCULAR_COMPARISON_CONFIGURATION, CIRCULAR_LEGACY_CONFIGURATION, CIRCULAR_HALO_CONFIGURATION
            from generators.image.qwen_21_toroidal import TOROIDAL_LEGACY_CONFIGURATION, TOROIDAL_ATTENTION_CONFIGURATION
            if current_request_record['circular_vae'] in (*CIRCULAR_SELECTABLE_CONFIGURATIONS, *CIRCULAR_TANGENT_ONE_SELECTABLE_CONFIGURATIONS, *CIRCULAR_PREVIOUS_SELECTABLE_CONFIGURATIONS, CIRCULAR_VAE_CONFIGURATION, CIRCULAR_TANGENT_ONE_CONFIGURATION, CIRCULAR_PREVIOUS_VAE_CONFIGURATION, CIRCULAR_CORNER_CONFIGURATION, CIRCULAR_DOUBLE_STRIP_CONFIGURATION, CIRCULAR_SINGLE_STRIP_CONFIGURATION, CIRCULAR_VERTICAL_CONFIGURATION, CIRCULAR_COMPARISON_CONFIGURATION, TOROIDAL_LEGACY_CONFIGURATION, TOROIDAL_ATTENTION_CONFIGURATION):
                from generators.image.qwen_21_toroidal import install_toroidal_attention
                patched_block_count = install_toroidal_attention(current_pipeline_model, current_request_record)
                if current_request_record['circular_vae'] in (*CIRCULAR_SELECTABLE_CONFIGURATIONS, *CIRCULAR_TANGENT_ONE_SELECTABLE_CONFIGURATIONS, *CIRCULAR_PREVIOUS_SELECTABLE_CONFIGURATIONS, CIRCULAR_VAE_CONFIGURATION, CIRCULAR_TANGENT_ONE_CONFIGURATION, CIRCULAR_PREVIOUS_VAE_CONFIGURATION, CIRCULAR_CORNER_CONFIGURATION, CIRCULAR_DOUBLE_STRIP_CONFIGURATION, CIRCULAR_SINGLE_STRIP_CONFIGURATION, CIRCULAR_VERTICAL_CONFIGURATION, CIRCULAR_COMPARISON_CONFIGURATION):
                    from generators.image.qwen_21_circular import install_circular_comparison
                    if current_request_record['circular_vae']['baseline_decode']:
                        install_circular_comparison(current_pipeline_model, current_job_root)
                    else:
                        apply_circular_decoder(current_pipeline_model.vae)
                else:
                    current_pipeline_model.vae.enable_tiling()
                print(f'{datetime.now().isoformat()}/qwen21/toroidal 생성 토큰 경계 K/V · {patched_block_count}개 블록 · VAE 설정 {current_request_record["circular_vae"]["vae"]}', flush=True)
            elif current_request_record['circular_vae'] == CIRCULAR_HALO_CONFIGURATION:
                install_circular_halo_decode(current_pipeline_model, current_job_root)
                print(f'{datetime.now().isoformat()}/qwen21/circular 잠재 여백 8 · 일반/순환 동일 잠재값 비교 · 분할 없음', flush=True)
            elif current_request_record['circular_vae'] == CIRCULAR_LEGACY_CONFIGURATION:
                patched_module_count = apply_circular_decoder(current_pipeline_model.vae)
                print(f'{datetime.now().isoformat()}/qwen21/circular 기존 디코더 {patched_module_count}개 · XY 순환', flush=True)
            else:
                raise ValueError('순환 VAE 고정 설정 불일치')
        else:
            current_pipeline_model.vae.enable_tiling()
        current_pipeline_model.enable_sequential_cpu_offload()
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
        if 'circular_vae' in current_request_record:
            repeated_output_image = Image.new('RGB', (generated_output_image.width * 3, generated_output_image.height * 3))
            for repeated_row_index in range(3):
                for repeated_column_index in range(3):
                    repeated_output_image.paste(generated_output_image, (repeated_column_index * generated_output_image.width, repeated_row_index * generated_output_image.height))
            repeated_output_image.save(current_job_root / 'tiled-preview.png')
            if (current_job_root / 'baseline.png').is_file():
                with Image.open(current_job_root / 'baseline.png') as baseline_output_image:
                    for repeated_row_index in range(3):
                        for repeated_column_index in range(3):
                            repeated_output_image.paste(baseline_output_image, (repeated_column_index * baseline_output_image.width, repeated_row_index * baseline_output_image.height))
                    repeated_output_image.save(current_job_root / 'baseline-preview.png')
        current_result_record = {
            'model_id': QWEN_MODEL_IDENTIFIER, 'revision': QWEN_MODEL_REVISION,
            'size': list(generated_output_image.size), 'steps': selected_inference_steps,
            'seed': current_request_record['seed'], 'prompt': current_request_record['prompt'],
            'prompt_word_count': len(current_request_record['prompt'].split()),
            'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),
            'circular_vae': current_request_record.get('circular_vae'),
            'peak_gpu_bytes': torch.cuda.max_memory_allocated(), 'quality_warnings': [],
        }
        (current_job_root / 'result.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
        print(f'{datetime.now().isoformat()}/qwen21/complete 결과 저장', flush=True)
    finally:
        heartbeat_stop_event.set()
