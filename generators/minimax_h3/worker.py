"""MiniMax H3 first-frame experiment on Diffusers, executed by the shared GPU queue."""
import gc,hashlib,json,os,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.local/minimax-h3-diffusers/deps'),str(ROOT/'.local/minimax-h3-diffusers/backend')]
os.environ['HF_HUB_OFFLINE']='1';os.environ['UNSLOTH_DIFFUSION_FP8_STORAGE']='1';os.environ['PYTORCH_ALLOC_CONF']='expandable_segments:False'
from generators.common.reference_video_worker import run_reference_video_worker,save_video_outputs
from workflow.common.generation_records import write_record_atomically
from workflow.common.model_storage_layout import resolve_minimax_snapshot
BASE=resolve_minimax_snapshot(ROOT / '.model')
from generators.minimax_h3.assets import ASSETS, FILES

def validate(request):
 for path,size,digest in FILES:
  if path.is_symlink() or not path.is_file() or path.stat().st_size!=size:raise ValueError(f'파일 준비 오류: {path}')
  with path.open('rb') as f:
   if hashlib.file_digest(f,'sha256').hexdigest()!=digest:raise ValueError(f'파일 해시 불일치: {path}')

def execute(job,attempt,request,metrics):
 import logging,torch,numpy as np
 from PIL import Image
 import diffusers,utils.hf_xet_fallback as helper
 from safetensors import safe_open
 from core.inference.video_minimax_h3_te import load_h3_quantized_text_encoder
 from core.inference.diffusion_comfy_quant import load_comfy_quant_transformer,scan_comfy_quant
 from transformers import AutoTokenizer,AutoProcessor
 assert torch.version.hip and torch.cuda.is_available()
 helper.hf_hub_download_with_xet_fallback=lambda *args,**kwargs:str(FILES[1][0])
 metrics.update_generation_stage('load')
 pipe=diffusers.ModularPipeline.from_pretrained(str(BASE),workflow='fl2va',local_files_only=True)
 tokenizer=AutoTokenizer.from_pretrained(str(BASE/'tokenizer'),local_files_only=True)
 processor=AutoProcessor.from_pretrained(str(BASE/'processor'),local_files_only=True)
 scheduler=diffusers.MiniMaxH3Scheduler.from_pretrained(str(BASE/'scheduler'),local_files_only=True)
 audio_scheduler=diffusers.MiniMaxH3Scheduler.from_pretrained(str(BASE/'audio_scheduler'),local_files_only=True)
 pipe.update_components(tokenizer=tokenizer,processor=processor,scheduler=scheduler,audio_scheduler=audio_scheduler)
 encoder=load_h3_quantized_text_encoder(str(BASE),'int8',dtype=torch.bfloat16,local_base=str(BASE),local_files_only=True,logger=logging.getLogger('h3'))
 if encoder is None:raise RuntimeError('Diffusers 인코더 변환 실패')
 encoder._apply(lambda t:t.clone().to('cuda') if t.device.type=='cpu' else t.to('cuda'))
 if any(t.device.type!='cuda' for t in list(encoder.parameters())+list(encoder.buffers())):raise RuntimeError('인코더 GPU 적재 실패')
 pipe.update_components(text_encoder=encoder)
 vae=diffusers.AutoencoderKLMiniMaxH3.from_pretrained(str(ASSETS/'vae'),torch_dtype=torch.float16,local_files_only=True).to('cuda')
 audio_vae=diffusers.AutoencoderKLMiniMaxH3Audio.from_pretrained(str(ASSETS/'audio_vae'),torch_dtype=torch.float32,local_files_only=True).to('cuda')
 pipe.update_components(vae=vae,audio_vae=audio_vae)
 path=str(FILES[0][0]);scan=scan_comfy_quant(path)
 model=load_comfy_quant_transformer(diffusers.MiniMaxH3Transformer3DModel,path,scan,{'config':str(BASE),'subfolder':'transformer','torch_dtype':torch.bfloat16,'local_files_only':True},int8_backend=None,fp8_backend=None,fp8_storage=True,family='minimax-h3')
 if getattr(model,'_unsloth_comfy_quant',{}).get('fp8_stored')!=300:raise RuntimeError('FP8 계층 수 불일치')
 model=model.to('cuda')
 # Diffusers-native LightX2V LoRA, each factor is applied at alpha/rank.
 class LoRALinear(torch.nn.Module):
  def __init__(self,base,a,b,scale):
   super().__init__();self.base=base;self.register_buffer('lora_a',a);self.register_buffer('lora_b',b);self.scale=scale
  def forward(self,x,*args,**kwargs):
   return self.base(x,*args,**kwargs)+torch.nn.functional.linear(torch.nn.functional.linear(x,self.lora_a),self.lora_b)*self.scale
 with safe_open(str(FILES[6][0]),framework='pt',device='cpu') as f:
  keys=list(f.keys()); suffix='.lora_A.default.weight'; names=sorted(k[:-len(suffix)] for k in keys if k.endswith(suffix))
  if len(names)*2!=len(keys) or not names:raise ValueError('LoRA 키 구성 오류')
  alpha=float(f.metadata()['alpha'])
  for name in names:
   parent_name,_,leaf=name.rpartition('.');parent=model.get_submodule(parent_name);old=getattr(parent,leaf)
   a=f.get_tensor(name+suffix);b=f.get_tensor(name+'.lora_B.default.weight')
   if len(a.shape)!=2 or len(b.shape)!=2 or b.shape[1]!=a.shape[0] or getattr(old,'in_features',None)!=a.shape[1] or getattr(old,'out_features',None)!=b.shape[0]:raise ValueError(f'LoRA 차원 불일치: {name}')
   setattr(parent,leaf,LoRALinear(old,a.clone().to('cuda'),b.clone().to('cuda'),alpha/a.shape[0]))
 pipe.update_components(transformer=model)
 write_record_atomically(attempt/'runtime-environment.json',{'backend':'Hugging Face Diffusers','diffusers':diffusers.__version__,'torch':str(torch.__version__),'hip':torch.version.hip,'gpu':torch.cuda.get_device_name(0),'transformer':'FP8 storage / BF16 GPU compute','text_encoder':'INT8 ConvRot','turbo_lora_applied':len(names),'turbo_alpha':alpha,'turbo_rank':128,'unsloth_revision':'e9e031d2fabec27d62269623737fbc0ba611862c','offloading':False,'experimental_resolution':True})
 with Image.open(job/'reference-1.png') as im:
  im=im.convert('RGB');im.thumbnail((request['width'],request['height']),Image.Resampling.LANCZOS);image=Image.new('RGB',(request['width'],request['height']),'white');image.paste(im,((image.width-im.width)//2,(image.height-im.height)//2))
 metrics.update_generation_stage('inference')
 step=[0]
 def check_output(_module,_args,output):
  def check(x):
   if torch.is_tensor(x) and not torch.isfinite(x).all().item():raise ValueError('생성 모델 출력에 비유한 값')
   if isinstance(x,(tuple,list)):
    for y in x:check(y)
  check(output);step[0]+=1;metrics.record_generation_step(step[0])
 hook=model.register_forward_hook(check_output)
 with torch.no_grad():
  result=pipe(prompt=request['prompt'],image=image,width=request['width'],height=request['height'],num_frames=request['frames'],num_inference_steps=request['steps']+1,generator=torch.Generator(device='cpu').manual_seed(request['seed']),output_type='np',output=['videos','audio','sampling_rate'])
 hook.remove()
 videos=result['videos'];frames=np.asarray(videos[0])
 if not np.isfinite(frames).all():raise ValueError('영상에 비유한 값이 있습니다.')
 frames=(np.clip(frames,0,1)*255).round().astype(np.uint8)
 if len(frames)!=request['frames'] or step[0]!=request['steps']:raise ValueError(f'프레임 또는 스텝 수 불일치: {len(frames)}, {step[0]}')
 metrics.update_generation_stage('saving');hashes=save_video_outputs(attempt,frames,24)
 import soundfile as sf,subprocess,imageio_ffmpeg
 audio=result['audio'];audio=audio.detach().cpu().numpy() if torch.is_tensor(audio) else np.asarray(audio)
 if not np.isfinite(audio).all():raise ValueError('오디오 비유한 값')
 audio=np.squeeze(audio)
 if audio.ndim==2 and audio.shape[0]<=2:audio=audio.T
 sf.write(str(attempt/'audio.wav'),audio,int(result['sampling_rate']))
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(attempt/'preview.mp4'),'-i',str(attempt/'audio.wav'),'-c:v','copy','-c:a','aac','-shortest',str(attempt/'preview-audio.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 os.replace(attempt/'preview-audio.mp4',attempt/'preview.mp4')
 return {'attempt':attempt.name,'frames':len(frames),'fps':24,'video':'preview.mp4','output_sha256':hashes,'video_sha256':hashlib.sha256((attempt/'preview.mp4').read_bytes()).hexdigest(),'model_id':'MiniMax H3 Diffusers FP8 + Turbo 8-step','quality_status':'사용자 검수 대기'}
if __name__=='__main__':run_reference_video_worker(ROOT/'.tmp/test/minimax-h3-i2v',Path(__file__),validate,execute,assets_validator_takes_request=True)
