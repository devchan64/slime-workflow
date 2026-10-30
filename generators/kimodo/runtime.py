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
    current_prepared_text = current_llm_encoder.prepare_for_tokenization(current_llm_encoder._convert_to_str('',current_prompt_text))
    if len(current_tokenizer_value(current_prompt_text,add_special_tokens=False)['input_ids']) > 400:
        raise ValueError('인코더 400토큰 한도 초과: 자동 잘림 없이 중단합니다.')
    write_record_atomically(current_attempt_root/'prompt.json',{'prompt':current_prompt_text,'word_count':len(current_prompt_text.split()),'sha256':hashlib.sha256(current_prompt_text.encode()).hexdigest(),'encoder_text':current_prepared_text,'encoder_word_count':len(current_prepared_text.split()),'encoder_sha256':hashlib.sha256(current_prepared_text.encode()).hexdigest()})
    # 공개 LLM2Vec의 토큰화·평균 풀링을 유지하고 전체 .to() 재배치를 피한다.
    current_token_features = current_llm_encoder.tokenize([current_prepared_text])
    current_token_features = {current_field_name:current_tensor_value.to('cuda:0') for current_field_name,current_tensor_value in current_token_features.items()}
    with torch.inference_mode():
        current_embedding_tensor = current_llm_encoder(current_token_features).float().detach().cpu()
    if current_embedding_tensor.shape != (1,4096) or not torch.isfinite(current_embedding_tensor).all():
        raise ValueError('텍스트 임베딩 형식·유한값 오류')
    del current_token_features,current_llm_encoder,current_adapted_encoder,current_base_encoder,current_tokenizer_value
    gc.collect()
    torch.cuda.empty_cache()
    return current_embedding_tensor[:,None,:]


def execute_kimodo_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    import torch
    import numpy as np
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    from kimodo.exports.motion_io import save_kimodo_npz
    from generators.kimodo.preview import render_kimodo_frames
    os.environ['HF_HUB_OFFLINE'] = '1'
    current_final_prompt = normalize_kimodo_prompt(current_request_record['prompt'])
    current_metrics_recorder.update_generation_stage('encoding')
    current_embedding_tensor = encode_kimodo_prompt(current_final_prompt,current_attempt_root)
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
        if current_prompt_values != [current_final_prompt]:
            raise ValueError('인코딩 프롬프트와 모션 요청 불일치')
        return current_embedding_tensor.to('cuda:0'),[1]
    current_motion_model.text_encoder = provide_cached_embedding
    torch.manual_seed(current_request_record['seed'])
    torch.cuda.manual_seed_all(current_request_record['seed'])
    current_metrics_recorder.update_generation_stage('inference')
    def record_sampling_progress(current_sampling_indices):
        for current_step_index,current_sampling_index in enumerate(current_sampling_indices,1):
            yield current_sampling_index
            current_metrics_recorder.record_generation_step(current_step_index)
    current_motion_output = current_motion_model(prompts=current_final_prompt,num_frames=current_request_record['frames'],num_denoising_steps=current_request_record['steps'],cfg_weight=[current_request_record['guidance_scale'],2.0],cfg_type='separated',first_heading_angle=math.radians(current_request_record['heading_degrees']),post_processing=current_request_record['post_processing'],return_numpy=True,progress_bar=record_sampling_progress)
    current_joint_positions = current_motion_output['posed_joints']
    if current_joint_positions.shape != (current_request_record['frames'],77,3) or not np.isfinite(current_joint_positions).all():
        raise ValueError(f'SOMA 출력 크기·유한값 오류: {current_joint_positions.shape}')
    for current_field_name,current_field_value in current_motion_output.items():
        if isinstance(current_field_value,np.ndarray) and np.issubdtype(current_field_value.dtype,np.number) and not np.isfinite(current_field_value).all():
            raise ValueError(f'출력 비유한 값: {current_field_name}')
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
    from generators.kimodo.comparison import export_pose_comparison
    export_pose_comparison(current_attempt_root,current_request_record.get('directions',['front_left']))
    with zipfile.ZipFile(current_attempt_root/'frames.zip','a') as current_output_archive:
        if current_request_record.get('remove_horizontal_motion',False):
            current_output_archive.write(current_attempt_root/'motion-in-place.npz','motion-in-place.npz')
        for current_artifact_name in ('motion.npz','skeleton.json','prompt.json','text-embedding.npy'):
            current_output_archive.write(current_attempt_root/current_artifact_name,current_artifact_name)
        for current_artifact_name in ('soma-pose.json','comparison.mp4','joint-preview.mp4'):
            current_output_archive.write(current_attempt_root/current_artifact_name,current_artifact_name)
    current_result_record = {'attempt':current_attempt_root.name,'frames':current_request_record['frames'],'fps':30,'width':640,'height':480,'frame_sha256':current_frame_hashes,'model':'nvidia/Kimodo-SOMA-RP-v1.2','encoder':'matbee/kimodo-llm2vec-nf4','encoder_quantization':'NF4','motion_precision':'FP32','source_revision':KIMODO_ASSET_CONFIG['source_revision'],'model_revisions':{current_asset_record['role']:current_asset_record['revision'] for current_asset_record in KIMODO_ASSET_CONFIG['models']},'skeleton':'somaskel77','compute_device':'cuda','post_processing':current_request_record['post_processing'],'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20}
    current_result_record.update(remove_horizontal_motion=current_request_record.get('remove_horizontal_motion',False),directions=current_request_record.get('directions',['front_left']),pose_source='soma',anny_enabled=False)
    return current_result_record
