"""공식 Animate-2 ModularPipeline을 CUDA 연산·CPU 가중치 오프로드로 실행한다."""
import hashlib
import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE, ANIMATE_MODEL_DIRECTORY, ANIMATE_MODEL_IDENTIFIER, ANIMATE_MODEL_REVISION, ANIMATE_RUNTIME_DIRECTORY, ANIMATE_RUNTIME_REVISION, validate_animate_assets
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs


def execute_animate_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    sys.path.insert(0,str(ANIMATE_RUNTIME_DIRECTORY/'src'))
    import torch
    import numpy as np
    from diffusers import ModularPipeline
    from diffusers.hooks import apply_group_offloading
    from diffusers.utils import load_image, load_video
    from diffusers.models.transformers.transformer_wan_animate_2 import WanAnimate2KVLayerCache
    from generators.wan_animate2.cache_offload import enable_reference_cache_offload
    enable_reference_cache_offload(WanAnimate2KVLayerCache)
    from generators.wan_animate2.attention_compile import enable_compiled_attention
    enable_compiled_attention()
    current_video_path=current_job_root/'driving.mp4'
    if current_request_record['driving_video_file']!='driving.mp4' or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record['driving_video_sha256']:
        raise ValueError('동작 영상 사본 해시 불일치')
    current_metrics_recorder.update_generation_stage('model-load')
    current_pipeline_model=ModularPipeline.from_pretrained(str(ANIMATE_MODEL_DIRECTORY),local_files_only=True)
    current_pipeline_model.load_components(dtype=torch.bfloat16,pretrained_model_name_or_path=str(ANIMATE_MODEL_DIRECTORY),revision=None,local_files_only=True)
    for current_component_name in ('transformer','text_encoder','image_encoder','vae','tokenizer','scheduler'):
        if getattr(current_pipeline_model,current_component_name,None) is None:
            raise RuntimeError(f'공식 모델 구성요소 로드 실패: {current_component_name}')
    # 체크포인트의 Transformers 4.57 UMT5는 encoder와 shared 임베딩을 공유한다.
    # Transformers 5의 분리 초기화가 원본 가중치를 대신하지 않도록 공식 setter로 연결한다.
    current_pipeline_model.text_encoder.set_input_embeddings(current_pipeline_model.text_encoder.shared)
    if current_pipeline_model.text_encoder.encoder.embed_tokens.weight is not current_pipeline_model.text_encoder.shared.weight:
        raise RuntimeError('UMT5 원본 공유 임베딩 연결 실패')
    current_pipeline_model.transformer.enable_group_offload(onload_device=torch.device('cuda'),offload_device=torch.device('cpu'),offload_type='leaf_level',use_stream=False)
    for current_component_model in (current_pipeline_model.text_encoder,current_pipeline_model.image_encoder,current_pipeline_model.vae):
        apply_group_offloading(current_component_model,onload_device=torch.device('cuda'),offload_device=torch.device('cpu'),offload_type='leaf_level',use_stream=False)
    current_source_frames,current_source_rate=load_video(str(current_video_path),return_fps=True)
    current_frame_count=current_request_record['frames']
    current_frame_indices=np.round(np.arange(current_frame_count)*current_source_rate/24).astype(int)
    if current_frame_indices[-1]>=len(current_source_frames):
        raise ValueError('24fps 기준 동작 영상 길이 부족')
    current_driving_frames=[current_source_frames[int(current_frame_index)] for current_frame_index in current_frame_indices]
    current_metrics_recorder.update_generation_stage('inference')
    current_scheduler_step=current_pipeline_model.scheduler.step
    current_completed_steps=[0]
    def record_scheduler_step(*current_step_arguments,**current_step_keywords):
        current_step_result=current_scheduler_step(*current_step_arguments,**current_step_keywords)
        current_completed_steps[0]+=1
        current_metrics_recorder.record_generation_step(current_completed_steps[0])
        return current_step_result
    current_pipeline_model.scheduler.step=record_scheduler_step
    current_output_videos=current_pipeline_model(image=load_image(str(current_job_root/current_request_record['references'][0])),driving_video=current_driving_frames,driving_video_fps=24,prompt=current_request_record['prompt'],height=480,width=832,segment_frame_length=current_frame_count,num_inference_steps=current_request_record['steps'],generator=torch.Generator(device='cuda').manual_seed(current_request_record['seed']),output='videos')
    current_frame_arrays=np.asarray(current_output_videos[0])
    if current_frame_arrays.dtype!=np.uint8:
        current_frame_arrays=np.rint(np.clip(current_frame_arrays,0,1)*255).astype(np.uint8)
    if len(current_frame_arrays)!=current_frame_count:
        raise ValueError(f'공식 출력 프레임 불일치: {len(current_frame_arrays)} / {current_frame_count}')
    current_metrics_recorder.update_generation_stage('postprocess')
    current_output_hashes=save_video_outputs(current_attempt_root,current_frame_arrays,24)
    return {'attempt':current_attempt_root.name,'frames':current_frame_count,'fps':24,'output_sha256':current_output_hashes,'model_id':ANIMATE_MODEL_IDENTIFIER,'model_revision':ANIMATE_MODEL_REVISION,'runtime_revision':ANIMATE_RUNTIME_REVISION,'prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'attention_execution':'inductor-fullgraph-isolated','reference_kv_offload':'cpu-lossless','cuda_allocator':'expandable_segments:True','quality_status':'사용자 검수 대기'}

if __name__=='__main__':
    run_reference_video_worker(ANIMATE_JOB_STORAGE,Path(__file__),validate_animate_assets,execute_animate_inference)
