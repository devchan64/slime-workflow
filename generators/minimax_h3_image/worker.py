"""Run a MiniMax H3 Image job inside the common GPU queue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / '.local/minimax-h3-diffusers/deps'), str(ROOT / '.local/minimax-h3-diffusers/backend')]
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:False'
os.environ.pop('PYTORCH_CUDA_ALLOC_CONF', None)

from generators.minimax_h3_image.contracts import BASE, ENCODER, ENCODER_BASE, FILES, STORAGE, TRANSFORMER, inspect_runtime
from workflow.common.generation_records import write_record_atomically
from workflow.common.worker_generation_progress import WorkerGenerationProgress


def execute(job):
    job = Path(job)
    if job.is_symlink() or job.resolve().parent != STORAGE.resolve():
        raise ValueError('이미지 작업 경로 오류')
    request = json.loads((job / 'request.json').read_text())
    from generators.minimax_h3_image.contracts import validate_request
    validate_request({key: request[key] for key in ('action', 'prompt', 'width', 'height', 'steps', 'seed', 'tag')} | {'images': []})
    status = inspect_runtime()
    if not status['generation_ready']:
        raise ValueError(status['message'])
    checksums = {}
    for path, size in FILES:
        if path.is_symlink() or path.stat().st_size != size:
            raise ValueError('모델 파일이 변경됐습니다: ' + path.name)
        with path.open('rb') as stream:
            checksums[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    if checksums[TRANSFORMER.name] != 'b4d94247ec1292f3fb9aafc738c8eb5961b63685f19f5e5275630b53721e8da5':
        raise ValueError('INT8 이미지 모델 SHA-256 불일치')
    if checksums[ENCODER.name] != 'bc2ced0fbea64757fa9acddccfc0b3f4819d1dcf1da6c124d690d368be283923':
        raise ValueError('INT8 텍스트 인코더 SHA-256 불일치')
    if checksums['diffusion_pytorch_model.safetensors'] != 'a7c8bb1e181865e7cf87c29d3d6bc728d944ce4862b92d0e1cbdcc36b3b180b2':
        raise ValueError('이미지 VAE SHA-256 불일치')
    import torch
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('ROCm GPU를 사용할 수 없습니다.')
    import utils.hf_xet_fallback as helper
    from core.inference.video_minimax_h3_te import load_h3_quantized_text_encoder
    from core.inference.diffusion_prequant import PrequantSource, load_prequantized_transformer
    from core.inference.diffusion_minimax_h3_image import (native_config_transformer_class,
        h3_image_prepare_prequant_model, load_minimax_h3_image_pipeline)
    helper.hf_hub_download_with_xet_fallback = lambda *args, **kwargs: str(ENCODER)
    os.environ['UNSLOTH_ALLOW_LOCAL_PREQUANT_PATH'] = str(TRANSFORMER.parent)
    encoder = load_h3_quantized_text_encoder(str(ENCODER_BASE), 'int8', dtype=torch.bfloat16,
                                             local_base=str(ENCODER_BASE), local_files_only=True)
    if encoder is None:
        raise RuntimeError('INT8 텍스트 인코더 적재 실패')
    transformer = load_prequantized_transformer(native_config_transformer_class(), str(BASE),
        PrequantSource(kind='path', location=str(TRANSFORMER)), device='cuda', dtype=torch.bfloat16,
        scheme='int8', prepare_model=h3_image_prepare_prequant_model(), local_files_only=True,
        placement_device='cpu', family='minimax-h3-image')
    if transformer is None:
        raise RuntimeError('INT8 이미지 모델 적재 실패; 다른 정밀도로 전환하지 않습니다.')
    os.environ['UNSLOTH_H3_IMAGE_PLACEMENT'] = 'stream'
    pipe = load_minimax_h3_image_pipeline(str(BASE), dtype=torch.bfloat16, device='cuda',
        transformer_quant='int8', text_encoder_quant='int8', text_encoder=encoder, transformer=transformer,
        local_files_only=True, plan_width=request['width'], plan_height=request['height'])
    if pipe._unsloth_h3_plan.placement != 'stream':
        raise RuntimeError('요청한 스트리밍 배치가 적용되지 않았습니다.')
    def check(module, args, output):
        def visit(value):
            if torch.is_tensor(value) and not torch.isfinite(value).all().item():
                raise ValueError('모델 출력에 NaN 또는 무한대가 있습니다.')
            if isinstance(value, (tuple, list)):
                for item in value: visit(item)
        visit(output)
    hook = transformer.register_forward_hook(check)
    progress = WorkerGenerationProgress(job)
    progress.record_worker_progress({'stage': 'inference', 'step': 0, 'total': 6})
    def on_step(_pipe, index, _timestep, payload):
        for value in payload.values():
            if torch.is_tensor(value) and not torch.isfinite(value).all().item():
                raise ValueError('잠재값에 NaN 또는 무한대가 있습니다.')
        progress.record_worker_progress({'stage': 'inference', 'step': index + 1, 'total': 6})
        print(f'stage=inference step={index + 1}/6', flush=True)
        return payload
    with torch.inference_mode():
        image = pipe(prompt=request['prompt'], width=request['width'], height=request['height'],
                     num_inference_steps=6, generator=torch.Generator('cpu').manual_seed(request['seed']),
                     callback_on_step_end=on_step).images[0]
    hook.remove()
    image.save(job / 'result.png')
    write_record_atomically(job / 'result.json', {'seed': request['seed'], 'width': request['width'],
        'height': request['height'], 'steps': 6, 'weights': checksums,
        'image_sha256': hashlib.sha256((job / 'result.png').read_bytes()).hexdigest(),
        'torch': str(torch.__version__), 'hip': torch.version.hip, 'gpu': torch.cuda.get_device_name(0),
        'allocator': os.environ['PYTORCH_ALLOC_CONF'], 'sdpa': '기본 경로; 정확도 미검증',
        'quality_status': '사용자 검수 대기'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--job-dir', required=True)
    job = Path(parser.parse_args().job_dir)
    try:
        execute(job)
        write_record_atomically(job / 'status.json', {'status': 'completed', 'image': f'/minimax-h3-image/jobs/{job.name}/result.png'})
    except BaseException as error:
        traceback.print_exc()
        write_record_atomically(job / 'status.json', {'status': 'failed', 'error': str(error)})
        raise
