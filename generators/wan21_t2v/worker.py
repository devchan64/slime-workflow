"""Wan 2.1 T2V 1.3B experiment, run through the GPU queue."""
import gc
import hashlib
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    os.environ['PYTORCH_ALLOC_CONF']='expandable_segments:False'
    os.environ.pop('PYTORCH_CUDA_ALLOC_CONF',None)
    temp=ROOT/'.tmp/wan21-t2v-runtime'; temp.mkdir(parents=True,exist_ok=True)
    os.environ['TMPDIR']=str(temp)
sys.path.insert(0,str(ROOT))

from generators.wan21_t2v.assets import DIRECTORY, FILES, BOSS_LORA, inspect_assets, inspect_boss_lora
from generators.wan21_video_contracts import RUNTIME
from generators.wan21_video_lora import apply_adapter
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from workflow.common.generation_records import write_record_atomically

JOB_STORAGE=ROOT/'.tmp/test/wan21-t2v'


def validate_assets(request):
    if not inspect_assets(): raise ValueError('Wan 2.1 T2V 모델 및 가속 LoRA 무결성을 확인하세요.')
    from generators.wan_i2v.contracts import SHARED_FILES, COMFY_REVISION
    for path,size in SHARED_FILES:
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=size:
            raise ValueError(f'공유 모델 파일 준비 필요: {path}')
    if (RUNTIME/'PINNED_REVISION').read_text().strip()!=COMFY_REVISION:
        raise ValueError('ComfyUI 고정 리비전이 다릅니다.')
    if request['action_lora'] and not inspect_boss_lora(BOSS_LORA):
        raise ValueError('KXSR 1.3B LoRA 파일이 없거나 SHA-256이 일치하지 않습니다.')


def load_model(torch,sd,utils,supported,path):
    device=torch.device('cuda:0')
    free,_=torch.cuda.mem_get_info(device)
    required=2*path.stat().st_size+4*1024**3
    if free<required: raise RuntimeError(f'T2V 모델 적재 GPU 여유 메모리 부족: {free} < {required}')
    config=supported.WAN21_T2V; original=config.get_model
    def build_meta(instance,state_dict,prefix='',device=None):
        return original(instance,state_dict,prefix,device=torch.device('meta')).to_empty(device=torch.device('cuda:0'))
    try:
        config.get_model=build_meta
        weights=utils.load_torch_file(str(path),device=device)
        model=sd.load_diffusion_model_state_dict(weights,model_options={'dtype':torch.bfloat16})
        if model is None or model.load_device.type!='cuda' or model.offload_device.type!='cuda':
            raise RuntimeError('T2V GPU 전용 모델 로드 실패')
        return model
    finally:
        config.get_model=original


def execute(job,attempt,request,metrics):
    sys.path.insert(0,str(RUNTIME))
    import torch
    import numpy as np
    import comfy.cli_args
    comfy.cli_args.args.lowvram=False; comfy.cli_args.args.highvram=True; comfy.cli_args.args.gpu_only=True
    comfy.cli_args.args.cpu_vae=False; comfy.cli_args.args.fp32_vae=True; comfy.cli_args.args.bf16_unet=True
    import nodes,folder_paths,comfy.model_management,comfy.sample,comfy.sd,comfy.utils,comfy.supported_models
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from generators.wan_fun.vae_diagnostic import disable_vae_tiled_fallback
    from generators.wan_fun.numerical_diagnostics import guard_fun_vae_method,record_fun_numerical_step
    if not torch.version.hip or not torch.cuda.is_available(): raise RuntimeError('ROCm GPU가 필요합니다.')
    comfy.model_management.text_encoder_device=lambda:torch.device('cuda:0')
    folder_paths.add_model_folder_path('text_encoders',str(ROOT/'.model/wan22-animate-components/split_files/text_encoders'))
    folder_paths.add_model_folder_path('vae',str(ROOT/'.model/wan22-animate-components/split_files/vae'))
    metrics.update_generation_stage('load')
    clip=nodes.CLIPLoader().load_clip('umt5_xxl_fp16.safetensors',type='wan')[0]
    if clip.patcher.load_device.type!='cuda' or clip.patcher.offload_device.type!='cuda': raise RuntimeError('텍스트 인코더는 GPU 전용이어야 합니다.')
    positive=nodes.CLIPTextEncode().encode(clip,request['prompt'])[0]
    negative=nodes.CLIPTextEncode().encode(clip,request['negative_prompt'])[0]
    if not all(torch.isfinite(c[0][0]).all().item() for c in (positive,negative)): raise ValueError('텍스트 조건에 비유한 값이 있습니다.')
    comfy.model_management.unload_all_models(); del clip; gc.collect(); comfy.model_management.soft_empty_cache()
    model=load_model(torch,comfy.sd,comfy.utils,comfy.supported_models,DIRECTORY/'base/model.safetensors')
    counts={}; boss_digest=None
    if request['acceleration']:
        model,counts['acceleration']=apply_adapter(model,DIRECTORY/'acceleration/self-forcing.safetensors',1.0,comfy.sd,comfy.utils)
    if request['action_lora']:
        with BOSS_LORA.open('rb') as stream: boss_digest=hashlib.file_digest(stream,'sha256').hexdigest()
        model,counts['action']=apply_adapter(model,BOSS_LORA,request['action_strength'],comfy.sd,comfy.utils)
    model=ModelSamplingSD3().patch(model,request['flow_shift'])[0]
    latent=torch.zeros([1,16,((request['frames']-1)//4)+1,request['height']//8,request['width']//8],device=comfy.model_management.intermediate_device())
    noise=comfy.sample.prepare_noise(latent,request['seed']); metrics.update_generation_stage('inference')
    def callback(index,denoised,sample_value,total):
        torch.cuda.synchronize(); record_fun_numerical_step(torch,attempt,'t2v',index+1,denoised,sample_value); metrics.record_generation_step(index+1)
    sample=comfy.sample.sample(model,noise,request['steps'],request['guidance_scale'],'euler','simple',positive,negative,latent,denoise=1.0,force_full_denoise=True,callback=callback,seed=request['seed'])
    if not torch.isfinite(sample).all().item(): raise ValueError('샘플러 출력에 비유한 값이 있습니다.')
    write_record_atomically(attempt/'model-assets.json',{'files':[{'path':p,'repository':r,'revision':v,'source':s,'size':n,'sha256':h} for p,r,v,s,n,h in FILES], 'boss_sha256':boss_digest,'sampler':'euler','scheduler':'simple','lora_patch_counts':counts})
    comfy.model_management.unload_all_models(); del model; gc.collect(); comfy.model_management.soft_empty_cache()
    metrics.update_generation_stage('decoding'); vae=nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0]
    if vae.device.type!='cuda' or vae.patcher.offload_device.type!='cuda' or vae.vae_dtype!=torch.float32: raise RuntimeError('VAE는 FP32 GPU 전용이어야 합니다.')
    disable_vae_tiled_fallback(vae)
    with guard_fun_vae_method(vae,attempt,torch,'decode'): frames=vae.decode(sample)
    if frames.ndim==5: frames=frames.flatten(0,1)
    if frames.shape[0]!=request['frames'] or not torch.isfinite(frames).all().item(): raise ValueError('출력 프레임 수 또는 유한값 오류')
    arrays=(frames.clamp(0,1).cpu().numpy()*255).round().astype(np.uint8)
    hashes=save_video_outputs(attempt,arrays,16)
    return {'attempt':attempt.name,'frames':len(arrays),'fps':16,'output_sha256':hashes,'model_id':'Wan 2.1 T2V 1.3B','prompt_sha256':hashlib.sha256(request['prompt'].encode()).hexdigest(),'prompt_words':len(request['prompt'].split()),'quality_status':'사용자 검수 대기'}


if __name__=='__main__':
    run_reference_video_worker(JOB_STORAGE,Path(__file__),validate_assets,execute,assets_validator_takes_request=True)
