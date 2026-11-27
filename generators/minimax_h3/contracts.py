"""MiniMax H3 I2V의 입력 및 준비 상태 계약."""
from pathlib import Path
import io
from PIL import Image
from workflow.domains.image.three_reference_generation import decode_reference_image
from generators.minimax_h3.assets import FILES, current_files
from workflow.common.model_storage_layout import resolve_minimax_snapshot

ROOT = Path(__file__).resolve().parents[2]
JOB_STORAGE = ROOT / '.tmp/test/minimax-h3-i2v'
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
RUNTIME = ROOT / '.local/minimax-h3-diffusers'
REVISION = 'e9e031d2fabec27d62269623737fbc0ba611862c'


def inspect_runtime():
    missing=[]
    try:
        records = current_files(FILES)
    except ValueError as error:
        return {'ready': False, 'missing': [str(error)], 'message': '준비 필요: '+str(error)}
    for path,size,_ in records:
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            missing.append(path.name)
    for path in (PYTHON,RUNTIME/'deps/diffusers/__init__.py',RUNTIME/'deps/accelerate/__init__.py',
                 RUNTIME/'deps/torchao/__init__.py',RUNTIME/'backend/core/inference/video_minimax_h3_te.py',
                 RUNTIME/'backend/core/inference/diffusion_comfy_quant.py',
                 ROOT/'.model/minimax-h3-diffusers/vae/config.json',
                 ROOT/'.model/minimax-h3-diffusers/vae/diffusion_pytorch_model.safetensors.index.json',
                 ROOT/'.model/minimax-h3-diffusers/audio_vae/config.json'):
        if not path.is_file(): missing.append(path.name)
    try:
        if (RUNTIME/'UNSLOTH_REVISION').read_text().strip()!=REVISION: missing.append('변환 로더 리비전')
    except OSError:
        missing.append('변환 로더 리비전')
    snapshot=resolve_minimax_snapshot(ROOT / '.model')
    for relative in ('modular_model_index.json','transformer/config.json','text_encoder/config.json','processor/preprocessor_config.json','tokenizer/tokenizer.json','scheduler/scheduler_config.json','audio_scheduler/scheduler_config.json'):
        if not (snapshot/relative).is_file(): missing.append(relative)
    return {'ready':not missing,'missing':missing,'message':'Diffusers I2V 파일 준비 완료 · 실행 시 SHA-256 검증' if not missing else '준비 필요: '+', '.join(missing)}


def validate_request(request):
    if not isinstance(request,dict) or set(request) not in ({'action','prompt','images','width','height','frames','steps','seed'}, {'action','prompt','images','width','height','frames','steps','seed','mode'}) or request.get('action')!='generate':
        raise ValueError('MiniMax H3 요청 필드가 올바르지 않습니다.')
    if not isinstance(request['prompt'],str) or not request['prompt'].strip() or len(request['prompt'])>8000:
        raise ValueError('동작 프롬프트를 1~8000자로 입력하세요.')
    if (type(request['width']) is not int or type(request['height']) is not int
            or (request['width'],request['height']) not in {(832,480),(768,448)}
            or type(request['frames']) is not int or request['frames'] not in range(124, 346, 17)
            or type(request['steps']) is not int or request['steps'] != 8):
        raise ValueError('832×480 또는 기존 768×448, 124~345프레임(17프레임 간격) · 8스텝 설정을 사용하세요.')
    if type(request['seed']) is not int or not 0<=request['seed']<=2147483647:
        raise ValueError('시드는 0~2147483647의 정수여야 합니다.')
    mode=request.get('mode','first')
    counts={'text':0,'first':1,'last':1,'first_last':2}
    if mode not in counts or not isinstance(request['images'],list) or len(request['images'])!=counts[mode]:
        raise ValueError('생성 모드에 맞는 참조 이미지 수를 확인하세요.')
    for encoded in request['images']:
        with Image.open(io.BytesIO(decode_reference_image(encoded))) as image:
            if image.size!=(832,480): raise ValueError('참조 이미지는 832×480이어야 합니다.')
    return {**request,'prompt':request['prompt'].strip(),'tag':'minimax-h3-i2v'}
