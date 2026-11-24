"""Stable backup names for selected catalog installations."""
from pathlib import Path

CATALOG_TARGETS = {'catalog-flux-report-vision': ('models', 'flux-report-vision'),
                   'catalog-trellis-dinov2': ('models', 'trellis-dinov2'),
                   'catalog-trellis-image-large': ('models', 'trellis-image-large'),
                   'catalog-hermes-coding': ('models', 'hermes-coding'),
                   'catalog-writer-agent': ('models', 'qwen3-embedding-0.6b'),
                   'catalog-translation-model': ('models', 'translategemma-4b'),
                   'catalog-heartmula': ('models', 'audio', 'heartmula'),
                   'catalog-dasheng-audiogen': ('models', 'audio', 'dasheng-audiogen'),
                   'catalog-minimax-hf-cache': ('cache', 'huggingface')}
LEGACY_TARGETS = {'catalog-flux-report-vision': 'flux-report-vision',
                  'catalog-trellis-dinov2': 'trellis-dinov2',
                  'catalog-trellis-image-large': 'trellis-image-large',
                  'catalog-hermes-coding': 'hermes-agent',
                  'catalog-writer-agent': 'writer-agent',
                  'catalog-translation-model': 'prompt-translation',
                  'catalog-heartmula': ('music', 'music-heartmula'),
                  'catalog-dasheng-audiogen': ('music', 'sfx-dasheng-audiogen'),
                  'catalog-minimax-hf-cache': 'huggingface'}


FLATTENED_TARGETS = {name: parts[1:] for name, parts in CATALOG_TARGETS.items()
                     if parts[0] == 'models' and name not in ('catalog-trellis-dinov2', 'catalog-trellis-image-large')}


def target_parts(root, name):
    if isinstance(name, tuple):
        return name
    nested = CATALOG_TARGETS.get(name, (name,))
    flat = FLATTENED_TARGETS.get(name)
    if flat is None:
        return nested
    root = Path(root)
    nested_path = _checked_path(root, nested)
    flat_path = _checked_path(root, flat)
    if nested_path.exists() and flat_path.exists():
        raise ValueError('이전 경로와 새 경로가 모두 존재해 모델 설치본을 결정할 수 없습니다.')
    return flat if flat_path.exists() else nested


def _checked_path(root, parts):
    root = Path(root)
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('모델 대상 경로에 심볼릭 링크를 사용할 수 없습니다.')
    return path


def target_path(root, name, *, layout_root=None):
    return _checked_path(root, target_parts(layout_root if layout_root is not None else root, name))
