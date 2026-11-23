"""공식 Animate-2 ModularPipeline을 ROCm GPU 상주 연산로 실행한다."""
import hashlib
from functools import wraps
import os
def configure_animate_memory_allocator(current_environment_values):
    """GPU 초기화 전에 검증된 할당 정책을 고정하고 이전 별칭 충돌을 제거한다."""
    current_environment_values.pop('PYTORCH_CUDA_ALLOC_CONF', None)
    current_environment_values['PYTORCH_ALLOC_CONF'] = 'expandable_segments:False'


configure_animate_memory_allocator(os.environ)
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE, ANIMATE_MODEL_DIRECTORY, ANIMATE_MODEL_IDENTIFIER, ANIMATE_MODEL_REVISION, ANIMATE_RUNTIME_DIRECTORY, ANIMATE_RUNTIME_REVISION, ANIMATE_OUTPUT_FRAME_RATE, validate_animate_assets
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs


def check_animate_finite_tensor(current_tensor_value, current_torch_module, current_stage_name):
    """스케줄러에 전달되는 GPU 텐서의 비유한 값을 실패로 처리한다."""
    if isinstance(current_tensor_value, current_torch_module.Tensor) and (current_tensor_value.is_floating_point() or current_tensor_value.is_complex()):
        if not bool(current_torch_module.isfinite(current_tensor_value).all().item()):
            raise ValueError(f'Animate2 {current_stage_name}에 NaN 또는 무한대가 있습니다.')


def validate_animate_output_frames(current_frame_arrays, current_numpy_module):
    """비유한 프레임을 정수로 변환해 정상 결과로 저장하지 않는다."""
    if not bool(current_numpy_module.isfinite(current_frame_arrays).all()):
        raise ValueError('Animate2 출력 프레임에 NaN 또는 무한대가 있습니다.')
    return current_frame_arrays


def guard_animate_vae_encoding(current_encode_function, current_torch_module):
    """참조 영상과 이미지의 VAE 잠재값을 사용하기 전에 검증한다."""
    def encode_checked_animate_video(*current_encode_arguments, **current_encode_keywords):
        current_latent_tensor = current_encode_function(*current_encode_arguments, **current_encode_keywords)
        check_animate_finite_tensor(current_latent_tensor, current_torch_module, 'VAE 인코딩 출력')
        return current_latent_tensor
    return encode_checked_animate_video


def install_animate_vae_math_attention(current_vae_model):
    """VAE 인코딩·디코딩 안에서만 수학 SDPA를 선택한다."""
    from torch.nn.attention import SDPBackend, sdpa_kernel

    for current_method_name in ('encode', 'decode'):
        current_original_method = getattr(current_vae_model, current_method_name)

        def build_guarded_vae_method(current_vae_method):
            @wraps(current_vae_method)
            def execute_with_math_attention(*current_method_arguments, **current_method_keywords):
                with sdpa_kernel(SDPBackend.MATH):
                    return current_vae_method(*current_method_arguments, **current_method_keywords)
            return execute_with_math_attention

        setattr(current_vae_model, current_method_name, build_guarded_vae_method(current_original_method))


def load_animate_gpu_components(current_pipeline_model, current_load_options):
    """모델은 장치에 직접 적재하고, 실패·CPU 대체를 허용하지 않는다."""
    for current_component_name in ('transformer','text_encoder','image_encoder','vae'):
        current_pipeline_model.load_components(names=[current_component_name],device_map='cuda',**current_load_options)
        current_component_model=getattr(current_pipeline_model,current_component_name,None)
        if current_component_model is None:
            raise RuntimeError(f'공식 모델 구성요소 로드 실패: {current_component_name}')
        if any(current_parameter.device.type != 'cuda' for current_parameter in current_component_model.parameters()):
            raise RuntimeError(f'모델 구성요소 GPU 적재 실패: {current_component_name}')
    current_pipeline_model.load_components(names=['tokenizer','scheduler'],**current_load_options)


def execute_animate_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    current_lora_mode = current_request_record.get('lora_mode', 'none')
    if current_lora_mode not in ('none', 'lightx2v'):
        raise ValueError('지원하지 않는 Animate-2 LoRA 선택입니다.')
    if current_lora_mode == 'lightx2v':
        from generators.wan_animate2.lightx2v_assets import validate_lightx2v
        validate_lightx2v()
    sys.path.insert(0,str(ANIMATE_RUNTIME_DIRECTORY/'src'))
    import torch
    import numpy as np
    from diffusers import ModularPipeline
    from diffusers.utils import load_image, load_video
    from diffusers.modular_pipelines.wan_animate_2 import encoders as animate_encoder_module, denoise as animate_denoise_module
    from generators.wan_animate2.attention_compile import enable_compiled_attention
    enable_compiled_attention()
    from diffusers.models.transformers import transformer_wan_animate_2 as current_transformer_module
    from generators.wan_animate2.attention_layout import install_animate_reference_layout
    install_animate_reference_layout(current_transformer_module,torch)
    current_checked_vae_encode=guard_animate_vae_encoding(animate_encoder_module.encode_vae,torch)
    animate_encoder_module.encode_vae=current_checked_vae_encode
    animate_denoise_module.encode_vae=current_checked_vae_encode
    current_video_path=current_job_root/'driving.mp4'
    if current_request_record['driving_video_file']!='driving.mp4' or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record['driving_video_sha256']:
        raise ValueError('동작 영상 사본 해시 불일치')
    current_metrics_recorder.update_generation_stage('model-load')
    current_pipeline_model=ModularPipeline.from_pretrained(str(ANIMATE_MODEL_DIRECTORY),local_files_only=True)
    current_load_options=dict(dtype=torch.bfloat16,pretrained_model_name_or_path=str(ANIMATE_MODEL_DIRECTORY),revision=None,local_files_only=True)
    load_animate_gpu_components(current_pipeline_model,current_load_options)
    for current_component_name in ('transformer','text_encoder','image_encoder','vae','tokenizer','scheduler'):
        if getattr(current_pipeline_model,current_component_name,None) is None:
            raise RuntimeError(f'공식 모델 구성요소 로드 실패: {current_component_name}')
    if current_lora_mode == 'lightx2v':
        from generators.wan_animate2.lightx2v_assets import PATH, SHA256, validate_lightx2v
        from generators.wan_animate2.lightx2v import apply_lightx2v_weights
        from generators.wan_animate2.lightx2v_scheduler import AnimateLightX2VScheduler
        from diffusers import ClassifierFreeGuidance
        validate_lightx2v()
        current_applied_weights = apply_lightx2v_weights(current_pipeline_model.transformer, PATH)
        current_pipeline_model.update_components(scheduler=AnimateLightX2VScheduler(), guider=ClassifierFreeGuidance(guidance_scale=1.0))
        print(f'Animate-2 LightX2V applied={current_applied_weights} sha256={SHA256} steps={current_request_record["steps"]} cfg=1 shift=5 sampler=lcm',flush=True)
    install_animate_vae_math_attention(current_pipeline_model.vae)
    # 체크포인트의 Transformers 4.57 UMT5는 encoder와 shared 임베딩을 공유한다.
    # Transformers 5의 분리 초기화가 원본 가중치를 대신하지 않도록 공식 setter로 연결한다.
    current_pipeline_model.text_encoder.set_input_embeddings(current_pipeline_model.text_encoder.shared)
    if current_pipeline_model.text_encoder.encoder.embed_tokens.weight is not current_pipeline_model.text_encoder.shared.weight:
        raise RuntimeError('UMT5 원본 공유 임베딩 연결 실패')
    current_source_frames,current_source_rate=load_video(str(current_video_path),return_fps=True)
    current_frame_count=current_request_record['frames']
    current_frame_indices=np.round(np.arange(current_frame_count)*current_source_rate/ANIMATE_OUTPUT_FRAME_RATE).astype(int)
    if current_frame_indices[-1]>=len(current_source_frames):
        raise ValueError('16fps 기준 동작 영상 길이 부족')
    current_driving_frames=[current_source_frames[int(current_frame_index)] for current_frame_index in current_frame_indices]
    current_metrics_recorder.update_generation_stage('inference')
    current_scheduler_step=current_pipeline_model.scheduler.step
    current_completed_steps=[0]
    def record_scheduler_step(*current_step_arguments,**current_step_keywords):
        current_model_output=current_step_keywords.get('model_output',current_step_arguments[0] if current_step_arguments else None)
        current_input_sample=current_step_keywords.get('sample',current_step_arguments[2] if len(current_step_arguments)>2 else None)
        check_animate_finite_tensor(current_model_output,torch,'스케줄러 예측값')
        check_animate_finite_tensor(current_input_sample,torch,'스케줄러 입력')
        current_step_result=current_scheduler_step(*current_step_arguments,**current_step_keywords)
        current_previous_sample=getattr(current_step_result,'prev_sample',None)
        if current_previous_sample is None and isinstance(current_step_result,(tuple,list)) and current_step_result:
            current_previous_sample=current_step_result[0]
        check_animate_finite_tensor(current_previous_sample,torch,'스케줄러 출력')
        current_completed_steps[0]+=1
        current_metrics_recorder.record_generation_step(current_completed_steps[0])
        return current_step_result
    current_pipeline_model.scheduler.step=record_scheduler_step
    current_output_videos=current_pipeline_model(image=load_image(str(current_job_root/current_request_record['references'][0])),driving_video=current_driving_frames,driving_video_fps=ANIMATE_OUTPUT_FRAME_RATE,fps=ANIMATE_OUTPUT_FRAME_RATE,prompt=current_request_record['prompt'],height=480,width=832,segment_frame_length=current_frame_count,num_inference_steps=current_request_record['steps'],generator=torch.Generator(device='cuda').manual_seed(current_request_record['seed']),output='videos')
    current_frame_arrays=validate_animate_output_frames(np.asarray(current_output_videos[0]),np)
    if current_frame_arrays.dtype!=np.uint8:
        current_frame_arrays=np.rint(np.clip(current_frame_arrays,0,1)*255).astype(np.uint8)
    if len(current_frame_arrays)!=current_frame_count:
        raise ValueError(f'공식 출력 프레임 불일치: {len(current_frame_arrays)} / {current_frame_count}')
    current_metrics_recorder.update_generation_stage('postprocess')
    current_output_hashes=save_video_outputs(current_attempt_root,current_frame_arrays,ANIMATE_OUTPUT_FRAME_RATE)
    return {'attempt':current_attempt_root.name,'frames':current_frame_count,'fps':ANIMATE_OUTPUT_FRAME_RATE,'output_sha256':current_output_hashes,'model_id':ANIMATE_MODEL_IDENTIFIER,'model_revision':ANIMATE_MODEL_REVISION,'runtime_revision':ANIMATE_RUNTIME_REVISION,'lora_mode':current_lora_mode,'lora_sha256':SHA256 if current_lora_mode == 'lightx2v' else None,'sampler':'lcm-simple-shift5-cfg1' if current_lora_mode == 'lightx2v' else 'base','prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'attention_execution':'inductor-fullgraph-isolated','vae_attention_backend':'math','reference_kv_offload':None,'compute_backend':'rocm','weight_offload':None,'cuda_allocator':'expandable_segments:False','quality_status':'사용자 검수 대기'}

if __name__=='__main__':
    run_reference_video_worker(ANIMATE_JOB_STORAGE,Path(__file__),validate_animate_assets,execute_animate_inference)
