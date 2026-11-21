"""공용 GPU 대기열의 FLUX 용도별 이미지 실행기."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.management.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY, FLUX_MODEL_REVISION_VALUE
from tools.management.domains.image.three_reference_generation import verify_reference_snapshots


def execute_flux_image_worker():
    current_parser_value = argparse.ArgumentParser()
    current_parser_value.add_argument('--job-dir', required=True)
    current_job_root = Path(current_parser_value.parse_args().job_dir).resolve()
    from tools.management.domains.image.flux_image_generation import FLUX_IMAGE_PROFILE_RECORDS
    current_profile_name = current_job_root.parent.name.removesuffix('-generator')
    if current_profile_name not in FLUX_IMAGE_PROFILE_RECORDS or current_job_root.parent != (WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/(current_profile_name+'-generator')).resolve():
        raise ValueError('FLUX 이미지 작업 경로가 올바르지 않습니다.')
    current_request_record = json.loads((current_job_root/'request.json').read_text())
    verify_reference_snapshots(current_job_root, current_request_record)
    if current_request_record.get('profile') != current_profile_name or current_request_record.get('flux_model_revision') != FLUX_MODEL_REVISION_VALUE or hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_request_record.get('prompt_sha256'):
        raise ValueError('프롬프트 또는 모델 기록이 일치하지 않습니다.')
    current_seamless_method = current_request_record.get('seamless_method','edge-blend') if current_profile_name == 'flux-seamless' else None
    if current_seamless_method not in (None,'global-periodic-v1','circular-vae-v2','circular-vae','edge-blend'):
        raise ValueError('지원하지 않는 심리스 처리 방식입니다.')
    if current_seamless_method == 'global-periodic-v1' and (current_request_record.get('width') != 512 or current_request_record.get('height') != 512 or current_request_record.get('references') or current_request_record.get('steps') != 16):
        raise ValueError('전역 주기 어텐션은 512×512 무참조 16단계만 지원합니다.')
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
    from generators.image.flux_gpu_resident import load_flux_resident_components
    load_flux_resident_components(current_pipeline_value, torch, FLUX_MODEL_ROOT_DIRECTORY)
    current_pipeline_value.vae.disable_tiling()
    install_vae_decode_guard(current_pipeline_value.vae, torch)
    current_patched_layer_count = 0
    if current_seamless_method in ('global-periodic-v1','circular-vae','circular-vae-v2'):
        current_decoder_layers=[layer for layer in current_pipeline_value.vae.decoder.modules() if isinstance(layer,torch.nn.Conv2d) and any(layer.padding)]
        if not current_decoder_layers:
            raise ValueError('순환 패딩을 적용할 VAE 디코더 합성곱이 없습니다.')
        current_patched_layer_count=len(current_decoder_layers)
        if current_seamless_method in ('global-periodic-v1','circular-vae-v2'):
            for current_layer_value in current_decoder_layers:
                current_layer_value.padding_mode='circular'
        else:
            current_ordinary_decode=current_pipeline_value.vae.decode
            current_original_modes=[layer.padding_mode for layer in current_decoder_layers]
            current_decode_calls=0
            def decode_with_circular_boundary(*current_decode_args,**current_decode_kwargs):
                nonlocal current_decode_calls
                current_decode_calls += 1
                if current_decode_calls != 1:
                    raise ValueError('예상하지 못한 추가 VAE 디코딩입니다.')
                current_ordinary_result=current_ordinary_decode(*current_decode_args,**current_decode_kwargs)
                current_ordinary_tensor=current_ordinary_result[0] if isinstance(current_ordinary_result,(tuple,list)) else current_ordinary_result.sample
                current_pipeline_value.image_processor.postprocess(current_ordinary_tensor,output_type='pil')[0].save(current_job_root/'raw-result.png')
                try:
                    for current_layer_value in current_decoder_layers: current_layer_value.padding_mode='circular'
                    return current_ordinary_decode(*current_decode_args,**current_decode_kwargs)
                finally:
                    for current_layer_value,current_original_mode in zip(current_decoder_layers,current_original_modes): current_layer_value.padding_mode=current_original_mode
            current_pipeline_value.vae.decode=decode_with_circular_boundary
    if current_seamless_method == 'global-periodic-v1':
        from generators.image.flux_global_periodic_attention import GLOBAL_PERIODIC_SHIFT_SEQUENCE, install_global_periodic_attention
        current_periodic_calls, current_image_block_count, current_joint_block_count = install_global_periodic_attention(current_pipeline_value, require_finite_tensor)
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
    current_reference_images = []
    for current_reference_name in current_request_record['references']:
        with Image.open(current_job_root/current_reference_name) as current_image_file:
            current_reference_images.append(current_image_file.convert('RGB').copy())
    current_pipeline_arguments = {'prompt':current_request_record['prompt'],'width':current_request_record['width'],'height':current_request_record['height'],'num_inference_steps':current_request_record['steps'],'generator':torch.Generator('cpu').manual_seed(current_request_record['seed']),'output':['images']}
    if current_reference_images:
        current_pipeline_arguments['image'] = current_reference_images
    with torch.inference_mode():
        current_output_value = current_pipeline_value(**current_pipeline_arguments)
        if current_seamless_method == 'global-periodic-v1' and current_periodic_calls[0] != 16:
            raise ValueError('전역 주기 디노이저 호출 횟수가 올바르지 않습니다.')
        current_output_image = current_output_value['images'][0]
        if current_profile_name == 'flux-seamless':
            from tools.management.domains.image.flux_seamless_output import blend_opposite_tile_edges, build_repeated_tile_preview
            if current_seamless_method == 'circular-vae':
                with Image.open(current_job_root/'raw-result.png') as current_raw_image:
                    current_blended_image=blend_opposite_tile_edges(current_raw_image)
                current_blended_image.save(current_job_root/'blend-result.png')
                build_repeated_tile_preview(current_blended_image).save(current_job_root/'blend-preview.png')
            elif current_seamless_method == 'edge-blend':
                current_output_image.save(current_job_root/'raw-result.png')
                current_output_image = blend_opposite_tile_edges(current_output_image)
            build_repeated_tile_preview(current_output_image).save(current_job_root/'tiled-preview.png')
        current_output_image.save(current_job_root/'result.png')
    current_output_hash = hashlib.sha256((current_job_root/'result.png').read_bytes()).hexdigest()
    current_result_record={'image_sha256':current_output_hash,'reference_sha256':[item['sha256'] for item in current_request_record['reference_snapshots']],'prompt_sha256':current_request_record['prompt_sha256'],'model_revision':FLUX_MODEL_REVISION_VALUE,'seed':current_request_record['seed'],'steps':current_request_record['steps'],'width':current_request_record['width'],'height':current_request_record['height'],'torch_version':torch.__version__,'hip_version':torch.version.hip,'device_name':torch.cuda.get_device_name(),'allocated_peak_bytes':torch.cuda.max_memory_allocated(),'dtype':'bfloat16; vae float32','offload':'none','device_policy':'rocm-gpu-resident-v1'}
    if current_profile_name == 'flux-seamless':
        current_result_record['edge_processing'] = {'method':current_seamless_method,'decoder_patched_conv2d_count':current_patched_layer_count,'preview_sha256':hashlib.sha256((current_job_root/'tiled-preview.png').read_bytes()).hexdigest()}
        if current_seamless_method not in ('global-periodic-v1','circular-vae-v2'):
            current_result_record['edge_processing']['raw_sha256']=hashlib.sha256((current_job_root/'raw-result.png').read_bytes()).hexdigest()
        if current_seamless_method == 'global-periodic-v1':
            current_result_record['edge_processing'].update(shifts=GLOBAL_PERIODIC_SHIFT_SEQUENCE, transformer_calls=current_periodic_calls[0], image_attention_blocks=current_image_block_count, joint_attention_blocks=current_joint_block_count, vae_tiling=False)
        if current_seamless_method == 'circular-vae':
            current_result_record['edge_processing']['blend_sha256']=hashlib.sha256((current_job_root/'blend-result.png').read_bytes()).hexdigest()
            current_result_record['edge_processing']['blend_preview_sha256']=hashlib.sha256((current_job_root/'blend-preview.png').read_bytes()).hexdigest()
    (current_job_root/'result.json').write_text(json.dumps(current_result_record,ensure_ascii=False,indent=2))
    (current_job_root/'status.json').write_text(json.dumps({'status':'completed','image':f"/{current_profile_name}-generator/jobs/{current_job_root.name}/result.png"},ensure_ascii=False))


if __name__ == '__main__':
    execute_flux_image_worker()
