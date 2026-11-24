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
    from generators.minimax_h3_image.contracts import verify_saved_request
    from workflow.domains.image.three_reference_generation import validate_three_reference_request
    if 'common_style' in request:
        verify_saved_request(request)
    elif any(key in request for key in ('user_prompt', 'prompt_sha256')):
        raise ValueError('공용 화풍 입력 기록이 불완전합니다.')
    else:
        # Existing queued jobs predate common-style metadata; preserve their input.
        request['user_prompt'] = request['prompt']
        request['prompt_sha256'] = hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest()
    validate_three_reference_request({key: request[key] for key in ('action', 'width', 'height', 'steps', 'seed', 'tag')}
        | {'prompt': request['user_prompt'], 'images': []}, allowed_inference_steps=(6,), maximum_reference_count=0,
        minimum_output_size=512, maximum_output_size=2048)
    if request['width'] % 32 or request['height'] % 32:
        raise ValueError('출력 크기는 32의 배수여야 합니다.')
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
        h3_image_prepare_prequant_model, load_h3_image_vae, install_h3_image_forward,
        install_pdd_head_bank, MiniMaxH3ImagePipeline, MiniMaxH3ImageScheduler, H3_IMAGE_SIGMAS)
    from transformers import AutoTokenizer
    helper.hf_hub_download_with_xet_fallback = lambda *args, **kwargs: str(ENCODER)
    os.environ['UNSLOTH_ALLOW_LOCAL_PREQUANT_PATH'] = str(TRANSFORMER.parent)
    encoder = load_h3_quantized_text_encoder(str(ENCODER_BASE), 'int8', dtype=torch.bfloat16,
                                             local_base=str(ENCODER_BASE), local_files_only=True)
    if encoder is None:
        raise RuntimeError('INT8 텍스트 인코더 적재 실패')
    encoder._apply(lambda value: value.clone().to('cuda') if value.device.type == 'cpu' else value.to('cuda'))
    if any(value.device.type != 'cuda' for value in list(encoder.parameters()) + list(encoder.buffers())):
        raise RuntimeError('텍스트 인코더 GPU 적재 확인 실패')
    transformer = load_prequantized_transformer(native_config_transformer_class(), str(BASE),
        PrequantSource(kind='path', location=str(TRANSFORMER)), device='cuda', dtype=torch.bfloat16,
        scheme='int8', prepare_model=h3_image_prepare_prequant_model(), local_files_only=True,
        placement_device='cuda', family='minimax-h3-image')
    if transformer is None:
        raise RuntimeError('INT8 이미지 모델 적재 실패; 다른 정밀도로 전환하지 않습니다.')
    if any(value.device.type != 'cuda' for value in list(transformer.parameters()) + list(transformer.buffers())):
        raise RuntimeError('이미지 모델 GPU 적재 확인 실패')
    install_h3_image_forward(transformer)
    install_pdd_head_bank(transformer)
    vae = load_h3_image_vae(BASE).to('cuda')
    tokenizer = AutoTokenizer.from_pretrained(str(BASE / 'tokenizer'), local_files_only=True)
    pipe = MiniMaxH3ImagePipeline(transformer=transformer, vae=vae, text_encoder=encoder,
        tokenizer=tokenizer, scheduler=MiniMaxH3ImageScheduler(sample_sigmas=list(H3_IMAGE_SIGMAS)))
    pipe._unsloth_h3_device = 'cuda'
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
        'height': request['height'], 'steps': 6, 'weights': checksums, 'prompt_sha256': request['prompt_sha256'],
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
