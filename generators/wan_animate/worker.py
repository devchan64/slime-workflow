"""공용 GPU 대기열에서 호출하는 Animate Q4 실험 작업자."""
from pathlib import Path
import argparse,sys,json,uuid,traceback,signal,hashlib,zipfile,importlib.util,gc,os
ANIMATE_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ANIMATE_WORKSPACE_ROOT))
from generators.wan_animate.contracts import ANIMATE_JOB_STORAGE, ANIMATE_RUNTIME_DIRECTORY, validate_animate_assets
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder

def handle_animate_signal(current_signal_number,current_stack_frame):
 raise InterruptedError(f'종료 신호 {current_signal_number}')

def execute_animate_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
 current_allocator_options=[current_option_value for current_option_value in os.environ.get('PYTORCH_ALLOC_CONF','').split(',') if current_option_value and not current_option_value.startswith('expandable_segments:')]
 current_allocator_options.append('expandable_segments:True')
 os.environ['PYTORCH_ALLOC_CONF']=','.join(current_allocator_options)
 sys.path.insert(0,str(ANIMATE_RUNTIME_DIRECTORY/'ComfyUI'))
 import comfy.cli_args
 comfy.cli_args.args.lowvram=True
 import torch,numpy as np
 from PIL import Image
 import nodes,folder_paths,comfy.model_management,comfy.sample
 from comfy_extras.nodes_wan import WanAnimateToVideo
 from comfy_extras.nodes_model_advanced import ModelSamplingSD3
 import imageio.v2 as imageio
 if not torch.cuda.is_available(): raise RuntimeError('CUDA 사용 불가')
 def resolve_encoder_cuda():
  return torch.device('cuda:0')
 comfy.model_management.text_encoder_device=resolve_encoder_cuda
 runtime_package_spec=importlib.util.spec_from_file_location('animate_gguf_runtime',ANIMATE_RUNTIME_DIRECTORY/'ComfyUI-GGUF/__init__.py',submodule_search_locations=[str(ANIMATE_RUNTIME_DIRECTORY/'ComfyUI-GGUF')])
 runtime_package_module=importlib.util.module_from_spec(runtime_package_spec)
 sys.modules[runtime_package_spec.name]=runtime_package_module
 runtime_package_spec.loader.exec_module(runtime_package_module)
 for model_folder_name,model_relative_path in [('diffusion_models','.model/wan22-animate-14b-gguf'),('unet_gguf','.model/wan22-animate-14b-gguf'),('clip','.model/wan22-animate-components'),('clip_gguf','.model/wan22-animate-components'),('vae','.model/wan22-animate-components/split_files/vae')]:
  folder_paths.add_model_folder_path(model_folder_name,str(ANIMATE_WORKSPACE_ROOT/model_relative_path))
 current_metrics_recorder.update_generation_stage('load')
 text_encoder_model=runtime_package_module.NODE_CLASS_MAPPINGS['CLIPLoaderGGUF']().load_clip('umt5-xxl-encoder-Q4_K_M.gguf',type='wan')[0]
 if text_encoder_model.patcher.load_device.type!='cuda': raise RuntimeError('텍스트 인코더 CUDA 설정 오류')
 positive_condition_data=nodes.CLIPTextEncode().encode(text_encoder_model,current_request_record['prompt'])[0]
 negative_condition_data=nodes.CLIPTextEncode().encode(text_encoder_model,'')[0]
 comfy.model_management.unload_all_models()
 del text_encoder_model
 gc.collect()
 comfy.model_management.soft_empty_cache()
 vae_model_object=nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0]
 from generators.wan_animate.memory import TiledAnimateVae
 vae_model_object=TiledAnimateVae(vae_model_object)
 write_record_atomically(current_attempt_root/'memory-policy.json',{'inference_mode':True,'encode_tile_pixels':256,'encode_tile_frames':9,'encode_overlap_frames':5,'decode_tile_latents':32,'decode_temporal_latents':max(2,(current_request_record['frames']-1)//4+1),'decode_temporal_policy':'full-sequence-spatial-tiles','compute_device':'cuda','allocator':os.environ['PYTORCH_ALLOC_CONF']})
 (current_attempt_root/'memory-source.py').write_bytes((ANIMATE_WORKSPACE_ROOT/'generators/common/wan_video_memory.py').read_bytes())
 current_metrics_recorder.update_generation_stage('encoding')
 input_image_tensors=[torch.from_numpy(np.array(Image.open(current_job_root/current_image_name).convert('RGB')).astype(np.float32)/255.0) for current_image_name in current_request_record['references']]
 reference_image_tensor=input_image_tensors[0].unsqueeze(0)
 current_frame_count=current_request_record['frames']
 current_output_fps=current_request_record.get('fps',16)
 pose_video_tensor=torch.stack(input_image_tensors[1:1+current_frame_count]) if len(input_image_tensors)>1 else None
 face_video_tensor=torch.stack(input_image_tensors[1+current_frame_count:]) if len(input_image_tensors)>1+current_frame_count else None
 import comfy.clip_vision
 clip_vision_model=comfy.clip_vision.load(str(ANIMATE_WORKSPACE_ROOT/'.model/wan22-animate-components/split_files/clip_vision/clip_vision_h.safetensors'))
 if clip_vision_model.load_device.type!='cuda': raise RuntimeError('CLIP Vision CUDA 설정 오류')
 clip_condition_output=clip_vision_model.encode_image(reference_image_tensor,crop=False)
 comfy.model_management.unload_all_models()
 del clip_vision_model
 gc.collect()
 comfy.model_management.soft_empty_cache()
 current_sampler_name='uni_pc'
 current_scheduler_name='sgm_uniform'
 write_record_atomically(current_attempt_root/'conditioning.json',{'reference_images':1,'pose_frames':0 if pose_video_tensor is None else len(pose_video_tensor),'face_video':face_video_tensor is not None,'face_frames':0 if face_video_tensor is None else len(face_video_tensor),'clip_vision':clip_condition_output is not None,'sampler':current_sampler_name,'scheduler':current_scheduler_name})
 condition_output_data=WanAnimateToVideo.execute(positive_condition_data,negative_condition_data,vae_model_object,current_request_record['width'],current_request_record['height'],current_frame_count,1,5,0,reference_image=reference_image_tensor,pose_video=pose_video_tensor,face_video=face_video_tensor,clip_vision_output=clip_condition_output)
 positive_condition_data,negative_condition_data,latent_input_record,trim_latent_count,trim_image_count=condition_output_data[:5]
 comfy.model_management.unload_all_models()
 comfy.model_management.soft_empty_cache()
 diffusion_model_object=runtime_package_module.NODE_CLASS_MAPPINGS['UnetLoaderGGUF']().load_unet('Wan2.2-Animate-14B-Q4_K_M.gguf')[0]
 diffusion_model_object=ModelSamplingSD3().patch(diffusion_model_object,current_request_record['flow_shift'])[0]
 current_metrics_recorder.update_generation_stage('inference')
 def record_animate_step(current_step_index,current_denoised_tensor,current_sample_tensor,current_step_total):
  current_metrics_recorder.record_generation_step(current_step_index+1)
 latent_input_tensor=latent_input_record['samples']
 noise_input_tensor=comfy.sample.prepare_noise(latent_input_tensor,current_request_record['seed'])
 with torch.inference_mode():
  latent_output_tensor=comfy.sample.sample(diffusion_model_object,noise_input_tensor,current_request_record['steps'],current_request_record['guidance_scale'],current_sampler_name,current_scheduler_name,positive_condition_data,negative_condition_data,latent_input_tensor,denoise=1.0,noise_mask=latent_input_record.get('noise_mask'),callback=record_animate_step,seed=current_request_record['seed'])
 comfy.model_management.unload_all_models()
 del diffusion_model_object
 gc.collect()
 comfy.model_management.soft_empty_cache()
 current_metrics_recorder.update_generation_stage('saving')
 with torch.inference_mode():
  current_decode_latents=latent_output_tensor[:,:,trim_latent_count:]
  torch.save({'samples':current_decode_latents.detach().cpu(),'trim_image_count':trim_image_count,'source_frames':current_request_record.get('source_frames',current_frame_count),'fps':current_output_fps},current_attempt_root/'decode-latents.pt')
  # 시간 전체를 한 타일로 처리해 8프레임 간격의 디코딩 경계를 없앤다. 공간 타일은 유지한다.
  decoded_frame_tensor=vae_model_object.decode(current_decode_latents,current_temporal_tile_count=max(2,current_decode_latents.shape[2]))
 decoded_frame_tensor=decoded_frame_tensor[trim_image_count:]
 if decoded_frame_tensor.shape[0]!=current_frame_count: raise ValueError(f'출력 프레임 수 오류: {decoded_frame_tensor.shape}')
 decoded_frame_tensor=decoded_frame_tensor[:current_request_record.get('source_frames',current_frame_count)]
 current_frame_count=len(decoded_frame_tensor)
 output_frame_arrays=(decoded_frame_tensor.clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)
 output_frame_hashes=[]
 with zipfile.ZipFile(current_attempt_root/'frames.zip','w',compression=zipfile.ZIP_DEFLATED) as frame_archive_file:
  for current_frame_index,current_frame_array in enumerate(output_frame_arrays):
   current_frame_path=current_attempt_root/f'output-{current_frame_index:03d}.png'
   Image.fromarray(current_frame_array).save(current_frame_path)
   output_frame_hashes.append(hashlib.sha256(current_frame_path.read_bytes()).hexdigest())
   frame_archive_file.write(current_frame_path,current_frame_path.name)
 imageio.mimwrite(str(current_attempt_root/'preview.mp4'),output_frame_arrays,fps=current_output_fps,codec='libx264',quality=8,macro_block_size=1)
 comfy.model_management.unload_all_models()
 del vae_model_object
 gc.collect()
 return {'attempt':current_attempt_root.name,'frames':current_frame_count,'fps':current_output_fps,'duration_seconds':current_frame_count/current_output_fps,'output_sha256':output_frame_hashes,'model_id':'QuantStack/Wan2.2-Animate-14B-GGUF','model_compute_device':'cuda','prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),'quality_status':'사용자 검수 대기'}

def execute_animate_worker():
 current_argument_parser=argparse.ArgumentParser(description=__doc__)
 current_argument_parser.add_argument('--job-dir',type=Path,required=True)
 current_job_root=current_argument_parser.parse_args().job_dir.resolve()
 if current_job_root.parent!=ANIMATE_JOB_STORAGE.resolve(): raise ValueError('Animate 작업 경로 오류')
 current_request_record=json.loads((current_job_root/'request.json').read_text())
 from tools.review.domains.image.three_reference_generation import verify_reference_snapshots
 verify_reference_snapshots(current_job_root,current_request_record)
 current_attempt_root=current_job_root/'attempts'/uuid.uuid4().hex
 current_attempt_root.mkdir(parents=True)
 write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_root.name})
 write_record_atomically(current_attempt_root/'request.json',current_request_record)
 (current_attempt_root/'executor-source.py').write_bytes(Path(__file__).read_bytes())
 current_metrics_recorder=GenerationTelemetryRecorder(current_attempt_root,current_request_record['steps'],[])
 current_metrics_recorder.start_generation_telemetry()
 current_final_status='failed'
 signal.signal(signal.SIGTERM,handle_animate_signal)
 signal.signal(signal.SIGINT,handle_animate_signal)
 try:
  validate_animate_assets()
  if current_request_record.get('driving_video_file'):
   import subprocess
   current_metrics_recorder.update_generation_stage('preprocessing')
   current_preprocess_environment={**os.environ,'PYTHONPATH':str(ANIMATE_RUNTIME_DIRECTORY/'preprocess-deps')}
   subprocess.run([sys.executable,str(Path(__file__).parent/'preprocess.py'),str(current_job_root),str(current_attempt_root)],env=current_preprocess_environment,check=True)
   current_pose_names=[str((current_attempt_root/'preprocess'/f'pose-{current_frame_index:03d}.png').relative_to(current_job_root)) for current_frame_index in range(current_request_record['frames'])]
   current_face_names=[str((current_attempt_root/'preprocess'/f'face-{current_frame_index:03d}.png').relative_to(current_job_root)) for current_frame_index in range(current_request_record['frames'])]
   current_request_record={**current_request_record,'references':[current_request_record['references'][0],*current_pose_names,*current_face_names]}
  import torch
  with torch.inference_mode():
   current_result_record=execute_animate_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder)
  write_record_atomically(current_attempt_root/'result.json',current_result_record)
  write_record_atomically(current_job_root/'result.json',current_result_record)
  current_final_status='completed'
 except BaseException as current_execution_error:
  current_final_status='cancelled' if isinstance(current_execution_error,(InterruptedError,KeyboardInterrupt)) else 'failed'
  write_record_atomically(current_attempt_root/'error.json',{'error':str(current_execution_error),'traceback':traceback.format_exc()})
  traceback.print_exc()
  raise
 finally:
  current_metrics_recorder.finish_generation_telemetry(current_final_status)
  write_record_atomically(current_job_root/'status.json',{'status':current_final_status,'attempt':current_attempt_root.name})
if __name__=='__main__':
 execute_animate_worker()
