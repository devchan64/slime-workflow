"""Wan 2.1 I2V single-denoiser experiment, run through the GPU queue."""

if __name__ == '__main__':
    raise SystemExit('Wan 2.1 I2V 작업자는 폐기되어 새 작업을 실행하지 않습니다.')
import gc
import hashlib
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    os.environ['PYTORCH_ALLOC_CONF']='expandable_segments:False'
    os.environ.pop('PYTORCH_CUDA_ALLOC_CONF',None)
    temp=ROOT/'.tmp/wan21-i2v-runtime'; temp.mkdir(parents=True,exist_ok=True)
    os.environ['TMPDIR']=str(temp)
sys.path.insert(0,str(ROOT))

from generators.wan21_i2v.assets import DIRECTORY, FILES, inspect_assets
from generators.wan21_video_contracts import RUNTIME
from generators.wan_i2v.worker import load_i2v_model
from generators.wan21_video_lora import apply_adapter
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from workflow.common.generation_records import write_record_atomically

JOB_STORAGE=ROOT/'.tmp/test/wan21-i2v'


def validate_assets(request):
    if not inspect_assets():
        raise ValueError('Wan 2.1 I2V 모델 및 LoRA 파일 무결성을 확인하세요.')
    from generators.wan_i2v.contracts import SHARED_FILES, COMFY_REVISION
    for path, size in SHARED_FILES:
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError(f'공유 모델 파일 준비 필요: {path}')
    if (RUNTIME/'PINNED_REVISION').read_text().strip() != COMFY_REVISION:
        raise ValueError('ComfyUI 고정 리비전이 다릅니다.')
    if request.get('action_lora') and request.get('action_variant','fight') in ('attack_high','attack_low'):
        from generators.wan21_i2v.attack_lora import inspect_assets as inspect_attack_assets
        if not inspect_attack_assets(): raise ValueError('공격 동작 LoRA 파일 무결성을 확인하세요.')


def execute(job, attempt, request, metrics):
    raise RuntimeError('Wan 2.1 I2V 생성 기능은 폐기되었습니다.')
    sys.path.insert(0,str(RUNTIME))
    import torch
    import numpy as np
    from PIL import Image
    import comfy.cli_args
    comfy.cli_args.args.lowvram=False
    comfy.cli_args.args.highvram=True
    comfy.cli_args.args.gpu_only=True
    comfy.cli_args.args.cpu_vae=False
    comfy.cli_args.args.fp32_vae=True
    comfy.cli_args.args.bf16_unet=True
    import nodes, folder_paths, comfy.model_management, comfy.sample, comfy.sd, comfy.utils, comfy.supported_models, comfy.clip_vision
    from comfy_extras.nodes_wan import WanImageToVideo
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from generators.wan_fun.vae_diagnostic import disable_vae_tiled_fallback
    from generators.wan_fun.numerical_diagnostics import guard_fun_vae_method, record_fun_numerical_step
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('ROCm GPU가 필요합니다.')
    comfy.model_management.text_encoder_device=lambda:torch.device('cuda:0')
    folder_paths.add_model_folder_path('text_encoders',str(ROOT/'.model/wan22-animate-components/split_files/text_encoders'))
    folder_paths.add_model_folder_path('vae',str(ROOT/'.model/wan22-animate-components/split_files/vae'))
    metrics.update_generation_stage('load')
    clip=nodes.CLIPLoader().load_clip('umt5_xxl_fp16.safetensors',type='wan')[0]
    if clip.patcher.load_device.type != 'cuda' or clip.patcher.offload_device.type != 'cuda':
        raise RuntimeError('텍스트 인코더는 GPU 전용이어야 합니다.')
    positive=nodes.CLIPTextEncode().encode(clip,request['prompt'])[0]
    negative=nodes.CLIPTextEncode().encode(clip,request['negative_prompt'])[0]
    if not all(torch.isfinite(cond[0][0]).all().item() for cond in (positive,negative)):
        raise ValueError('텍스트 조건에 비유한 값이 있습니다.')
    comfy.model_management.unload_all_models(); del clip; gc.collect(); comfy.model_management.soft_empty_cache()
    with Image.open(job/request['references'][0]) as image:
        pixels=torch.from_numpy(np.asarray(image.convert('RGB'),dtype=np.float32)/255).unsqueeze(0)
    vision=comfy.clip_vision.load(str(DIRECTORY/'clip_vision/clip_vision_h.safetensors'))
    if vision is None:
        raise ValueError('비전 인코더를 읽을 수 없습니다.')
    vision_output=vision.encode_image(pixels)
    if not torch.isfinite(vision_output.penultimate_hidden_states).all().item():
        raise ValueError('이미지 인코더 출력에 비유한 값이 있습니다.')
    comfy.model_management.unload_all_models(); del vision; gc.collect(); comfy.model_management.soft_empty_cache()
    def load_vae():
        vae=nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0]
        if vae.device.type != 'cuda' or vae.patcher.offload_device.type != 'cuda' or vae.vae_dtype != torch.float32:
            raise RuntimeError('VAE는 FP32 GPU 전용이어야 합니다.')
        disable_vae_tiled_fallback(vae)
        return vae
    vae=load_vae(); metrics.update_generation_stage('encoding')
    with guard_fun_vae_method(vae,attempt,torch,'encode'):
        positive,negative,latent=WanImageToVideo.execute(positive,negative,vae,request['width'],request['height'],request['frames'],1,start_image=pixels,clip_vision_output=vision_output)
    if not torch.isfinite(positive[0][1]['concat_latent_image']).all().item():
        raise ValueError('참조 이미지 잠재값에 비유한 값이 있습니다.')
    comfy.model_management.unload_all_models(); del vae,vision_output; gc.collect(); comfy.model_management.soft_empty_cache()
    metrics.update_generation_stage('load')
    model=load_i2v_model(torch,comfy.sd,comfy.utils,comfy.supported_models,DIRECTORY/'base/model.safetensors')
    counts={}
    if request['acceleration']:
        model,counts['acceleration']=apply_adapter(model,DIRECTORY/'acceleration/lightx2v.safetensors',1.0,comfy.sd,comfy.utils)
    if request['action_lora']:
        variant=request.get('action_variant','fight')
        action_files={'fight':'action/fight.safetensors','attack_high':'action/attack-high.safetensors','attack_low':'action/attack-low.safetensors'}
        if variant not in action_files: raise ValueError('지원하지 않는 동작 LoRA 종류입니다.')
        model,counts['action']=apply_adapter(model,DIRECTORY/action_files[variant],request['action_strength'],comfy.sd,comfy.utils)
    model=ModelSamplingSD3().patch(model,request['flow_shift'])[0]
    noise=comfy.sample.prepare_noise(latent['samples'],request['seed'])
    metrics.update_generation_stage('inference')
    def callback(index,denoised,sample_value,total):
        torch.cuda.synchronize()
        record_fun_numerical_step(torch,attempt,'i2v',index+1,denoised,sample_value)
        metrics.record_generation_step(index+1)
    sample=comfy.sample.sample(model,noise,request['steps'],request['guidance_scale'],'euler','simple',positive,negative,latent['samples'],denoise=1.0,force_full_denoise=True,callback=callback,seed=request['seed'])
    if not torch.isfinite(sample).all().item(): raise ValueError('샘플러 출력에 비유한 값이 있습니다.')
    recorded_files=list(FILES)
    if request['action_lora'] and request.get('action_variant','fight') in ('attack_high','attack_low'):
        from generators.wan21_i2v.attack_lora import FILES as attack_files
        recorded_files.extend(attack_files)
    write_record_atomically(attempt/'model-assets.json',{'files':[{'path':p,'repository':r,'revision':v,'source':s,'size':n,'sha256':h} for p,r,v,s,n,h in recorded_files], 'action_variant':request.get('action_variant','fight'), 'sampler':'euler','scheduler':'simple','lora_patch_counts':counts})
    comfy.model_management.unload_all_models(); del model; gc.collect(); comfy.model_management.soft_empty_cache()
    metrics.update_generation_stage('decoding'); vae=load_vae()
    with guard_fun_vae_method(vae,attempt,torch,'decode'):
        frames=vae.decode(sample)
    if frames.ndim==5: frames=frames.flatten(0,1)
    if frames.shape[0]!=request['frames'] or not torch.isfinite(frames).all().item(): raise ValueError('출력 프레임 수 또는 유한값 오류')
    arrays=(frames.clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)
    hashes=save_video_outputs(attempt,arrays,16)
    return {'attempt':attempt.name,'frames':len(arrays),'fps':16,'output_sha256':hashes,'model_id':'Wan 2.1 I2V 14B 480P','prompt_sha256':hashlib.sha256(request['prompt'].encode()).hexdigest(),'prompt_words':len(request['prompt'].split()),'quality_status':'사용자 검수 대기'}


if __name__=='__main__':
    run_reference_video_worker(JOB_STORAGE,Path(__file__),validate_assets,execute,assets_validator_takes_request=True)
