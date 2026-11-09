"""사전 NF4 인코더와 원본 FP32 모션 모델을 CUDA에서 순차 실행한다."""
import gc
import hashlib
import json
import math
import os
import shutil
import zipfile
from generators.kimodo.contracts import KIMODO_MODEL_ROOT, KIMODO_ASSET_CONFIG, normalize_kimodo_prompt
from generators.common.reference_video_worker import save_video_outputs
from tools.review.common.generation_records import write_record_atomically


def encode_kimodo_prompt(current_prompt_text, current_attempt_root):
    import torch
    from transformers import AutoTokenizer
    from peft import PeftModel
    from kimodo.model.llm2vec.models.bidirectional_llama import LlamaBiModel
    from kimodo.model.llm2vec.llm2vec import LLM2Vec
    current_encoder_root = KIMODO_MODEL_ROOT/'encoder'
    current_base_encoder = LlamaBiModel.from_pretrained(str(current_encoder_root),local_files_only=True,device_map={'':'cuda:0'},dtype=torch.bfloat16,attn_implementation='sdpa')
    if not getattr(current_base_encoder,'is_loaded_in_4bit',False):
        raise RuntimeError('NF4 가중치가 4비트로 로드되지 않았습니다.')
    current_adapted_encoder = PeftModel.from_pretrained(current_base_encoder,str(current_encoder_root/'supervised_adapter'),local_files_only=True).eval()
    if any(current_parameter_value.device.type != 'cuda' for current_parameter_value in current_adapted_encoder.parameters()):
        raise RuntimeError('인코더 연산 가중치가 CUDA 밖에 있습니다.')
    current_adapted_encoder.config._name_or_path = 'meta-llama/Meta-Llama-3-8B-Instruct'
    current_tokenizer_value = AutoTokenizer.from_pretrained(str(current_encoder_root),local_files_only=True)
    current_tokenizer_value.pad_token = current_tokenizer_value.eos_token
    current_tokenizer_value.padding_side = 'left'
    current_llm_encoder = LLM2Vec(current_adapted_encoder,current_tokenizer_value,pooling_mode='mean',max_length=512,doc_max_length=400,skip_instruction=True)
    current_prompt_values = [current_prompt_text] if isinstance(current_prompt_text,str) else current_prompt_text
    current_embedding_values = []
    current_prompt_records = []
    for current_segment_prompt in current_prompt_values:
        current_prepared_text = current_llm_encoder.prepare_for_tokenization(current_llm_encoder._convert_to_str('',current_segment_prompt))
        if len(current_tokenizer_value(current_segment_prompt,add_special_tokens=False)['input_ids']) > 400:
            raise ValueError('인코더 400토큰 한도 초과: 자동 잘림 없이 중단합니다.')
        current_prompt_records.append({'prompt':current_segment_prompt,'word_count':len(current_segment_prompt.split()),'sha256':hashlib.sha256(current_segment_prompt.encode()).hexdigest(),'encoder_text':current_prepared_text,'encoder_word_count':len(current_prepared_text.split()),'encoder_sha256':hashlib.sha256(current_prepared_text.encode()).hexdigest()})
        current_token_features = current_llm_encoder.tokenize([current_prepared_text])
        current_token_features = {current_field_name:current_tensor_value.to('cuda:0') for current_field_name,current_tensor_value in current_token_features.items()}
        with torch.inference_mode():
            current_segment_embedding = current_llm_encoder(current_token_features).float().detach().cpu()
        if current_segment_embedding.shape != (1,4096) or not torch.isfinite(current_segment_embedding).all():
            raise ValueError('텍스트 임베딩 형식·유한값 오류')
        current_embedding_values.append(current_segment_embedding)
    current_embedding_tensor = torch.cat(current_embedding_values,dim=0)
    write_record_atomically(current_attempt_root/'prompt.json',current_prompt_records[0] if len(current_prompt_records)==1 else {'segments':current_prompt_records,'word_count':sum(current_prompt_record['word_count'] for current_prompt_record in current_prompt_records)})
    del current_token_features,current_llm_encoder,current_adapted_encoder,current_base_encoder,current_tokenizer_value
    gc.collect()
    torch.cuda.empty_cache()
    return current_embedding_tensor[:,None,:]


def execute_kimodo_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    if current_request_record.get('pose_constraints'):
        raise ValueError('전신 키프레임 제약 기능은 폐기되었습니다. 입력값을 불러와 제약 없이 새로 생성하세요.')
    import torch
    import subprocess
    from pathlib import Path
    import numpy as np
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    from kimodo.exports.motion_io import save_kimodo_npz
    from generators.kimodo.preview import render_kimodo_frames
    os.environ['HF_HUB_OFFLINE'] = '1'
    if current_request_record.get('references'):
        import subprocess
        from pathlib import Path
        current_workspace_root=Path(__file__).resolve().parents[2]
        current_metrics_recorder.update_generation_stage('reference-proportions')
        subprocess.run([str(current_workspace_root/'.venv/bin/python'),str(Path(__file__).with_name('reference_extraction.py')),str(current_job_root),str(current_attempt_root)],env={**os.environ,'PYTHONPATH':str(current_workspace_root/'.local/wan22-animate/preprocess-deps')},check=True)
    from generators.kimodo.motion_sequence import resolve_motion_segments
    current_segment_prompts,current_segment_frames = resolve_motion_segments(current_request_record['prompt'],current_request_record['frames'],current_request_record.get('segment_frames'))
    current_final_prompts = [normalize_kimodo_prompt(current_segment_prompt) for current_segment_prompt in current_segment_prompts]
    current_sequence_enabled = len(current_final_prompts)>1
    current_final_prompt = current_final_prompts[0]
    current_metrics_recorder.update_generation_stage('encoding')
    current_embedding_tensor = encode_kimodo_prompt(current_final_prompts,current_attempt_root)
    np.save(current_attempt_root/'text-embedding.npy',current_embedding_tensor.numpy())
    current_metrics_recorder.update_generation_stage('load')
    current_model_config = OmegaConf.load(KIMODO_MODEL_ROOT/'motion/config.yaml')
    current_model_config.checkpoint_dir = str(KIMODO_MODEL_ROOT/'motion')
    current_model_config = OmegaConf.to_container(current_model_config,resolve=True)
    current_model_config.pop('checkpoint_dir')
    current_model_config['text_encoder'] = None
    current_motion_model = instantiate_from_dict(current_model_config,overrides={'device':'cuda:0'}).eval()
    if any(current_parameter_value.device.type != 'cuda' for current_parameter_value in current_motion_model.parameters()):
        raise RuntimeError('모션 모델 CUDA 배치 오류')
    def provide_cached_embedding(current_prompt_values):
        if any(current_prompt_value not in current_final_prompts for current_prompt_value in current_prompt_values):
            raise ValueError('인코딩 프롬프트와 모션 요청 불일치')
        return current_embedding_tensor[[current_final_prompts.index(current_prompt_value) for current_prompt_value in current_prompt_values]].to('cuda:0'),[1]*len(current_prompt_values)
    current_motion_model.text_encoder = provide_cached_embedding
    torch.manual_seed(current_request_record['seed'])
    torch.cuda.manual_seed_all(current_request_record['seed'])
    current_metrics_recorder.update_generation_stage('inference')
    def record_sampling_progress(current_sampling_indices):
        for current_step_index,current_sampling_index in enumerate(current_sampling_indices,1):
            yield current_sampling_index
            current_metrics_recorder.record_generation_step(current_step_index)
    if current_sequence_enabled:
        # 공식 순차 경로는 progress_bar를 내부 _generate에 전달하지 않아 관측만 연결한다.
        current_original_generate = current_motion_model._generate
        current_completed_steps = [0]
        def record_sequence_progress(current_sampling_indices):
            for current_sampling_index in current_sampling_indices:
                yield current_sampling_index
                current_completed_steps[0] += 1
                current_metrics_recorder.record_generation_step(current_completed_steps[0])
        def generate_with_progress(*current_call_arguments,**current_call_keywords):
            current_call_keywords['progress_bar'] = record_sequence_progress
            return current_original_generate(*current_call_arguments,**current_call_keywords)
        current_motion_model._generate = generate_with_progress
    from generators.kimodo.pose_library import prepare_soma_endpoint_constraints
    current_endpoint_constraints = prepare_soma_endpoint_constraints(current_request_record,current_attempt_root,current_motion_model.skeleton)
    if current_request_record.get('keyframes'):
        from kimodo.constraints import load_constraints_lst
        from tools.review.domains.kimodo.keyframe_storage import build_kimodo_keyframe_constraints
        current_constraint_records = build_kimodo_keyframe_constraints(current_job_root,current_request_record)
        write_record_atomically(current_attempt_root/'keyframe-constraints.json',current_constraint_records)
        current_endpoint_constraints = load_constraints_lst(current_constraint_records,current_motion_model.skeleton,device='cuda')
    from contextlib import nullcontext
    from generators.kimodo.sequence_constraints import support_empty_sequence_constraints
    if current_sequence_enabled and current_request_record.get('keyframes'):
        from kimodo.constraints import FullBodyConstraintSet
        current_constraint_context = support_empty_sequence_constraints(FullBodyConstraintSet)
    else:
        current_constraint_context = nullcontext()
    with current_constraint_context:
        current_motion_output = current_motion_model(constraint_lst=current_endpoint_constraints,prompts=current_final_prompts if current_sequence_enabled else current_final_prompt,num_frames=current_segment_frames if current_sequence_enabled else current_request_record['frames'],multi_prompt=current_sequence_enabled,num_samples=1,num_denoising_steps=current_request_record['steps'],cfg_weight=[current_request_record['guidance_scale'],2.0],cfg_type='separated',first_heading_angle=math.radians(current_request_record['heading_degrees']),post_processing=current_request_record['post_processing'],return_numpy=True,progress_bar=record_sampling_progress)
    # 공식 후처리까지 배치 차원을 유지하고, 저장 직전에 단일 샘플을 꺼낸다.
    if any(not isinstance(current_field_value,np.ndarray) or current_field_value.ndim < 1 or current_field_value.shape[0] != 1 for current_field_value in current_motion_output.values()):
        raise ValueError('Kimodo 단일 샘플 배치 출력 계약 오류')
    current_motion_output = {current_field_name:current_field_value[0] for current_field_name,current_field_value in current_motion_output.items()}
    current_joint_positions = current_motion_output['posed_joints']
    if current_joint_positions.shape != (current_request_record['frames'],77,3) or not np.isfinite(current_joint_positions).all():
        raise ValueError(f'SOMA 출력 크기·유한값 오류: {current_joint_positions.shape}')
    for current_field_name,current_field_value in current_motion_output.items():
        if isinstance(current_field_value,np.ndarray) and np.issubdtype(current_field_value.dtype,np.number) and not np.isfinite(current_field_value).all():
            raise ValueError(f'출력 비유한 값: {current_field_name}')
    if current_request_record.get('endpoint_pose_id'):
        current_endpoint_distances = np.linalg.norm(current_joint_positions[-1]-current_joint_positions[0],axis=-1)
        write_record_atomically(current_attempt_root/'endpoint-measurement.json',{'pose_id':current_request_record['endpoint_pose_id'],'unit':'meters','mean_joint_distance':float(current_endpoint_distances.mean()),'maximum_joint_distance':float(current_endpoint_distances.max()),'scope':'생성 SOMA 원본 첫·마지막 프레임 · 렌더 및 포즈 출력 전'})
    if current_request_record.get('keyframes'):
        from tools.review.domains.kimodo.keyframe_storage import load_kimodo_keyframe_snapshot
        current_keyframe_placements = current_request_record['keyframes']
        _,current_first_arrays,_ = load_kimodo_keyframe_snapshot(current_job_root/'keyframes',current_keyframe_placements[0]['id'])
        current_origin_position = current_first_arrays['smooth_root_pos'][0,[0,2]]
        current_measurement_records = []
        for current_placement_record in current_keyframe_placements:
            _,current_target_arrays,_ = load_kimodo_keyframe_snapshot(current_job_root/'keyframes',current_placement_record['id'])
            current_target_positions = current_target_arrays['posed_joints'][0].copy()
            current_target_positions[:,[0,2]] -= current_origin_position
            current_joint_distances = np.linalg.norm(current_joint_positions[current_placement_record['frame']-1]-current_target_positions,axis=-1)
            current_measurement_records.append({'id':current_placement_record['id'],'frame':current_placement_record['frame'],'mean_joint_distance':float(current_joint_distances.mean()),'maximum_joint_distance':float(current_joint_distances.max())})
        write_record_atomically(current_attempt_root/'keyframe-measurement.json',{'unit':'meters','scope':'SOMA 77관절 · 원본 30fps · 첫 키프레임의 평활 루트 원점 기준 · 렌더·수평 이동 보정 전','placements':current_measurement_records})
    current_joint_parents = current_motion_model.output_skeleton.joint_parents.cpu().tolist()
    current_joint_names = current_motion_model.output_skeleton.bone_order_names
    current_metrics_recorder.update_generation_stage('saving')
    save_kimodo_npz(str(current_attempt_root/'motion.npz'),current_motion_output)
    write_record_atomically(current_attempt_root/'skeleton.json',{'skeleton':'somaskel77','fps':30,'parents':current_joint_parents,'joint_names':current_joint_names})
    if current_request_record.get('remove_horizontal_motion',False):
        from generators.kimodo.motion_processing import remove_horizontal_translation
        current_corrected_output = remove_horizontal_translation(current_motion_output,current_joint_names)
        save_kimodo_npz(str(current_attempt_root/'motion-in-place.npz'),current_corrected_output)
        current_joint_positions = current_corrected_output['posed_joints']
    current_frame_arrays = render_kimodo_frames(current_joint_positions,current_joint_parents)
    current_frame_hashes = save_video_outputs(current_attempt_root,current_frame_arrays,30)
    shutil.copy2(current_attempt_root/'preview.mp4',current_attempt_root/'joint-preview.mp4')
    # 추론 모델 해제 후 원본 관절을 투영한다.
    del current_motion_model,current_embedding_tensor
    gc.collect()
    torch.cuda.empty_cache()
    from generators.kimodo.soma_render import render_soma_motion
    from generators.kimodo.contracts import KIMODO_DIRECTION_RECORDS
    current_metrics_recorder.update_generation_stage('soma-render')
    current_soma_videos = render_soma_motion(current_attempt_root, {current_direction_name: KIMODO_DIRECTION_RECORDS[current_direction_name]['angle'] for current_direction_name in current_request_record.get('directions', ['front_left'])},current_elevation_angle=current_request_record.get('camera_elevation_degrees',0))
    from generators.kimodo.pose_outputs import export_kimodo_pose_outputs
    current_direct_record,current_dwpose_record,current_quality_warnings = export_kimodo_pose_outputs(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder)
    from generators.kimodo.comparison import export_pose_comparison
    export_pose_comparison(current_attempt_root,current_request_record.get('directions',['front_left']),current_request_record.get('openpose_scale_percent',100.0))
    with zipfile.ZipFile(current_attempt_root/'frames.zip','a') as current_output_archive:
        for current_pose_path in [current_attempt_root/'dwpose-export.json',current_attempt_root/'soma-direct-pose.json',*current_attempt_root.glob('soma-direct-*.mp4'),*current_attempt_root.glob('dwpose-*.mp4'),*current_attempt_root.glob('dwpose-*/*.json')]:
            current_output_archive.write(current_pose_path,str(current_pose_path.relative_to(current_attempt_root)))
        for current_soma_filename in [*current_soma_videos.values(), 'soma-render.json']:
            current_output_archive.write(current_attempt_root/current_soma_filename, current_soma_filename)
        if current_request_record.get('remove_horizontal_motion',False):
            current_output_archive.write(current_attempt_root/'motion-in-place.npz','motion-in-place.npz')
        if (current_attempt_root/'reference-proportions.json').is_file():
            for current_reference_artifact in [current_attempt_root/'reference-proportions.json',*sorted(current_attempt_root.glob('reference-pose-*.png'))]:
                current_output_archive.write(current_reference_artifact,current_reference_artifact.name)
        for current_artifact_name in ('motion.npz','skeleton.json','prompt.json','text-embedding.npy'):
            current_output_archive.write(current_attempt_root/current_artifact_name,current_artifact_name)
        if current_request_record.get('keyframes'):
            for current_artifact_name in ('keyframe-constraints.json','keyframe-measurement.json'):
                current_output_archive.write(current_attempt_root/current_artifact_name,current_artifact_name)
        for current_artifact_name in ('soma-pose.json','comparison.mp4','joint-preview.mp4'):
            current_output_archive.write(current_attempt_root/current_artifact_name,current_artifact_name)
    current_result_record = {'attempt':current_attempt_root.name,'frames':current_request_record['frames'],'fps':30,'width':640,'height':480,'frame_sha256':current_frame_hashes,'model':'nvidia/Kimodo-SOMA-RP-v1.2','encoder':'matbee/kimodo-llm2vec-nf4','encoder_quantization':'NF4','motion_precision':'FP32','source_revision':KIMODO_ASSET_CONFIG['source_revision'],'model_revisions':{current_asset_record['role']:current_asset_record['revision'] for current_asset_record in KIMODO_ASSET_CONFIG['models']},'skeleton':'somaskel77','compute_device':'cuda','post_processing':current_request_record['post_processing'],'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20}
    current_result_record.update(openpose_scale_basis='legacy-fit',openpose_scale_percent=current_request_record.get('openpose_scale_percent',100.0),remove_horizontal_motion=current_request_record.get('remove_horizontal_motion',False),directions=current_request_record.get('directions',['front_left']),pose_source='soma',anny_enabled=False,reference_proportions=bool(current_request_record.get('references')))
    current_result_record['camera_elevation_degrees'] = current_request_record.get('camera_elevation_degrees',0)
    current_result_record['direct_pose_videos'] = {current_direction_name:current_direction_record['video'] for current_direction_name,current_direction_record in current_direct_record['directions'].items()}
    current_result_record['quality_warnings'] = current_quality_warnings
    current_result_record['dwpose_status'] = current_dwpose_record.get('status','completed')
    current_result_record['dwpose_videos'] = current_dwpose_record['videos']
    current_result_record['soma_render_videos'] = current_soma_videos
    return current_result_record
