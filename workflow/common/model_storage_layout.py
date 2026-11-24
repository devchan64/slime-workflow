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
    if default_new and not modern.exists() and not modern.is_symlink() and not modern.parent.is_symlink():
        return modern
    return legacy


def resolve_hermes_model_directory(root):
    return _resolve(root, 'hermes-agent', 'models/hermes-coding', default_new=True)


def resolve_writer_embedding_directory(root):
    return _resolve(root, 'writer-agent', 'models/qwen3-embedding-0.6b', default_new=True)


def resolve_translation_model_directory(root):
    return _resolve(root, 'prompt-translation', 'models/translategemma-4b', default_new=True)


def resolve_audio_model_directory(root, service):
    names = {'music-heartmula': 'heartmula', 'sfx-dasheng-audiogen': 'dasheng-audiogen'}
    if service not in names:
        return Path(root) / 'music' / service
    return _resolve(root, 'music/' + service, 'models/audio/' + names[service], default_new=True)


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
