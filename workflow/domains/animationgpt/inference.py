"""AnimationGPT 추론 준비: 22관절 좌표만 반환하며 서비스·GPU 대기열에 연결되지 않았다."""
import re
from pathlib import Path

MOTIONGPT_REVISION = '001aaca8d0ee218fc17f8265d11ac124044fe42f'


def parse_motion_tokens(text, codebook_size=512):
    """공식 경계가 없는 출력은 0번 모션으로 조용히 대체하지 않는다."""
    start = f'<motion_id_{codebook_size}>'
    end = f'<motion_id_{codebook_size + 1}>'
    if not isinstance(text, str) or text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('모션 시작·종료 토큰이 없거나 중복되었습니다.')
    middle = text.split(start, 1)[1].split(end, 1)[0]
    matches = re.findall(r'<motion_id_(\d+)>', middle)
    if not matches or ''.join(f'<motion_id_{value}>' for value in matches) != middle:
        raise ValueError('모션 토큰 시퀀스가 비어 있거나 손상되었습니다.')
    tokens = [int(value) for value in matches]
    if any(token >= codebook_size for token in tokens):
        raise ValueError('모션 코드북 범위를 벗어났습니다.')
    return tokens


def generate_motion(prompt, seed, source_root, model_root, *, max_tokens=160):
    """격리된 CPU 프로세스 전용 실험 추론. 생성 품질·무기 데이터는 보장하지 않는다."""
    import sys
    import types
    import numpy as np
    import torch
    from safetensors.torch import load_file
    from transformers import T5Config, T5ForConditionalGeneration
    from unittest.mock import patch

    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        raise ValueError('프롬프트는 1~2000자여야 합니다.')
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError('시드 범위 오류')
    if type(max_tokens) is not int or not 8 <= max_tokens <= 256:
        raise ValueError('최대 토큰 범위 오류')
    source_root = Path(source_root).resolve()
    model_root = Path(model_root).resolve()
    sys.path.insert(0, str(source_root))
    from mGPT.archs.mgpt_lm import MLM
    from mGPT.archs.mgpt_vq import VQVae
    # 상위 data 패키지의 훈련 전용 Lightning 의존성을 초기화하지 않는다.
    if 'mGPT.data' in sys.modules or 'mGPT.data.humanml' in sys.modules:
        raise RuntimeError('격리된 새 프로세스에서만 추론할 수 있습니다.')
    for name, path in [('mGPT.data', source_root/'mGPT/data'), ('mGPT.data.humanml', source_root/'mGPT/data/humanml')]:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    from mGPT.data.humanml.scripts.motion_process import recover_from_ric

    torch.set_num_threads(4)
    torch.manual_seed(seed)
    state = load_file(str(model_root/'AnimationGPT_fp16.safetensors'), device='cpu')

    def build_t5(path):
        config = T5Config.from_pretrained(path, local_files_only=True)
        # Transformers 5는 원본의 false 설정을 덮어쓸 수 있다. 체크포인트의 두 행렬은 다르다.
        config.tie_word_embeddings = False
        return T5ForConditionalGeneration(config)

    with patch.object(T5ForConditionalGeneration, 'from_pretrained', side_effect=build_t5):
        lm = MLM(model_path=str(model_root/'flan-t5-base'), motion_codebook_size=512)
    vae = VQVae(nfeats=263, quantizer='ema_reset', code_num=512, code_dim=512,
                 output_emb_width=512, down_t=2, stride_t=2, width=512, depth=3,
                 dilation_growth_rate=3, norm=None, activation='relu')
    for label, model in [('lm', lm), ('vae', vae)]:
        model.load_state_dict({key[len(label)+1:]: value for key, value in state.items() if key.startswith(label+'.')}, strict=True)
        model.eval()
    del state
    # 원본 generate_direct는 경계가 없으면 가짜 [0]을 반환하므로 원문을 직접 검증한다.
    text = f'Generate a motion that depicts {prompt.strip()}'
    encoding = lm.tokenizer([text], padding='max_length', max_length=lm.max_length,
                            truncation=True, return_tensors='pt')
    if not torch.isfinite(lm.language_model.shared.weight).all() or not torch.isfinite(lm.language_model.lm_head.weight).all():
        raise ValueError('언어 모델에 비유한 가중치가 있습니다.')
    with torch.inference_mode():
        output = lm.language_model.generate(encoding.input_ids, max_length=max_tokens, do_sample=True)
        decoded = lm.tokenizer.batch_decode(output, skip_special_tokens=True)[0]
        codes = parse_motion_tokens(decoded)
        features = vae.decode(torch.tensor(codes, dtype=torch.long))
        if not torch.isfinite(features).all():
            raise ValueError('모션 특징에 비유한 값이 있습니다.')
        mean = torch.tensor(np.load(model_root/'motion-stats/mean.npy', allow_pickle=False), dtype=features.dtype)
        std = torch.tensor(np.load(model_root/'motion-stats/std.npy', allow_pickle=False), dtype=features.dtype)
        if mean.shape != (263,) or std.shape != (263,) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
            raise ValueError('정규화 통계 오류')
        joints = recover_from_ric(features * std + mean, 22)
        if not torch.isfinite(joints).all() or joints.ndim != 4 or joints.shape[0] != 1 or joints.shape[2:] != (22, 3):
            raise ValueError('생성된 관절 좌표 오류')
    return joints[0].cpu().numpy(), {'seed': seed, 'prompt': prompt, 'motion_tokens': len(codes), 'frames': joints.shape[1], 'fps': 20, 'source_revision': MOTIONGPT_REVISION, 'weapon_track': False}
