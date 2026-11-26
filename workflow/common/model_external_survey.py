"""Read-only survey of selected model files outside the model backup root."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

EXTERNAL_GROUPS = ('.local/pixal3d-experiment', '.local/trellis2-experiment',
                   '.local/anigen-experiment', '.local/model-catalog/retained',
                   '.local/animationgpt-legacy/flan-t5-base')
MINIMUM_BYTES = 100 * 1024**2
EXTENSIONS = {'.safetensors', '.gguf', '.ckpt', '.pth', '.pt', '.bin'}


def survey_external_weights(workspace):
    root = Path(workspace).resolve(strict=True)
    records, errors = [], []
    for group in EXTERNAL_GROUPS:
        directory = root / group
        # Refuse links in every component, including an existing symlinked parent.
        parts = Path(group).parts
        if any((root.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)) or not directory.is_dir():
            errors.append({'path': group, 'error': '경로 없음 또는 심볼릭 링크'})
            continue
        def onerror(error):
            try:
                path = Path(error.filename).relative_to(root).as_posix()
            except (TypeError, ValueError):
                path = group
            errors.append({'path': path, 'error': str(error)})
        for current, dirs, files in os.walk(directory, followlinks=False, onerror=onerror):
            dirs[:] = sorted(name for name in dirs if not (Path(current) / name).is_symlink())
            for name in sorted(files):
                path = Path(current) / name
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                try:
                    before = path.lstat()
                    if not stat.S_ISREG(before.st_mode) or before.st_size <= MINIMUM_BYTES:
                        continue
                    after = path.lstat()
                    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
                    records.append({'group': group, 'path': path.relative_to(root).as_posix(), 'size': before.st_size,
                                    'allocated_bytes': before.st_blocks * 512, 'links': before.st_nlink,
                                    'mtime_ns': before.st_mtime_ns, 'changed': identity(before) != identity(after)})
                except OSError as error:
                    onerror(error)
    return {'observed_at': datetime.now(timezone.utc).isoformat(), 'minimum_bytes_exclusive': MINIMUM_BYTES,
            'roots': list(EXTERNAL_GROUPS), 'files': records, 'errors': errors,
            'scope': 'regular files with selected model extensions; no file contents read; not a complete inventory or deletion assessment'}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    print(json.dumps(survey_external_weights(args.workspace), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
