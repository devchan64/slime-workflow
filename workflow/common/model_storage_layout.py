"""Resolve legacy and reorganized installations without moving model data."""
from pathlib import Path

MINIMAX_SNAPSHOT = 'hub/models--MiniMaxAI--MiniMax-H3/snapshots/1cc7549f2cf0af8ff2f09b24f3c57303c8aa6317'


def _resolve(root, old, new, *, default_new=False):
    root = Path(root)
    legacy = root / old
    modern = root / new
    # Keep the current installation authoritative until an explicit move.
    # A link at either level is not accepted as a new installation.
    if legacy.exists() or legacy.is_symlink():
        return legacy
    if modern.is_dir() and not any(path.is_symlink() for path in (modern, modern.parent)):
        return modern
    # During flattening, prefer the existing nested installation until it has
    # actually been moved. Do not follow a link at any new path component.
    if new.startswith('models/'):
        flattened = root / new.removeprefix('models/')
        parts = flattened.relative_to(root).parts
        ancestors = [root.joinpath(*parts[:index]) for index in range(1, len(parts) + 1)]
        if flattened.is_dir() and not any(path.is_symlink() for path in ancestors):
            return flattened
    if default_new and not modern.exists() and not modern.is_symlink() and not modern.parent.is_symlink():
        if new.startswith('models/') and not modern.parent.exists():
            return root / new.removeprefix('models/')
        return modern
    return legacy


def resolve_hermes_model_directory(root):
    root = Path(root)
    existing = _resolve(root, 'hermes-agent', 'models/hermes-coding')
    named = root/'qwen3.8-27b-iq4-xs'
    if named.is_symlink():
        raise ValueError('Qwen 모델 경로에 심볼릭 링크를 사용할 수 없습니다.')
    if existing.exists() or existing.is_symlink():
        if named.exists():
            raise ValueError('Qwen 모델이 이전 경로와 새 경로에 모두 존재합니다.')
        return existing
    return named


def resolve_writer_embedding_directory(root):
    return _resolve(root, 'writer-agent', 'models/qwen3-embedding-0.6b', default_new=True)


def resolve_translation_model_directory(root):
    return _resolve(root, 'prompt-translation', 'models/translategemma-4b', default_new=True)


def resolve_audio_model_directory(root, service):
    names = {'music-heartmula': 'heartmula', 'sfx-dasheng-audiogen': 'dasheng-audiogen'}
    if service not in names:
        return Path(root) / 'music' / service
    metadata = Path(root).parent / '.local/audio-model-runtime' / names[service]
    if metadata.is_dir() and not metadata.is_symlink():
        return metadata
    existing = _resolve(root, 'music/' + service, 'models/audio/' + names[service])
    if existing.exists() or existing.is_symlink():
        return existing
    flattened = Path(root)/'audio'/names[service]
    if flattened.exists() or flattened.is_symlink():
        return flattened
    return metadata


def resolve_huggingface_cache(root):
    root = Path(root)
    previous = _resolve(root, 'huggingface', 'cache/huggingface')
    if previous.exists() or previous.is_symlink():
        return previous
    external = root.parent / '.cache/huggingface'
    intermediate = root / 'cache/huggingface'
    if (not any(path.is_symlink() for path in (external, external.parent, intermediate, intermediate.parent))
            and (external.is_dir() or not external.exists())):
        return external
    return previous


def resolve_minimax_snapshot(root):
    return resolve_huggingface_cache(root) / MINIMAX_SNAPSHOT


def resolve_wan_shared_model_directory(root, component):
    """Resolve one shared Wan model without choosing between conflicting trees."""
    paths = {
        'umt5': ('wan22-animate-components/split_files/text_encoders', 'umt5-xxl-fp16'),
        'vae': ('wan22-animate-components/split_files/vae', 'wan-2.1-vae'),
    }
    if component not in paths:
        raise ValueError('지원하지 않는 Wan 공용 모델입니다.')
    root = Path(root)
    old, new = (root / value for value in paths[component])
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('Wan 모델 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_dir():
            raise ValueError('Wan 모델 경로가 디렉터리가 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('Wan 모델의 이전 경로와 새 경로가 모두 존재합니다.')
    return old if old.exists() else new


def resolve_wan_vace_lora_directory(root, component):
    """Resolve one VACE LoRA installation across a directory separation."""
    paths = {
        'lightning': ('wan22-vace-loras/lightning-t2v-v1.1', 'wan22-lightning-t2v-v11'),
        'fighting': ('wan22-vace-loras', 'wan22-fighting-lora-high'),
    }
    if component not in paths:
        raise ValueError('지원하지 않는 VACE LoRA입니다.')
    root = Path(root)
    old, new = (root/value for value in paths[component])
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('LoRA 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_dir():
            raise ValueError('LoRA 경로가 디렉터리가 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('LoRA 이전 경로와 새 경로가 모두 존재합니다.')
    return old if old.exists() else new


def resolve_wan_i2v_lightning_directory(root):
    """Resolve the I2V Lightning pair without accepting ambiguous installations."""
    return _resolve_wan_i2v_lora_directory(root, 'lightning', 'wan22-lightning-i2v-seko-v1')


def resolve_wan_i2v_kungfu_directory(root):
    """Resolve the retained KungFu pair without restoring the retired option."""
    return _resolve_wan_i2v_lora_directory(root, 'kungfu', 'wan22-i2v-kungfu')


def _resolve_wan_i2v_lora_directory(root, legacy_name, new_name):
    root = Path(root)
    old = root / 'wan22-i2v' / legacy_name
    new = root / new_name
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('I2V LoRA 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_dir():
            raise ValueError('I2V LoRA 경로가 디렉터리가 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('I2V LoRA의 이전 경로와 새 경로가 모두 존재합니다.')
    return old if old.exists() else new


def resolve_pose_model_file(root, filename, *, legacy_directory=None):
    """Resolve one original or converted pose component without ambiguity."""
    names = {'yolox_l.onnx': 'yolox-l', 'yolox_l.cuda.onnx': 'yolox-l',
             'dw-ll_ucoco_384.onnx': 'dwpose-ll-ucoco-384',
             'dw-ll_ucoco_384.cuda.onnx': 'dwpose-ll-ucoco-384'}
    if filename not in names:
        raise ValueError('지원하지 않는 포즈 모델 파일입니다.')
    root = Path(root)
    legacy = Path(legacy_directory) if legacy_directory is not None else root/'wan22-fun-pose'
    if legacy.parent != root:
        raise ValueError('기존 포즈 모델 경로가 올바르지 않습니다.')
    old = legacy/filename
    new = root/names[filename]/filename
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('포즈 모델 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_file():
            raise ValueError('포즈 모델 경로가 파일이 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('포즈 모델의 이전 경로와 새 경로가 모두 존재합니다.')
    if old.exists() or (not new.exists() and not new.parent.is_dir() and legacy.is_dir()):
        return old
    return new


def resolve_vace_bf16_encoder(root):
    """Resolve the VACE BF16 UMT5 weight without choosing between duplicates."""
    root = Path(root)
    old = root/'wan22-vace'/'models_t5_umt5-xxl-enc-bf16.pth'
    new = root/'umt5-xxl-encoder-bf16'/old.name
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('UMT5 BF16 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_file():
            raise ValueError('UMT5 BF16 경로가 파일이 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('UMT5 BF16 이전 파일과 새 파일이 모두 존재합니다.')
    return old if old.exists() else new


def resolve_vace_tokenizer_directory(root):
    """Resolve the complete UMT5 tokenizer across the storage transition."""
    root = Path(root)
    old = root/'wan22-vace/official-tokenizer'
    new = root/'umt5-xxl-tokenizer-vace'
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('UMT5 토크나이저 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_dir():
            raise ValueError('UMT5 토크나이저 경로가 디렉터리가 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('UMT5 토크나이저 이전 경로와 새 경로가 모두 존재합니다.')
    return old if old.exists() else new


def resolve_minimax_qwen_encoder(root, variant):
    """Keep distinct Qwen3VL encoder formats in independently named locations."""
    variants = {
        'int8-convrot': ('qwen3vl_32b_minimax_h3_int8_convrot.safetensors', 'qwen3vl-32b-minimax-h3-int8-convrot'),
        'nvfp4-awq': ('qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors', 'qwen3vl-32b-minimax-h3-nvfp4-awq'),
    }
    if variant not in variants:
        raise ValueError('지원하지 않는 MiniMax 텍스트 인코더 형식입니다.')
    filename, directory = variants[variant]
    root = Path(root)
    old, new = root/'minimax-h3-i2v/text_encoders'/filename, root/directory/filename
    for path in (old, new):
        for parent in (path, *path.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError('MiniMax 인코더 경로에 심볼릭 링크를 사용할 수 없습니다.')
        if path.exists() and not path.is_file():
            raise ValueError('MiniMax 인코더 경로가 파일이 아닙니다.')
    if old.exists() and new.exists():
        raise ValueError('MiniMax 인코더 이전 파일과 새 파일이 모두 존재합니다.')
    return old if old.exists() else new
