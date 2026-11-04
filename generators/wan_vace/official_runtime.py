"""고정 GGUF와 공식 VideoX-Fun 파이프라인을 연결하는 CUDA 실행부."""
import sys
import os
import json
import hashlib
from pathlib import Path
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES, VACE_MODEL_REVISION, VACE_SOURCE_REVISION, VACE_MODEL_IDENTIFIER, VACE_ENCODER_REVISION
from generators.wan_vace.official_gguf import VACE_OFFICIAL_SOURCE_ROOT, load_official_gguf


def load_official_pipeline(current_metrics_recorder=None, current_flow_shift=12.0, current_attempt_root=None):
    os.environ['VIDEOX_OFFLOAD_VACE_LATENTS'] = '1'
    from generators.wan_vace.official_prepare import verify_official_runtime
    verify_official_runtime()
    import torch
    import yaml
    from accelerate import cpu_offload
    from safetensors.torch import load_file
    from transformers import AutoTokenizer
    from generators.wan_vace.sampling import build_vace_scheduler
    if not torch.cuda.is_available():
        raise RuntimeError('공식 VACE 실행은 CUDA가 필요합니다.')
    sys.path.insert(0,str(VACE_OFFICIAL_SOURCE_ROOT))
    from videox_fun.models import AutoencoderKLWan, WanT5EncoderModel
    from videox_fun.models import wan_transformer3d
    from generators.wan_vace.query_offload import install_query_result_offload
    install_query_result_offload(wan_transformer3d)
    from generators.wan_vace.cpu_offload import install_expert_block_offload, VACE_TRANSIENT_MODULE_NAMES
    from videox_fun.pipeline import Wan2_2VaceFunPipeline
    current_model_class = None
    if current_attempt_root is not None:
        from generators.wan_vace.activation_offload import load_input_offload_pipeline, load_branch_offload_model
        Wan2_2VaceFunPipeline = load_input_offload_pipeline(VACE_OFFICIAL_SOURCE_ROOT, current_attempt_root)
        current_model_class = load_branch_offload_model(VACE_OFFICIAL_SOURCE_ROOT, current_attempt_root)
    current_config_record = yaml.safe_load((VACE_OFFICIAL_SOURCE_ROOT/'config/wan2.2/wan_civitai_t2v.yaml').read_text())
    current_encoder_config = {current_field_name:current_field_value for current_field_name,current_field_value in current_config_record['text_encoder_kwargs'].items() if current_field_name not in ('text_encoder_subpath','tokenizer_subpath','text_length')}
    with torch.device('meta'):
        current_text_encoder = WanT5EncoderModel(**current_encoder_config)
    current_encoder_state = torch.load(VACE_WORKSPACE_ROOT/VACE_MODEL_FILES['encoder'][0],map_location='cpu',weights_only=True,mmap=True)
    current_text_encoder.load_state_dict(current_encoder_state,strict=True,assign=True)
    current_text_encoder.eval().requires_grad_(False)
    cpu_offload(current_text_encoder,execution_device=torch.device('cuda'))
    current_vae_model = AutoencoderKLWan()
    current_vae_state = load_file(str(VACE_WORKSPACE_ROOT/VACE_MODEL_FILES['vae'][0]))
    current_vae_model.load_state_dict({'model.'+current_tensor_name:current_tensor_value for current_tensor_name,current_tensor_value in current_vae_state.items()},strict=True)
    current_vae_model.to(device='cuda',dtype=torch.bfloat16).eval().requires_grad_(False)
    current_low_model = load_official_gguf('low', current_model_class)
    current_high_model = load_official_gguf('high', current_model_class)
    install_expert_block_offload(current_low_model)
    install_expert_block_offload(current_high_model)
    current_tokenizer_model = AutoTokenizer.from_pretrained(str(VACE_WORKSPACE_ROOT/'.model/wan22-vace/official-tokenizer'),local_files_only=True)
    current_pipeline_object = Wan2_2VaceFunPipeline(tokenizer=current_tokenizer_model,text_encoder=current_text_encoder,vae=current_vae_model,transformer=current_low_model,transformer_2=current_high_model,scheduler=build_vace_scheduler(current_flow_shift))
    current_inference_started = False
    def prepare_active_expert(current_active_model, current_input_values):
        nonlocal current_inference_started
        if not current_inference_started and current_metrics_recorder is not None:
            current_metrics_recorder.update_generation_stage('inference')
            current_inference_started = True
        current_inactive_model = current_high_model if current_active_model is current_low_model else current_low_model
        current_inactive_model.to('cpu')
        current_vae_model.to('cpu')
        for current_child_name,current_child_module in current_active_model.named_children():
            if current_child_name not in {'blocks', 'vace_blocks'} | VACE_TRANSIENT_MODULE_NAMES:
                current_child_module.to('cuda')
        torch.cuda.empty_cache()
    current_low_model.register_forward_pre_hook(prepare_active_expert)
    current_high_model.register_forward_pre_hook(prepare_active_expert)
    return current_pipeline_object


def execute_official_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    import torch
    import numpy as np
    from PIL import Image
    from generators.wan_vace.video_edit import decode_edit_video
    from generators.common.reference_video_worker import save_video_outputs
    from tools.review.common.generation_records import write_record_atomically
    write_record_atomically(current_attempt_root / 'model-selection.json', {
        'model_id': VACE_MODEL_IDENTIFIER, 'revision': VACE_MODEL_REVISION,
        'files': VACE_MODEL_FILES, 'quantization': 'Q4_K_M',
        'text_encoder_precision': 'BF16', 'text_encoder_quantized': False,
        'text_encoder_revision': VACE_ENCODER_REVISION,
        'source_revision': VACE_SOURCE_REVISION,
        'runtime': 'VideoX-Fun official + GGUF adapter',
        'adapter_source_sha256': {
            current_source_name: hashlib.sha256((Path(__file__).parent / current_source_name).read_bytes()).hexdigest()
            for current_source_name in ('official_runtime.py', 'official_gguf.py', 'cpu_offload.py', 'activation_offload.py', 'query_offload.py', 'memory_diagnostics.py', 'sampling.py', 'noise_experiment.py', 'attention_experiment.py')
        },
        'compute_device': 'cuda', 'offload_device': 'cpu',
        'non_block_module_offload': True,
        'encoded_input_cpu_offload': True,
        'rope_query_result_cpu_offload': True,
        'active_expert_block_offload': True, 'official_forward_unmodified': False, 'official_math_unmodified': 'attention_prefix_frames' not in current_request_record, 'branch_activation_cpu_offload': True, 'custom_math_patches': 'attention_prefix_frames' in current_request_record, 'vace_latent_offload': True, 'inactive_expert_offload': True, 'vae_inference_offload': True, 'temporal_vae_tiling': False,
    })
    current_metrics_recorder.update_generation_stage('load')
    current_pipeline_object = load_official_pipeline(current_metrics_recorder, current_request_record['flow_shift'], current_attempt_root)
    if 'attention_prefix_frames' in current_request_record:
        from videox_fun.models import wan_transformer3d
        from generators.wan_vace.attention_experiment import install_prefix_attention_isolation
        current_branch_scope = current_request_record.get("attention_branch_scope", "all")
        install_prefix_attention_isolation(wan_transformer3d, current_pipeline_object, current_branch_scope)
        write_record_atomically(current_attempt_root / 'attention-experiment.json', {
            'experimental_only': True, 'official_math_unmodified': False,
            'prefix_frames': 21, 'prefix_tokens': 10920, 'total_tokens': 18720,
            'branch_scope': current_branch_scope,
            'scope': '선택 분기 self-attention의 앞 7잠재 슬롯은 앞 7슬롯만 참조; 뒤쪽은 전체 참조; cross-attention 유지',
        })
    current_frame_count = current_request_record['frames']
    current_condition_inputs = {}
    if current_request_record['references']:
        current_reference_pixels = np.array(Image.open(current_job_root/current_request_record['references'][0]).convert('RGB'))
        current_reference_tensor = torch.from_numpy(current_reference_pixels.astype(np.float32)/255).permute(2,0,1)[None,:,None]
        if current_request_record['mode'] in ('reference','video_edit','pose'):
            current_condition_inputs['subject_ref_images'] = current_reference_tensor
        elif current_request_record['mode'] == 'first_frame':
            current_video_tensor = torch.zeros((1,3,current_frame_count,480,832))
            current_mask_tensor = torch.ones((1,1,current_frame_count,480,832))
            current_video_tensor[:,:,:1] = current_reference_tensor
            current_mask_tensor[:,:,:1] = 0
            current_condition_inputs.update(video=current_video_tensor,mask_video=current_mask_tensor)
    if current_request_record['mode'] == 'video_edit':
        for current_field_name,current_argument_name in [('edit_video','video'),('edit_mask','mask_video')]:
            current_file_name=current_field_name.replace('_','-')+'.mp4'
            current_input_path=current_job_root/current_file_name
            if current_request_record[current_field_name+'_file']!=current_file_name or hashlib.sha256(current_input_path.read_bytes()).hexdigest()!=current_request_record[current_field_name+'_sha256']:
                raise ValueError('편집 입력 해시 불일치')
            current_frame_arrays=decode_edit_video(current_input_path,current_frame_count)
            if current_field_name=='edit_mask':current_frame_arrays=(current_frame_arrays>=128).astype(np.uint8)*255
            current_condition_inputs[current_argument_name]=torch.from_numpy(current_frame_arrays.astype(np.float32)/255).permute(3,0,1,2)[None]
            if current_field_name=='edit_mask':current_condition_inputs[current_argument_name]=current_condition_inputs[current_argument_name][:,:1]
    if current_request_record['mode'] == 'pose':
        current_condition_inputs.update(build_pose_conditions(current_job_root, current_request_record))
    if 'noise_prefix_frames' in current_request_record:
        from generators.wan_vace.noise_experiment import build_prefix_noise_latents
        current_condition_inputs['latents'] = build_prefix_noise_latents(current_pipeline_object, current_request_record, current_attempt_root)
    def record_official_step(current_pipeline_value,current_step_index,current_time_value,current_callback_values):
        current_metrics_recorder.record_generation_step(current_step_index+1)
        if current_step_index + 1 == current_request_record['steps']:
            if 'attention_prefix_frames' in current_request_record:
                from safetensors.torch import save_file
                save_file({'latents': current_callback_values['latents'].detach().cpu().contiguous()}, str(current_attempt_root / 'final-latents.safetensors'))
            current_pipeline_value.transformer.to('cpu')
            current_pipeline_value.transformer_2.to('cpu')
            torch.cuda.empty_cache()
            current_pipeline_value.vae.to('cuda')
            current_metrics_recorder.update_generation_stage('decoding')
        return current_callback_values
    current_metrics_recorder.update_generation_stage('encoding')
    current_output_tensor=current_pipeline_object(prompt=current_request_record['prompt'],negative_prompt=current_request_record['negative_prompt'],height=480,width=832,num_frames=current_frame_count,num_inference_steps=current_request_record['steps'],guidance_scale=current_request_record['guidance_scale'],generator=torch.Generator(device='cuda').manual_seed(current_request_record['seed']),boundary=.875,shift=current_request_record['flow_shift'],vace_context_scale=current_request_record['reference_strength'],callback_on_step_end=record_official_step,**current_condition_inputs).videos
    current_sigma_values = current_pipeline_object.scheduler.sigmas.cpu()
    write_record_atomically(current_attempt_root / 'conditioning.json', {
        'mode': current_request_record['mode'],
        'sigmas': current_sigma_values.tolist(), 'boundary': .875,
        'switch_step': int((current_pipeline_object.scheduler.timesteps >= 875).sum()),
        'implementation': 'VideoX-Fun official + GGUF adapter',
        'source_revision': VACE_SOURCE_REVISION,
    })
    if not torch.isfinite(current_output_tensor).all():
        raise ValueError('공식 출력에 비유한 값이 있습니다.')
    current_frame_arrays=(current_output_tensor[0].permute(1,2,3,0).clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)
    if len(current_frame_arrays)!=current_frame_count:raise ValueError('공식 출력 프레임 수 불일치')
    current_metrics_recorder.update_generation_stage('saving')
    current_output_hashes=save_video_outputs(current_attempt_root,current_frame_arrays,16)
    if 'attention_prefix_frames' in current_request_record:
        from safetensors.torch import load_file
        current_comparison_latents = load_file(str(current_attempt_root / 'final-latents.safetensors'))['latents'][:, :, 1:7].to('cuda')
        current_metrics_recorder.update_generation_stage('decoding')
        current_comparison_video = current_pipeline_object.decode_latents(current_comparison_latents)
        current_comparison_frames = (current_comparison_video[0].transpose(1,2,3,0).clip(0,1)*255).round().astype(np.uint8)
        current_comparison_root = current_attempt_root / 'comparison-prefix'
        current_comparison_root.mkdir()
        save_video_outputs(current_comparison_root, current_comparison_frames, 16)
    return {'attempt':current_attempt_root.name,'mode':current_request_record['mode'],'prompt':current_request_record['prompt'],'frames':current_frame_count,'fps':16,'output_sha256':current_output_hashes,'runtime':'VideoX-Fun official + GGUF adapter','source_revision':VACE_SOURCE_REVISION,'model_revision':VACE_MODEL_REVISION,'prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'quality_status':'사용자 검수 대기'}


def build_pose_conditions(current_job_root, current_request_record):
    """공식 control+reference 예제의 전체 생성 마스크를 구성한다."""
    import torch
    import numpy as np
    from generators.wan_vace.video_edit import decode_edit_video
    current_pose_path = current_job_root/'pose-video.mp4'
    if current_request_record['pose_video_file'] != 'pose-video.mp4' or hashlib.sha256(current_pose_path.read_bytes()).hexdigest() != current_request_record['pose_video_sha256']:
        raise ValueError('포즈 영상 파일·해시 불일치')
    current_pose_arrays = decode_edit_video(current_pose_path, current_request_record['frames'])
    current_pose_tensor = torch.from_numpy(current_pose_arrays.astype(np.float32)/255).permute(3,0,1,2)[None]
    return {'control_video': current_pose_tensor, 'video': torch.zeros_like(current_pose_tensor),
            'mask_video': torch.ones_like(current_pose_tensor[:,:1])}
