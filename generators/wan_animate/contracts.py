"""Wan2.2 Animate Q4 실험 입력 계약. 모델은 코드로 고정한다."""
from pathlib import Path
import io
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
 for model_file_name,model_expected_bytes in ANIMATE_MODEL_FILES.values():
  model_file_path=ANIMATE_WORKSPACE_ROOT/model_file_name
  if not model_file_path.is_file() or model_file_path.stat().st_size!=model_expected_bytes:
   raise ValueError(f'Animate 모델 누락 또는 크기 오류: {model_file_path}')
 for runtime_directory_name,runtime_revision_hash in [('ComfyUI','b8730510db30c8858e1e5d8e126ef19eac395560'),('ComfyUI-GGUF','6ea2651e7df66d7585f6ffee804b20e92fb38b8a')]:
  if (ANIMATE_RUNTIME_DIRECTORY/runtime_directory_name/'PINNED_REVISION').read_text().strip()!=runtime_revision_hash:
   raise ValueError('Animate 실행기 리비전 오류')
def validate_animate_request(current_request_record):
 from tools.review.domains.image.three_reference_generation import decode_reference_image
 required_field_names={'action','prompt','images','width','height','frames','steps','seed','flow_shift','guidance_scale'}
 if not isinstance(current_request_record,dict) or set(current_request_record)!=required_field_names:
  raise ValueError('Animate 요청 필드 오류')
 if current_request_record['action']!='generate':
  raise ValueError('generate 요청이 필요합니다.')
 if not isinstance(current_request_record['prompt'],str) or not 1<=len(current_request_record['prompt'].strip())<=8000:
  raise ValueError('프롬프트는 1~8000자여야 합니다.')
 for setting_field_name,setting_expected_value in [('width',832),('height',480),('frames',21),('steps',20),('seed',42)]:
  if type(current_request_record[setting_field_name]) is not int or current_request_record[setting_field_name]!=setting_expected_value:
   raise ValueError(f'최초 Animate 실험의 {setting_field_name}는 {setting_expected_value}로 고정합니다.')
 for setting_field_name,setting_expected_value in [('flow_shift',5.0),('guidance_scale',1.0)]:
  if type(current_request_record[setting_field_name]) not in (int,float) or current_request_record[setting_field_name]!=setting_expected_value:
   raise ValueError(f'Animate {setting_field_name} 값 오류')
 if not isinstance(current_request_record['images'],list) or len(current_request_record['images']) not in (1,22):
  raise ValueError('참조 1장 또는 참조와 몸 포즈 21장을 입력하세요. 얼굴 영상은 사용하지 않습니다.')
 for encoded_image_value in current_request_record['images']:
  with Image.open(io.BytesIO(decode_reference_image(encoded_image_value))) as decoded_image_value:
   expected_image_size=(832,480)
   if decoded_image_value.size!=expected_image_size: raise ValueError(f'입력 이미지 크기는 {expected_image_size}이어야 합니다.')
 return {**current_request_record,'prompt':current_request_record['prompt'].strip(),'tag':('animate-q4-reference-only' if len(current_request_record['images'])==1 else 'animate-q4-anny-light-armor')}
