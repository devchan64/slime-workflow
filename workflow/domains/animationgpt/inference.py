"""AnimationGPT 제작자 방식 CPU 추론과 22관절 좌표 검증."""
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


def motion_decoder_constraints(tokenizer, decoder_start_id, codebook_size=512):
    """모션 시작·코드·종료만 허용한다. 종료되지 않은 출력은 호출자가 거절한다."""
    names = [f'<motion_id_{i}>' for i in range(codebook_size + 2)]
    ids = [tokenizer.convert_tokens_to_ids(name) for name in names]
    if any(type(value) is not int or value < 0 for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('모션 토큰 등록을 확인할 수 없습니다.')
    if any(tokenizer.convert_ids_to_tokens(value) != name for name, value in zip(names, ids)):
        raise ValueError('모션 토큰과 토크나이저가 일치하지 않습니다.')
    if type(decoder_start_id) is not int or decoder_start_id in ids:
        raise ValueError('디코더 시작 토큰을 확인할 수 없습니다.')
    codes, start, end = ids[:codebook_size], ids[codebook_size], ids[codebook_size+1]
    def allowed(_batch_id, output_ids):
        # 첫 코드까지는 종료를 금지해 빈 모션이 나오지 않게 한다.
        return codes if len(output_ids) <= 2 else [*codes, end]
    return [decoder_start_id, start], end, allowed


def author_t5_root(root):
    """Prefer the independent model installation; retain the legacy fallback."""
    root = Path(root)
    current = root / '.model/flan-t5-base'
    if current.exists() or current.is_symlink():
        if current.is_symlink() or not current.is_dir():
            raise ValueError('FLAN-T5 모델 경로를 확인할 수 없습니다.')
        return current
    return root / '.local/animationgpt-legacy/flan-t5-base'


def generate_motion(prompt, seed, source_root, model_root, *, max_tokens=256):
    """제작자 데모의 비제약 샘플링을 별도 Python 3.10 CPU 프로세스에서 실행한다."""
    import hashlib
    import sys
    import types
    import numpy as np
    import torch
    import transformers
    from safetensors.torch import load_file

    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        raise ValueError('프롬프트는 1~2000자여야 합니다.')
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError('시드 범위 오류')
    if type(max_tokens) is not int or not 8 <= max_tokens <= 256:
        raise ValueError('최대 토큰 범위 오류')
    if sys.version_info[:2] != (3, 10) or not torch.__version__.startswith('2.0.1') or transformers.__version__ != '4.38.2':
        raise RuntimeError('AnimationGPT 제작자 방식에는 준비된 Python 3.10, PyTorch 2.0.1, Transformers 4.38.2 환경이 필요합니다.')

    root = Path(__file__).resolve().parents[3]
    source_root, model_root = Path(source_root).resolve(), Path(model_root).resolve()
    author_weights = root / '.model/animationgpt-author/AnimationGPT_fp16.safetensors'
    t5_root = author_t5_root(root)
    expected = ((author_weights, '80d822c7c34faf075d93a8b605569142a7d97e9feb31972a94fb9968621aaa6b'),
                (t5_root / 'model.safetensors', '1dfb70afdcedceb9f9fae2f9b68e004ad934361fb35b9b2bd50b45ea90790fc8'))
    for path, digest in expected:
        if not path.is_file():
            raise FileNotFoundError(f'제작자 방식 모델 파일이 없습니다: {path}')
        with path.open('rb') as stream:
            actual = hashlib.sha256()
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                actual.update(block)
        if actual.hexdigest() != digest:
            raise ValueError(f'제작자 방식 모델 파일 해시가 다릅니다: {path}')
    sys.path.insert(0, str(source_root))
    from mGPT.archs.mgpt_lm import MLM
    from mGPT.archs.mgpt_vq import VQVae
    if 'mGPT.data' in sys.modules or 'mGPT.data.humanml' in sys.modules:
        raise RuntimeError('격리된 새 프로세스에서만 추론할 수 있습니다.')
    for name, path in [('mGPT.data', source_root/'mGPT/data'), ('mGPT.data.humanml', source_root/'mGPT/data/humanml')]:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    from mGPT.data.humanml.scripts.motion_process import recover_from_ric

    torch.set_num_threads(4)
    torch.manual_seed(seed)
    state = load_file(str(author_weights), device='cpu')
    vae = VQVae(nfeats=263, quantizer='ema_reset', code_num=512, code_dim=512,
                 output_emb_width=512, down_t=2, stride_t=2, width=512, depth=3,
                 dilation_growth_rate=3, norm=None, activation='relu')
    lm = MLM(model_path=str(t5_root), motion_codebook_size=512, stage='lm_instruct')
    for label, module in [('lm', lm), ('vae', vae)]:
        module.load_state_dict({key[len(label)+1:]: value for key, value in state.items() if key.startswith(label+'.')}, strict=True)
        module.eval()
    del state
    # 공식 demo.py는 입력 줄을 그대로 전달한다. 경계 누락의 0번 토큰 대체는 거부한다.
    encoding = lm.tokenizer([prompt.strip() + '\n'], padding='max_length', max_length=lm.max_length,
                            truncation=True, return_attention_mask=True, add_special_tokens=True, return_tensors='pt')
    if not torch.isfinite(lm.language_model.shared.weight).all() or not torch.isfinite(lm.language_model.lm_head.weight).all():
        raise ValueError('언어 모델에 비유한 가중치가 있습니다.')
    with torch.inference_mode():
        output = lm.language_model.generate(encoding.input_ids, max_length=max_tokens, num_beams=1,
                                            do_sample=True, bad_words_ids=None)
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
    return joints[0].cpu().numpy(), {'seed': seed, 'prompt': prompt, 'motion_tokens': len(codes),
        'frames': joints.shape[1], 'fps': 20, 'source_revision': MOTIONGPT_REVISION, 'weapon_track': False,
        'decoding': 'author-unconstrained-strict-validation-v1', 'device': 'cpu', 'dtype': 'float32',
        'python': sys.version.split()[0], 'torch': torch.__version__, 'transformers': transformers.__version__,
        'attention': 'T5 eager matmul-softmax; SDPA not used', 'author_weights_sha256': expected[0][1],
        'flan_weights_sha256': expected[1][1], 'max_tokens': max_tokens,
        'validation': 'finite shared/lm-head weights, decoded features, statistics and joints; intermediate attention not checked'}
