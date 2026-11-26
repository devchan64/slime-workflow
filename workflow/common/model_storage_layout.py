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
