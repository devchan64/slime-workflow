"""Qwen-Image-2512 표준 텍스트→이미지 생성기."""
from __future__ import annotations
import hashlib
import json
import logging
import time
from pathlib import Path

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXED_MODEL_IDENTIFIER = 'Qwen/Qwen-Image-2512'
FIXED_MODEL_REVISION = 'main'
FIXED_MODEL_DIRECTORY = WORKFLOW_REPOSITORY_ROOT / '.model/qwen-image-2512' / FIXED_MODEL_REVISION
FIXED_LIGHTNING_REPOSITORY = 'lightx2v/Qwen-Image-2512-Lightning'
FIXED_LIGHTNING_REVISION = 'main'
FIXED_LIGHTNING_FILENAME = 'Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors'
FIXED_LIGHTNING_DIRECTORY = WORKFLOW_REPOSITORY_ROOT / '.model/qwen-image-2512-lightning' / FIXED_LIGHTNING_REVISION
FIXED_LIGHTNING_SHA256 = 'de0d236e54ecf2c43b32447d13478c6eae0d361b1fed48c69675b084fa240d87'
FIXED_LIGHTNING_SIZE = 849608296
FIXED_INFERENCE_STEPS = 4
FIXED_GENERATOR_SEED = 251204

def calculate_file_sha256(source_file_path: Path) -> str:
    with source_file_path.open('rb') as source_file:
        return hashlib.file_digest(source_file, 'sha256').hexdigest()

def validate_qwen_2512_assets(*, enable_lightning_adapter=True, verify_adapter_hash=True) -> tuple[Path, Path]:
    model_index_path = FIXED_MODEL_DIRECTORY / 'model_index.json'
    lightning_file_path = FIXED_LIGHTNING_DIRECTORY / FIXED_LIGHTNING_FILENAME
    if not model_index_path.is_file():
        raise FileNotFoundError(f'모델 준비 필요: model_id={FIXED_MODEL_IDENTIFIER} model_path={FIXED_MODEL_DIRECTORY}')
    required_model_files = ['transformer/config.json','transformer/diffusion_pytorch_model.safetensors.index.json','text_encoder/config.json','text_encoder/model.safetensors.index.json','vae/config.json','vae/diffusion_pytorch_model.safetensors','scheduler/scheduler_config.json','tokenizer/tokenizer_config.json','tokenizer/vocab.json','tokenizer/merges.txt']
    for required_model_file in required_model_files:
        if not (FIXED_MODEL_DIRECTORY/required_model_file).is_file():
            raise FileNotFoundError(f'모델 다운로드 미완료: model_id={FIXED_MODEL_IDENTIFIER} model_path={FIXED_MODEL_DIRECTORY} missing={required_model_file}')
    for current_index_name in ('transformer/diffusion_pytorch_model.safetensors.index.json','text_encoder/model.safetensors.index.json'):
        current_index_path=FIXED_MODEL_DIRECTORY/current_index_name
        current_index_record=json.loads(current_index_path.read_text())
        for current_shard_name in set(current_index_record['weight_map'].values()):
            current_shard_path=current_index_path.parent/current_shard_name
            if not current_shard_path.is_file() or current_shard_path.stat().st_size==0:
                raise FileNotFoundError(f'모델 가중치 다운로드 미완료: {current_shard_path}')
    if not enable_lightning_adapter:
        return model_index_path, lightning_file_path
    if not lightning_file_path.is_file():
        raise FileNotFoundError(f'Lightning 준비 필요: model_id={FIXED_LIGHTNING_REPOSITORY} model_path={lightning_file_path}')
    if lightning_file_path.stat().st_size != FIXED_LIGHTNING_SIZE or (verify_adapter_hash and calculate_file_sha256(lightning_file_path) != FIXED_LIGHTNING_SHA256):
        raise ValueError(f'Lightning 파일 크기/SHA-256 불일치: {lightning_file_path}')
    return model_index_path, lightning_file_path

def generate_qwen_2512_lightning_image(*, output_directory: Path, prompt_text: str, width: int = 1024, height: int = 1024, selected_inference_steps: int = 4) -> dict:
    if not prompt_text.strip():
        raise ValueError('생성 프롬프트가 비어 있습니다.')
    if type(width) is not int or type(height) is not int or width < 256 or height < 256 or width > 1664 or height > 1664 or width % 16 or height % 16:
        raise ValueError('출력 크기는 16의 배수인 256 이상 정수여야 합니다.')
    if type(selected_inference_steps) is not int or selected_inference_steps not in (4,30):
        raise ValueError('생성 스텝은 4 또는 30이어야 합니다.')
    enable_lightning_adapter = selected_inference_steps == 4
    selected_guidance_scale = 1.0 if enable_lightning_adapter else 4.0
    _, lightning_file_path = validate_qwen_2512_assets(enable_lightning_adapter=enable_lightning_adapter)
    output_directory = output_directory.resolve()
    if not output_directory.is_relative_to((WORKFLOW_REPOSITORY_ROOT / '.tmp/test').resolve()):
        raise ValueError('후보 생성 결과는 저장소 .tmp 하위만 허용합니다.')
    output_directory.mkdir(parents=True, exist_ok=True)
    output_image_path = output_directory / 'result.png'
    if output_image_path.exists():
        raise FileExistsError(f'기존 결과를 덮어쓸 수 없습니다: {output_image_path}')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s/qwen-image-2512/%(message)s')
    started_at = time.monotonic()
    import torch
    from diffusers import QwenImagePipeline
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA를 사용할 수 없어 중단합니다. CPU 추론은 지원하지 않습니다.')
    logging.info('stage=load')
    pipeline = QwenImagePipeline.from_pretrained(str(FIXED_MODEL_DIRECTORY), torch_dtype=torch.bfloat16, local_files_only=True)
    if enable_lightning_adapter:
        pipeline.load_lora_weights(str(lightning_file_path.parent), weight_name=lightning_file_path.name, local_files_only=True)
    pipeline.enable_sequential_cpu_offload()
    def record_denoise_progress(current_pipeline_value,current_step_index,current_timestep_value,current_callback_values):
        logging.info('denoise step=%s/%s',current_step_index+1,selected_inference_steps)
        return current_callback_values
    logging.info('stage=inference')
    result_image = pipeline(callback_on_step_end=record_denoise_progress,prompt=prompt_text.strip(), width=width, height=height, negative_prompt=" ", num_inference_steps=selected_inference_steps, true_cfg_scale=selected_guidance_scale, guidance_scale=1.0, generator=torch.Generator(device='cuda').manual_seed(FIXED_GENERATOR_SEED)).images[0]
    result_image.save(output_image_path)
    result_record = {'status': 'completed', 'model_id': FIXED_MODEL_IDENTIFIER, 'model_revision': FIXED_MODEL_REVISION, 'lightning_repository': FIXED_LIGHTNING_REPOSITORY if enable_lightning_adapter else None, 'lightning_revision': FIXED_LIGHTNING_REVISION if enable_lightning_adapter else None, 'lightning_file': FIXED_LIGHTNING_FILENAME if enable_lightning_adapter else None, 'steps': selected_inference_steps, 'lightning_lora': enable_lightning_adapter, 'true_cfg_scale': selected_guidance_scale, 'seed': FIXED_GENERATOR_SEED, 'size': [width, height], 'prompt_sha256': hashlib.sha256(prompt_text.strip().encode()).hexdigest(), 'elapsed_seconds': round(time.monotonic() - started_at, 2), 'output': 'result.png'}
    (output_directory / 'result.json').write_text(json.dumps(result_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result_record
