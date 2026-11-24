"""Input and local model readiness for the experimental image generator."""
from pathlib import Path

from workflow.domains.image.three_reference_generation import validate_three_reference_request

ROOT = Path(__file__).resolve().parents[2]
STORAGE = ROOT / '.tmp/test/minimax-h3-image'
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
RUNTIME = ROOT / '.local/minimax-h3-diffusers'
BASE = ROOT / '.model/minimax-h3-image'
TRANSFORMER = ROOT / '.model/minimax-h3-image-quant/MiniMax-H3-Image-INT8-ConvRot.safetensors'
ENCODER = ROOT / '.model/minimax-h3-i2v/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
ENCODER_BASE = ROOT / '.model/huggingface/hub/models--MiniMaxAI--MiniMax-H3/snapshots/1cc7549f2cf0af8ff2f09b24f3c57303c8aa6317'
FILES = ((TRANSFORMER, 20272349984), (ENCODER, 27141342152),
         (BASE / 'vae/diffusion_pytorch_model.safetensors', 2336964672))


def inspect_runtime():
    missing = [str(path.relative_to(ROOT)) for path, size in FILES
               if path.is_symlink() or not path.is_file() or path.stat().st_size != size]
    for path in (PYTHON, RUNTIME / 'backend/core/inference/diffusion_minimax_h3_image.py',
                 BASE / 'model_index.json', BASE / 'pdd_config.json', BASE / 'transformer/config.json',
                 BASE / 'vae/config.json', BASE / 'tokenizer/tokenizer.json',
                 BASE / 'processor/preprocessor_config.json', ENCODER_BASE / 'text_encoder/config.json'):
        if not path.is_file():
            missing.append(str(path.relative_to(ROOT)))
    return {'ready': not missing, 'generation_ready': False, 'missing': missing,
            'message': ('모델 파일 크기는 확인됐지만 비상주 스트리밍 및 메모리 검증 전에는 실행할 수 없습니다.'
                        if not missing else '준비 필요: ' + ', '.join(missing))}


def validate_request(request):
    result = validate_three_reference_request(request, allowed_inference_steps=(6,), maximum_reference_count=0,
                                              minimum_output_size=1024, maximum_output_size=2048)
    if result['width'] % 32 or result['height'] % 32:
        raise ValueError('출력 너비와 높이는 32의 배수여야 합니다.')
    return {**result, 'prompt': result['prompt'].strip()}
