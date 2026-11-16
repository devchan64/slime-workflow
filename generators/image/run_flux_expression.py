"""공용 GPU 대기열의 FLUX 표정 이미지 실행기."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY, FLUX_MODEL_REVISION_VALUE
from tools.review.domains.image.three_reference_generation import verify_reference_snapshots


def execute_flux_expression_worker():
    current_parser_value = argparse.ArgumentParser()
    current_parser_value.add_argument('--job-dir', required=True)
    current_job_root = Path(current_parser_value.parse_args().job_dir).resolve()
    if current_job_root.parent != (WORKFLOW_ROOT_DIRECTORY/'.tmp/test/flux-expression-generator').resolve():
        raise ValueError('표정 작업 경로가 올바르지 않습니다.')
    current_request_record = json.loads((current_job_root/'request.json').read_text())
    verify_reference_snapshots(current_job_root, current_request_record)
    if current_request_record.get('flux_model_revision') != FLUX_MODEL_REVISION_VALUE or hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_request_record.get('prompt_sha256'):
        raise ValueError('프롬프트 또는 모델 기록이 일치하지 않습니다.')
    import torch
    from PIL import Image
    from diffusers import ModularPipeline
    from diffusers.modular_pipelines.components_manager import ComponentsManager
    from generators.common.numerical_guard import install_vae_decode_guard, require_finite_tensor
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_math_sdp(True)
    current_blocks_value = ModularPipeline.from_pretrained(FLUX_MODEL_ROOT_DIRECTORY,local_files_only=True).blocks
    current_blocks_value.sub_blocks.pop('prompt_upsampler')
    current_manager_value = ComponentsManager()
    current_pipeline_value = current_blocks_value.init_pipeline(FLUX_MODEL_ROOT_DIRECTORY,components_manager=current_manager_value)
    current_component_paths = {name:str(FLUX_MODEL_ROOT_DIRECTORY) for name in ('text_encoder','tokenizer','transformer','vae')}
    current_pipeline_value.load_components(dtype={'vae':torch.float32,'default':torch.bfloat16},pretrained_model_name_or_path=current_component_paths,local_files_only=True)
    current_pipeline_value.vae.disable_tiling()
    current_manager_value.enable_auto_cpu_offload(device='cuda',memory_reserve_margin='4GB')
    install_vae_decode_guard(current_pipeline_value.vae, torch)
    current_scheduler_step = current_pipeline_value.scheduler.step
    current_completed_steps = 0
    def validate_scheduler_step(*current_step_arguments, **current_step_keywords):
        nonlocal current_completed_steps
        current_step_result = current_scheduler_step(*current_step_arguments, **current_step_keywords)
        current_latent_value = current_step_result[0] if isinstance(current_step_result, (tuple, list)) else current_step_result.prev_sample
        require_finite_tensor(current_latent_value, torch, 'FLUX 디노이징 잠재값')
        current_completed_steps += 1
        print(f'stage=inference step={current_completed_steps}/{current_request_record["steps"]}', flush=True)
        return current_step_result
    current_pipeline_value.scheduler.step = validate_scheduler_step
    with Image.open(current_job_root/current_request_record['references'][0]) as current_image_file, torch.inference_mode():
        current_output_value = current_pipeline_value(prompt=current_request_record['prompt'],image=[current_image_file.convert('RGB')],width=current_request_record['width'],height=current_request_record['height'],num_inference_steps=current_request_record['steps'],generator=torch.Generator('cpu').manual_seed(current_request_record['seed']),output=['images'])
        current_output_value['images'][0].save(current_job_root/'result.png')
    current_output_hash = hashlib.sha256((current_job_root/'result.png').read_bytes()).hexdigest()
    (current_job_root/'result.json').write_text(json.dumps({'image_sha256':current_output_hash,'reference_sha256':current_request_record['reference_snapshots'][0]['sha256'],'prompt_sha256':current_request_record['prompt_sha256'],'model_revision':FLUX_MODEL_REVISION_VALUE,'seed':current_request_record['seed'],'steps':current_request_record['steps'],'width':current_request_record['width'],'height':current_request_record['height'],'torch_version':torch.__version__,'hip_version':torch.version.hip,'device_name':torch.cuda.get_device_name(),'allocated_peak_bytes':torch.cuda.max_memory_allocated(),'dtype':'bfloat16; vae float32'},ensure_ascii=False,indent=2))
    (current_job_root/'status.json').write_text(json.dumps({'status':'completed','image':f"/flux-expression-generator/jobs/{current_job_root.name}/result.png"},ensure_ascii=False))


if __name__ == '__main__':
    execute_flux_expression_worker()
