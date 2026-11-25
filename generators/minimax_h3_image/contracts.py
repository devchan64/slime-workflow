"""Input and local model readiness for the experimental image generator."""
from pathlib import Path
import hashlib

from generators.image.common_art_style import compose_common_style_prompt
from workflow.domains.image.three_reference_generation import validate_three_reference_request
from workflow.common.model_storage_layout import resolve_minimax_snapshot

ROOT = Path(__file__).resolve().parents[2]
STORAGE = ROOT / '.tmp/test/minimax-h3-image'
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
RUNTIME = ROOT / '.local/minimax-h3-diffusers'
BASE = ROOT / '.model/minimax-h3-image'
TRANSFORMER = ROOT / '.model/minimax-h3-image-quant/MiniMax-H3-Image-INT8-ConvRot.safetensors'
ENCODER = ROOT / '.model/minimax-h3-i2v/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
ENCODER_BASE = resolve_minimax_snapshot(ROOT / '.model')
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
    return {'ready': not missing, 'generation_ready': not missing, 'missing': missing,
            'message': ('모델 파일 크기 확인됨 · GPU 실행과 종료 후 메모리 반환 검증 필요'
                        if not missing else '준비 필요: ' + ', '.join(missing))}


def validate_request(request):
    if not isinstance(request, dict):
        raise ValueError('생성 요청은 객체여야 합니다.')
    request = dict(request)
    expected = request.pop('expected_prompt_sha256', None)
    if expected is not None and (not isinstance(expected, str) or len(expected) != 64):
        raise ValueError('프롬프트 확인값 오류')
    result = validate_three_reference_request(request, allowed_inference_steps=(6,), maximum_reference_count=2,
                                              minimum_output_size=480, maximum_output_size=2048)
    if result['width'] % 32 or result['height'] % 32:
        raise ValueError('출력 너비와 높이는 32의 배수여야 합니다.')
    user_prompt = result['prompt'].strip()
    final_prompt, style = compose_common_style_prompt(user_prompt)
    digest = hashlib.sha256(final_prompt.encode('utf-8')).hexdigest()
    if expected is not None and expected != digest:
        raise ValueError('검토 후 공용 화풍 또는 프롬프트가 변경됐습니다. 다시 검토하세요.')
    return {**result, 'user_prompt': user_prompt, 'prompt': final_prompt, 'common_style': style, 'prompt_sha256': digest}


def verify_saved_request(request):
    """Verify the exact submitted style snapshot without substituting a newer style."""
    if 'common_style' not in request:
        raise ValueError('공용 화풍 기록이 없는 이전 실험은 새 실행에 사용할 수 없습니다.')
    style = request['common_style']
    if (not isinstance(style, dict) or set(style) != {'id', 'version', 'source', 'prompt', 'sha256', 'already_present', 'user_prompt'}
            or style['id'] != 'slime_common_art_style' or style['version'] != '1.5.0'
            or style['source'] != 'prompts/common/art-style-v1.5.0.yaml'
            or not isinstance(style['prompt'], str) or type(style['already_present']) is not bool
            or not isinstance(style['user_prompt'], str) or request.get('user_prompt') != style['user_prompt']
            or hashlib.sha256(style['prompt'].encode('utf-8')).hexdigest() != style['sha256']):
        raise ValueError('공용 화풍 입력 기록 오류')
    normalized_prompt = ' '.join(style['user_prompt'].split())
    normalized_style = ' '.join(style['prompt'].split())
    count = normalized_prompt.count(normalized_style) if normalized_style else 0
    if not normalized_style or count > 1 or bool(count) != style['already_present']:
        raise ValueError('공용 화풍 중복 기록 오류')
    expected_prompt = style['user_prompt'].strip() if count else ' '.join((style['user_prompt'].strip(), style['prompt']))
    if request.get('prompt') != expected_prompt:
        raise ValueError('최종 프롬프트와 화풍 기록이 일치하지 않습니다.')
    if request.get('prompt_sha256') != hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest():
        raise ValueError('최종 프롬프트 무결성 오류')
