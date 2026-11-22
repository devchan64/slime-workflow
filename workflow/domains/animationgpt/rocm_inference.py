"""AnimationGPT ROCm 추론. 공용 GPU 작업자 안에서만 호출한다."""
import os
import sys
import types
from pathlib import Path

from workflow.domains.animationgpt.inference import parse_motion_tokens


def require_rocm(torch):
    if not getattr(torch.version, 'hip', None):
        raise RuntimeError('AnimationGPT에는 ROCm PyTorch가 필요합니다. CPU 또는 NVIDIA 추론으로 대체하지 않습니다.')
    if not torch.cuda.is_available():
        raise RuntimeError('AnimationGPT ROCm GPU를 사용할 수 없습니다.')
    if not os.environ.get('SLIME_GPU_QUEUE_TICKET'):
        raise RuntimeError('AnimationGPT 추론은 공용 GPU 대기열에서만 실행할 수 있습니다.')


def generate_rocm(prompt, seed, source_root, model_root):
    """원본 무제약 샘플링과 엄격한 모션 경계 검증; 입력과 출력을 GPU에서 계산한다."""
    import numpy as np
    import torch
    import transformers
    from safetensors.torch import load_file
    from transformers import T5Config, T5ForConditionalGeneration
    from unittest.mock import patch

    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        raise ValueError('프롬프트는 1~2000자여야 합니다.')
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError('시드 범위 오류')
    require_rocm(torch)
    root = Path(source_root).resolve(); model_root = Path(model_root).resolve()
    sys.path.insert(0, str(root))
    from mGPT.archs.mgpt_lm import MLM
    from mGPT.archs.mgpt_vq import VQVae
    if 'mGPT.data' in sys.modules or 'mGPT.data.humanml' in sys.modules:
        raise RuntimeError('격리된 새 프로세스에서만 추론할 수 있습니다.')
    for name, path in [('mGPT.data', root/'mGPT/data'), ('mGPT.data.humanml', root/'mGPT/data/humanml')]:
        module = types.ModuleType(name); module.__path__ = [str(path)]; sys.modules[name] = module
    from mGPT.data.humanml.scripts.motion_process import recover_from_ric
    torch.manual_seed(seed)
    state = load_file(str(model_root/'AnimationGPT_fp16.safetensors'), device='cpu')
    vae = VQVae(nfeats=263, quantizer='ema_reset', code_num=512, code_dim=512,
                 output_emb_width=512, down_t=2, stride_t=2, width=512, depth=3,
                 dilation_growth_rate=3, norm=None, activation='relu')
    def config_model(path):
        config = T5Config.from_pretrained(path, local_files_only=True); config.tie_word_embeddings = False
        return T5ForConditionalGeneration(config)
    with patch.object(T5ForConditionalGeneration, 'from_pretrained', side_effect=config_model):
        lm = MLM(model_path=str(model_root/'flan-t5-base'), motion_codebook_size=512, stage='lm_instruct')
    for label, module in [('lm', lm), ('vae', vae)]:
        module.load_state_dict({k[len(label)+1:]: v for k,v in state.items() if k.startswith(label+'.')}, strict=True)
        module.to('cuda').eval()
    del state
    counts = {'attention_outputs': 0}
    def inspect_attention(_module, _inputs, output):
        value = output[0] if isinstance(output, tuple) else output
        if not torch.isfinite(value).all():
            raise ValueError('T5 어텐션 출력에 NaN 또는 무한대가 있습니다.')
        counts['attention_outputs'] += 1
    hooks = [module.register_forward_hook(inspect_attention) for module in lm.modules() if module.__class__.__name__ == 'T5Attention']
    try:
        encoded = lm.tokenizer([prompt.strip() + '\n'], padding='max_length', max_length=lm.max_length,
                               truncation=True, return_attention_mask=True, add_special_tokens=True, return_tensors='pt')
        with torch.inference_mode():
            output = lm.language_model.generate(encoded.input_ids.to('cuda'), max_length=256, num_beams=1,
                                                 do_sample=True, bad_words_ids=None, return_dict_in_generate=True,
                                                 output_scores=True)
            if not counts['attention_outputs']:
                raise RuntimeError('T5 어텐션 검사가 실행되지 않았습니다.')
            if any(not torch.isfinite(scores).all() for scores in output.scores):
                raise ValueError('생성 점수에 NaN 또는 무한대가 있습니다.')
            decoded = lm.tokenizer.batch_decode(output.sequences, skip_special_tokens=True)[0]
            codes = parse_motion_tokens(decoded)
            features = vae.decode(torch.tensor(codes, device='cuda', dtype=torch.long))
            if not torch.isfinite(features).all(): raise ValueError('모션 특징에 비유한 값이 있습니다.')
            mean = torch.as_tensor(np.load(model_root/'motion-stats/mean.npy', allow_pickle=False), device='cuda', dtype=features.dtype)
            std = torch.as_tensor(np.load(model_root/'motion-stats/std.npy', allow_pickle=False), device='cuda', dtype=features.dtype)
            if mean.shape != (263,) or std.shape != (263,) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
                raise ValueError('정규화 통계 오류')
            joints = recover_from_ric(features * std + mean, 22)
            if not torch.isfinite(joints).all() or joints.ndim != 4 or joints.shape[0] != 1 or joints.shape[2:] != (22, 3):
                raise ValueError('생성 관절 오류')
            return joints[0].cpu().numpy(), {'seed':seed,'prompt':prompt,'frames':joints.shape[1],'fps':20,
                'motion_tokens':len(codes),'device':torch.cuda.get_device_name(0),'hip':torch.version.hip,
                'torch':torch.__version__,'transformers':transformers.__version__,'attention_checks':counts,
                'decoding':'unconstrained-strict','weapon_track':False}
    finally:
        for hook in hooks: hook.remove()
