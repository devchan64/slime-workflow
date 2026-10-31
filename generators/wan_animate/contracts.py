"""Wan2.2 Animate Q4 실험 입력 계약. 모델은 코드로 고정한다."""
from pathlib import Path
import io, math
from PIL import Image
ANIMATE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ANIMATE_JOB_STORAGE = ANIMATE_WORKSPACE_ROOT/'.tmp/test/wan22-animate'
ANIMATE_RUNTIME_DIRECTORY = ANIMATE_WORKSPACE_ROOT/'.local/wan22-animate'
ANIMATE_MODEL_FILES = {
 'diffusion':('.model/wan22-animate-14b-gguf/Wan2.2-Animate-14B-Q4_K_M.gguf',11496331072),
 'encoder':('.model/wan22-animate-components/umt5-xxl-encoder-Q4_K_M.gguf',3655145312),
 'vision':('.model/wan22-animate-components/split_files/clip_vision/clip_vision_h.safetensors',1264219396),
 'vae':('.model/wan22-animate-components/split_files/vae/wan_2.1_vae.safetensors',253815318),
}
def validate_animate_assets():
 for current_required_path in [ANIMATE_RUNTIME_DIRECTORY/'preprocess/pose2d.py',ANIMATE_RUNTIME_DIRECTORY/'preprocess/human_visualization.py',ANIMATE_RUNTIME_DIRECTORY/'preprocess-deps/onnxruntime/__init__.py',ANIMATE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint/det/yolov10m.onnx']:
  if not current_required_path.is_file():
   raise ValueError(f'Animate 자동 전처리 준비 누락: {current_required_path}')
 import subprocess
 current_pose_bundle=ANIMATE_WORKSPACE_ROOT/'.model/wan22-animate-preprocess/process_checkpoint/pose2d/vitpose_h_wholebody.onnx'
 current_validation_result=subprocess.run([str(ANIMATE_WORKSPACE_ROOT/'.venv/bin/python'),str(Path(__file__).with_name('model_validation.py')),str(current_pose_bundle)],capture_output=True,text=True,timeout=30)
 if current_validation_result.returncode:
  raise ValueError('Animate 포즈 모델 검증 실패: '+current_validation_result.stderr.strip())
 for model_file_name,model_expected_bytes in ANIMATE_MODEL_FILES.values():
  model_file_path=ANIMATE_WORKSPACE_ROOT/model_file_name
  if not model_file_path.is_file() or model_file_path.stat().st_size!=model_expected_bytes:
   raise ValueError(f'Animate 모델 누락 또는 크기 오류: {model_file_path}')
 for runtime_directory_name,runtime_revision_hash in [('ComfyUI','b8730510db30c8858e1e5d8e126ef19eac395560'),('ComfyUI-GGUF','6ea2651e7df66d7585f6ffee804b20e92fb38b8a')]:
  if (ANIMATE_RUNTIME_DIRECTORY/runtime_directory_name/'PINNED_REVISION').read_text().strip()!=runtime_revision_hash:
   raise ValueError('Animate 실행기 리비전 오류')
def validate_animate_request(current_request_record):
 if isinstance(current_request_record,dict) and 'driving_video' in current_request_record:
  from generators.wan_animate.video_input import validate_animation_video_request
  return validate_animation_video_request(current_request_record)
 from tools.review.domains.image.three_reference_generation import decode_reference_image
 required_field_names={'action','prompt','images','width','height','frames','steps','seed','flow_shift','guidance_scale'}
 if not isinstance(current_request_record,dict) or not required_field_names<=set(current_request_record) or set(current_request_record)-required_field_names-{'fps'}:
  raise ValueError('Animate 요청 필드 오류')
 if current_request_record['action']!='generate':
  raise ValueError('generate 요청이 필요합니다.')
 if not isinstance(current_request_record['prompt'],str) or not 1<=len(current_request_record['prompt'].strip())<=8000:
  raise ValueError('프롬프트는 1~8000자여야 합니다.')
 for setting_field_name,setting_minimum_value,setting_maximum_value in [('width',64,1280),('height',64,1280),('frames',1,121),('steps',1,100),('seed',0,4294967295)]:
  if type(current_request_record[setting_field_name]) is not int or not setting_minimum_value<=current_request_record[setting_field_name]<=setting_maximum_value:
   raise ValueError(f'Animate {setting_field_name} 범위: {setting_minimum_value}~{setting_maximum_value}')
 if current_request_record['width']%16 or current_request_record['height']%16 or current_request_record['frames']%4!=1:
  raise ValueError('해상도는 16배수, 프레임은 4n+1이어야 합니다.')
 for setting_field_name,setting_minimum_value,setting_maximum_value in [('flow_shift',0.1,20),('guidance_scale',1,20)]:
  if type(current_request_record[setting_field_name]) not in (int,float) or not math.isfinite(current_request_record[setting_field_name]) or not setting_minimum_value<=current_request_record[setting_field_name]<=setting_maximum_value:
   raise ValueError(f'Animate {setting_field_name} 값 오류')
 current_frame_count=current_request_record['frames']
 current_image_values=current_request_record['images']
 if not isinstance(current_image_values,list) or len(current_image_values) not in (1,1+current_frame_count,1+2*current_frame_count):
  raise ValueError('참조 1장 뒤에 몸 포즈 N장, 선택적으로 얼굴 크롭 N장을 입력하세요.')
 current_output_fps=current_request_record.get('fps',16)
 if type(current_output_fps) is not int or not 1<=current_output_fps<=60:
  raise ValueError('FPS는 1~60 정수여야 합니다.')
 for current_image_index,encoded_image_value in enumerate(current_image_values):
  with Image.open(io.BytesIO(decode_reference_image(encoded_image_value))) as decoded_image_value:
   expected_image_size=(512,512) if current_image_index>current_frame_count else (current_request_record['width'],current_request_record['height'])
   if decoded_image_value.size!=expected_image_size: raise ValueError(f'입력 {current_image_index+1} 크기는 {expected_image_size}이어야 합니다.')
 return {**current_request_record,'fps':current_output_fps,'prompt':current_request_record['prompt'].strip(),'tag':('animate-q4-reference-only' if len(current_image_values)==1 else 'animate-q4-pose-face' if len(current_image_values)==1+2*current_frame_count else 'animate-q4-pose')}
