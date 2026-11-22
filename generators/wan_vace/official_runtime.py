"""공식 BF16 VACE 모델을 GPU에 상주시켜 실행한다."""
import sys
import os
import json
import hashlib
from pathlib import Path
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES, VACE_MODEL_REVISION, VACE_SOURCE_REVISION, VACE_MODEL_IDENTIFIER, VACE_ENCODER_REVISION
from generators.wan_vace.official_prepare import VACE_OFFICIAL_INSTALL_ROOT as VACE_OFFICIAL_SOURCE_ROOT
from generators.wan_vace.official_full_precision import load_full_precision_expert


def build_blank_video_condition(torch, frame_count):
    """공식 예제의 이미지·영상 없는 경우와 같은 전체 마스크 입력."""
    return {'video':torch.zeros((1, 3, frame_count, 480, 832)),
            'mask_video':torch.ones((1, 1, frame_count, 480, 832)) * 255}


def load_official_pipeline(current_metrics_recorder=None, current_flow_shift=12.0, current_attempt_root=None):
    # 공식 구현은 문자열 "0"도 참으로 취급한다.
    os.environ.pop('VIDEOX_OFFLOAD_VACE_LATENTS', None)
    from generators.wan_vace.official_prepare import verify_official_runtime
    verify_official_runtime()
    import torch
    import yaml
    from safetensors.torch import load_file
    from transformers import AutoTokenizer
    from generators.wan_vace.sampling import build_vace_scheduler
    if not torch.version.hip or not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('BF16을 지원하는 AMD ROCm GPU가 필요합니다.')
    sys.path.insert(0, str(VACE_OFFICIAL_SOURCE_ROOT))
    from videox_fun.models import AutoencoderKLWan, WanT5EncoderModel, VaceWanTransformer3DModel
    from videox_fun.pipeline import Wan2_2VaceFunPipeline
    current_config_record = yaml.safe_load((VACE_OFFICIAL_SOURCE_ROOT / 'config/wan2.2/wan_civitai_t2v.yaml').read_text())
    current_encoder_config = {current_field_name: current_field_value for current_field_name, current_field_value in current_config_record['text_encoder_kwargs'].items() if current_field_name not in ('text_encoder_subpath', 'tokenizer_subpath', 'text_length')}
    with torch.device('meta'):
        current_text_encoder = WanT5EncoderModel(**current_encoder_config)
    current_encoder_state = torch.load(VACE_WORKSPACE_ROOT / VACE_MODEL_FILES['encoder'][0], map_location='cpu', weights_only=True, mmap=True)
    current_text_encoder.load_state_dict(current_encoder_state, strict=True, assign=True)
    current_text_encoder.to(device='cuda', dtype=torch.bfloat16).eval().requires_grad_(False)
    del current_encoder_state
    current_vae_model = AutoencoderKLWan()
    current_vae_state = load_file(str(VACE_WORKSPACE_ROOT / VACE_MODEL_FILES['vae'][0]))
    current_vae_model.load_state_dict({'model.' + current_tensor_name: current_tensor_value for current_tensor_name, current_tensor_value in current_vae_state.items()}, strict=True)
    current_vae_model.to(device='cuda', dtype=torch.bfloat16).eval().requires_grad_(False)
    del current_vae_state
    current_low_model = load_full_precision_expert('low', VaceWanTransformer3DModel)
    current_high_model = load_full_precision_expert('high', VaceWanTransformer3DModel)
    current_tokenizer_model = AutoTokenizer.from_pretrained(str(VACE_WORKSPACE_ROOT / '.model/wan22-vace/official-tokenizer'), local_files_only=True)
    current_pipeline_object = Wan2_2VaceFunPipeline(tokenizer=current_tokenizer_model, text_encoder=current_text_encoder, vae=current_vae_model, transformer=current_low_model, transformer_2=current_high_model, scheduler=build_vace_scheduler(current_flow_shift))
    current_inference_started = False
    def record_inference_start(current_active_model, current_input_values):
        nonlocal current_inference_started
        if not current_inference_started and current_metrics_recorder is not None:
            current_metrics_recorder.update_generation_stage('inference')
            current_inference_started = True
    current_low_model.register_forward_pre_hook(record_inference_start)
    current_high_model.register_forward_pre_hook(record_inference_start)
    return current_pipeline_object


def execute_official_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    import torch
    import torch.nn.functional as torch_functional_module
    import numpy as np
    from PIL import Image
    from generators.wan_vace.video_edit import decode_edit_video
    from generators.common.reference_video_worker import save_video_outputs
    from generators.wan_fun.attention_optimization import install_fun_attention_optimization
    from generators.wan_fun.attention_profile import install_fun_attention_profile
    from workflow.common.generation_records import write_record_atomically
    current_contiguous_enabled = install_fun_attention_optimization(torch, torch_functional_module)
    if os.environ.get('SLIME_VACE_ATTENTION_PROFILE', '1') == '1':
        install_fun_attention_profile(current_attempt_root, torch_functional_module, current_call_limit=2)
    write_record_atomically(current_attempt_root / 'model-selection.json', {
        'model_id': VACE_MODEL_IDENTIFIER, 'revision': VACE_MODEL_REVISION,
        'files': VACE_MODEL_FILES, 'quantization': None, 'precision': 'BF16',
        'pytorch_version': torch.__version__, 'rocm_version': torch.version.hip,
        'gpu_name': torch.cuda.get_device_name(0), 'allocator_backend': torch.cuda.memory.get_allocator_backend(),
        'allocator_configuration': os.environ.get('PYTORCH_ALLOC_CONF'),
        'text_encoder_revision': VACE_ENCODER_REVISION, 'source_revision': VACE_SOURCE_REVISION,
        'runtime': 'VideoX-Fun official BF16', 'gpu_backend': 'rocm',
        'gpu_runtime_version': torch.version.hip,
        'gpu_device_name': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        'model_profile': 'official-bf16-resident-v1', 'offload_device': None,
        'active_expert_block_offload': False, 'inactive_expert_offload': False,
        'encoded_input_cpu_offload': False, 'branch_activation_cpu_offload': False,
        'rope_query_result_cpu_offload': False, 'vace_latent_offload': False,
        'vae_inference_offload': False,
        'contiguous_long_attention': current_contiguous_enabled,
        'attention_profile_enabled': os.environ.get('SLIME_VACE_ATTENTION_PROFILE', '1') == '1',
        'vae_sdpa_diagnostic_enabled': os.environ.get('SLIME_VACE_VAE_SDPA_DIAGNOSTIC') == '1',
        'custom_math_patches': 'attention_prefix_frames' in current_request_record,
        'adapter_source_sha256': {current_source_name: hashlib.sha256((Path(__file__).parent / current_source_name).read_bytes()).hexdigest() for current_source_name in ('official_runtime.py', 'official_full_precision.py', 'sampling.py', 'noise_experiment.py', 'attention_experiment.py', 'numerical_guard.py', 'vae_numerical_guard.py', 'vae_attention_diagnostics.py')},
    })
    current_metrics_recorder.update_generation_stage('load')
    current_pipeline_object = load_official_pipeline(current_metrics_recorder, current_request_record['flow_shift'], current_attempt_root)
    from videox_fun.models import wan_transformer3d
    from generators.wan_vace.vae_numerical_guard import record_vace_tensor_failure
    from generators.wan_vace.numerical_guard import install_vace_attention_guard
    current_guard_state = install_vace_attention_guard(wan_transformer3d, current_attempt_root, torch)
    def check_vace_expert_output(current_expert_module, current_expert_inputs, current_expert_output):
        current_checked_output = current_expert_output[0] if isinstance(current_expert_output, (tuple, list)) else current_expert_output
        if not isinstance(current_checked_output, torch.Tensor) or not torch.isfinite(current_checked_output).all().item():
            record_vace_tensor_failure(current_attempt_root, 'expert-output', torch, {'output': current_checked_output} if isinstance(current_checked_output, torch.Tensor) else {}, {'step': current_guard_state['step']})
            raise ValueError(f"VACE 전문가 출력에 NaN 또는 무한대가 있습니다: 단계 {current_guard_state['step']}")
    def mark_vace_expert_step(current_expert_module, current_expert_inputs):
        current_guard_state['step'] += 1
    for current_expert_model in (current_pipeline_object.transformer, current_pipeline_object.transformer_2):
        if current_expert_model is not None:
            current_expert_model.register_forward_pre_hook(mark_vace_expert_step)
            current_expert_model.register_forward_hook(check_vace_expert_output)
    if 'attention_prefix_frames' in current_request_record:
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
    current_condition_inputs = build_blank_video_condition(torch, current_frame_count) if current_request_record['mode'] in ('text', 'reference') else {}
    if current_request_record['references']:
        current_reference_pixels = np.array(Image.open(current_job_root/current_request_record['references'][0]).convert('RGB'))
        current_reference_tensor = torch.from_numpy(current_reference_pixels.astype(np.float32)/255).permute(2,0,1)[None,:,None]
        if current_request_record['mode'] in ('reference','video_edit','video_condition','pose'):
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
    if current_request_record['mode'] == 'video_condition':
        from generators.wan_vace.video_edit import build_video_condition_inputs
        current_condition_inputs.update(build_video_condition_inputs(current_job_root, current_request_record))
    if current_request_record['mode'] == 'pose':
        current_condition_inputs.update(build_pose_conditions(current_job_root, current_request_record))
    if 'noise_prefix_frames' in current_request_record:
        from generators.wan_vace.noise_experiment import build_prefix_noise_latents
        current_condition_inputs['latents'] = build_prefix_noise_latents(current_pipeline_object, current_request_record, current_attempt_root)
    def record_official_step(current_pipeline_value,current_step_index,current_time_value,current_callback_values):
        if not isinstance(current_callback_values.get('latents'), torch.Tensor) or not torch.isfinite(current_callback_values['latents']).all().item():
            current_failed_latents = current_callback_values.get('latents')
            record_vace_tensor_failure(current_attempt_root, 'scheduler-latents', torch, {'latents': current_failed_latents} if isinstance(current_failed_latents, torch.Tensor) else {}, {'step': current_step_index + 1})
            raise ValueError(f'VACE 추론 {current_step_index + 1}단계 잠재값에 NaN 또는 무한대가 있습니다.')
        current_metrics_recorder.record_generation_step(current_step_index+1)
        if current_step_index + 1 == current_request_record['steps']:
            if 'attention_prefix_frames' in current_request_record:
                from safetensors.torch import save_file
                save_file({'latents': current_callback_values['latents'].detach().cpu().contiguous()}, str(current_attempt_root / 'final-latents.safetensors'))
            current_metrics_recorder.update_generation_stage('decoding')
        return current_callback_values
    current_metrics_recorder.update_generation_stage('encoding')
    from generators.wan_vace.vae_numerical_guard import guard_vace_vae_boundaries
    with guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, torch, os.environ.get('SLIME_VACE_VAE_SDPA_DIAGNOSTIC') == '1') as current_vae_check_counts:
        current_output_tensor=current_pipeline_object(prompt=current_request_record['prompt'],negative_prompt=current_request_record['negative_prompt'],height=480,width=832,num_frames=current_frame_count,num_inference_steps=current_request_record['steps'],guidance_scale=current_request_record['guidance_scale'],generator=torch.Generator(device='cuda').manual_seed(current_request_record['seed']),boundary=.875,shift=current_request_record['flow_shift'],vace_context_scale=current_request_record['reference_strength'],callback_on_step_end=record_official_step,**current_condition_inputs).videos
    current_sigma_values = current_pipeline_object.scheduler.sigmas.cpu()
    write_record_atomically(current_attempt_root / 'conditioning.json', {
        'mode': current_request_record['mode'],
        'sigmas': current_sigma_values.tolist(), 'boundary': .875,
        'switch_step': int((current_pipeline_object.scheduler.timesteps >= 875).sum()),
        'implementation': 'VideoX-Fun official BF16',
        'source_revision': VACE_SOURCE_REVISION,
    })
    from generators.wan_vace.vae_numerical_guard import check_vace_boundary_values
    check_vace_boundary_values(current_output_tensor, 'final-output', current_attempt_root, torch)
    write_record_atomically(current_attempt_root / 'numerical-validation.json', {'attention_calls': current_guard_state['attention_calls'], 'expert_calls': current_guard_state['step'], 'latent_steps_checked': current_request_record['steps'], 'attention_qkv_and_output_checked': True, 'expert_output_checked': True, 'vae_boundary_checks': current_vae_check_counts})
    current_frame_arrays=(current_output_tensor[0].permute(1,2,3,0).clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)
    if len(current_frame_arrays)!=current_frame_count:raise ValueError('공식 출력 프레임 수 불일치')
    current_metrics_recorder.update_generation_stage('saving')
    current_output_hashes=save_video_outputs(current_attempt_root,current_frame_arrays,16)
    if 'attention_prefix_frames' in current_request_record:
        from safetensors.torch import load_file
        current_comparison_latents = load_file(str(current_attempt_root / 'final-latents.safetensors'))['latents'][:, :, 1:7].to('cuda')
        current_metrics_recorder.update_generation_stage('decoding')
        with guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, torch):
            current_comparison_video = current_pipeline_object.decode_latents(current_comparison_latents)
        current_comparison_frames = (current_comparison_video[0].transpose(1,2,3,0).clip(0,1)*255).round().astype(np.uint8)
        current_comparison_root = current_attempt_root / 'comparison-prefix'
        current_comparison_root.mkdir()
        save_video_outputs(current_comparison_root, current_comparison_frames, 16)
    return {'attempt':current_attempt_root.name,'mode':current_request_record['mode'],'prompt':current_request_record['prompt'],'frames':current_frame_count,'fps':16,'output_sha256':current_output_hashes,'runtime':'VideoX-Fun official BF16','source_revision':VACE_SOURCE_REVISION,'model_revision':VACE_MODEL_REVISION,'prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'quality_status':'사용자 검수 대기'}


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
