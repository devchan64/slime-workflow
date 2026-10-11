"""검증된 Phantom S2V 추론. 가중치 CPU 오프로드, 모델 연산 CUDA."""
from pathlib import Path
import sys,json
WORKFLOW_SOURCE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent/'vendor'))

def generate_phantom_frames(CURRENT_REQUEST_RECORD,CURRENT_OUTPUT_ROOT,CURRENT_TELEMETRY_RECORDER):
 EXPERIMENT_OUTPUT_ROOT=CURRENT_OUTPUT_ROOT
 import torch
 import numpy as np
 import imageio.v2 as imageio
 from PIL import Image
 from accelerate import cpu_offload
 if not torch.cuda.is_available(): raise RuntimeError('CUDA GPU를 사용할 수 없습니다. CPU 추론은 실행하지 않습니다.')
 from phantom_wan.subject2video import Phantom_Wan_S2V
 from phantom_wan.configs import WAN_CONFIGS
 import phantom_wan.modules.model as phantom_model_module
 import phantom_wan.subject2video as phantom_subject_module
 def execute_cuda_attention(q,k,v,q_lens=None,k_lens=None,dropout_p=0.,softmax_scale=None,q_scale=None,causal=False,window_size=(-1,-1),deterministic=False,dtype=torch.bfloat16,version=None):
  # 외부 attention API 식별자는 공식 계약을 유지한다. 단일 배치의 길이를 직접 잘라 패딩 영향을 보존한다.
  if q.device.type!='cuda' or q.shape[0]!=1 or q_lens is not None or window_size!=(-1,-1) or dropout_p!=0 or causal or deterministic:
   raise ValueError('이 실험은 CUDA 단일 배치·전역 attention만 지원합니다.')
  attention_output_dtype=q.dtype
  attention_key_length=int(k_lens[0]) if k_lens is not None else k.shape[1]
  if q_scale is not None: q=q*q_scale
  with torch.nn.attention.sdpa_kernel(torch.nn.attention.SDPBackend.FLASH_ATTENTION):
   attention_output_tensor=torch.nn.functional.scaled_dot_product_attention(q.transpose(1,2).to(dtype),k[:,:attention_key_length].transpose(1,2).to(dtype),v[:,:attention_key_length].transpose(1,2).to(dtype),scale=softmax_scale)
  return attention_output_tensor.transpose(1,2).contiguous().to(attention_output_dtype)
 phantom_model_module.flash_attention=execute_cuda_attention
 def report_sampling_progress(current_timestep_values):
  CURRENT_TELEMETRY_RECORDER.update_generation_stage('inference')
  for current_step_index,current_timestep_tensor in enumerate(current_timestep_values):
   yield current_timestep_tensor
   CURRENT_TELEMETRY_RECORDER.record_generation_step(current_step_index+1)
  CURRENT_TELEMETRY_RECORDER.update_generation_stage('decode')
 phantom_subject_module.tqdm=report_sampling_progress
 current_pipeline_object=Phantom_Wan_S2V(config=WAN_CONFIGS['s2v-1.3B'],checkpoint_dir=str(WORKFLOW_SOURCE_ROOT/'.model/wan21-phantom-components'),phantom_ckpt=str(WORKFLOW_SOURCE_ROOT/'.model/phantom-1.3b/Phantom-Wan-1.3B.pth'),t5_cpu=False)
 cpu_offload(current_pipeline_object.text_encoder.model,execution_device=torch.device('cuda:0'),preload_module_classes=['T5RelativeEmbedding'])
 # 동일 공식 VAE 가중치를 엄격 변환하고 공간 타일 디코딩으로 GPU 메모리를 제한한다.
 from diffusers import AutoencoderKLWan
 from diffusers.loaders.single_file_utils import convert_wan_vae_to_diffusers
 current_vae_configuration=json.loads((Path(__file__).parent/'config/vae.json').read_text())
 current_tiled_decoder=AutoencoderKLWan.from_config(current_vae_configuration).eval().requires_grad_(False)
 current_original_weights=torch.load(WORKFLOW_SOURCE_ROOT/'.model/wan21-phantom-components/Wan2.1_VAE.pth',map_location='cpu',weights_only=True)
 current_tiled_decoder.load_state_dict(convert_wan_vae_to_diffusers(current_original_weights),strict=True)
 del current_original_weights
 current_tiled_decoder.enable_tiling()
 current_native_decode=current_pipeline_object.vae.decode
 def decode_saved_latents(current_latent_values):
  torch.save([current_latent_tensor.detach().cpu() for current_latent_tensor in current_latent_values],CURRENT_OUTPUT_ROOT/'denoised-latents.pt')
  current_pipeline_object.vae.model.cpu()
  torch.cuda.empty_cache()
  current_tiled_decoder.to(device='cuda',dtype=torch.float32)
  current_decoded_videos=[]
  for current_latent_tensor in current_latent_values:
   current_latent_mean=current_pipeline_object.vae.mean.view(1,16,1,1,1)
   current_latent_std=current_pipeline_object.vae.std.view(1,16,1,1,1)
   with torch.autocast('cuda',enabled=False):
    current_decoded_video=current_tiled_decoder.decode(current_latent_tensor.float().unsqueeze(0)*current_latent_std+current_latent_mean,return_dict=False)[0]
   current_decoded_videos.append(current_decoded_video.float().clamp(-1,1).squeeze(0))
  return current_decoded_videos
 current_pipeline_object.vae.decode=decode_saved_latents
 current_checked_outputs={'text_encoder':0,'transformer':0,'vae':0,'tiled_vae':0}
 def create_cuda_validator(current_component_name):
  def validate_cuda_output(current_module_object,current_input_values,current_output_value):
   if torch.is_tensor(current_output_value):
    if current_output_value.device.type!='cuda': raise RuntimeError(f'{current_component_name}의 모델 연산이 CUDA 밖에서 수행되었습니다.')
    current_checked_outputs[current_component_name]+=1
  return validate_cuda_output
 for current_component_name,current_model_object in [('text_encoder',current_pipeline_object.text_encoder.model),('transformer',current_pipeline_object.model),('vae',current_pipeline_object.vae.model),('tiled_vae',current_tiled_decoder)]:
  for current_layer_object in current_model_object.modules():
   if isinstance(current_layer_object,(torch.nn.Linear,torch.nn.Conv2d,torch.nn.Conv3d,torch.nn.Embedding)):
    current_layer_object.register_forward_hook(create_cuda_validator(current_component_name))
 current_positive_prompt=CURRENT_REQUEST_RECORD['prompt']
 current_negative_prompt=CURRENT_REQUEST_RECORD['phantom']['negative_prompt']
 current_token_counts={}
 for current_prompt_name,current_prompt_text in [('positive',current_positive_prompt),('negative',current_negative_prompt)]:
  current_token_counts[current_prompt_name]=len(current_pipeline_object.text_encoder.tokenizer.tokenizer(current_prompt_text,add_special_tokens=True,truncation=False)['input_ids'])
  if current_token_counts[current_prompt_name]>512: raise ValueError('프롬프트 512 토큰 제한 초과')
 CURRENT_TELEMETRY_RECORDER.update_generation_stage('encode')
 torch.cuda.reset_peak_memory_stats()
 with torch.inference_mode():
  current_video_tensor=current_pipeline_object.generate(current_positive_prompt,[Image.open(EXPERIMENT_OUTPUT_ROOT/current_reference_name).convert('RGB') for current_reference_name in CURRENT_REQUEST_RECORD['references']],size=(832,480),frame_num=CURRENT_REQUEST_RECORD['frames'],shift=CURRENT_REQUEST_RECORD['phantom']['flow_shift'],sampling_steps=CURRENT_REQUEST_RECORD['steps'],guide_scale_img=CURRENT_REQUEST_RECORD['phantom']['conditioning_scale'],guide_scale_text=CURRENT_REQUEST_RECORD['phantom']['guidance_scale'],n_prompt=current_negative_prompt,seed=CURRENT_REQUEST_RECORD['seed'],offload_model=True)
 if tuple(current_video_tensor.shape)!=(3,CURRENT_REQUEST_RECORD['frames'],480,832) or not torch.isfinite(current_video_tensor).all(): raise ValueError('출력 형태 또는 유한값 검증 실패')

 if not all(current_checked_outputs.values()):
  raise RuntimeError('GPU 연산 검증 표본 누락')
 current_frame_arrays=((current_video_tensor.float().clamp(-1,1).permute(1,2,3,0).cpu().numpy()+1)*127.5).round().astype(np.uint8)
 return [Image.fromarray(current_frame_array) for current_frame_array in current_frame_arrays], {'token_counts':current_token_counts,'gpu_checked_layer_outputs':current_checked_outputs}
