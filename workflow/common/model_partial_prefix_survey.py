"""Explicitly compare selected incomplete files to complete local model prefixes."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

CANDIDATES = (
    ('minimax-h3-image-quant', 'MiniMax-H3-Image-INT8-ConvRot.safetensors', 20272349984,
     'b4d94247ec1292f3fb9aafc738c8eb5961b63685f19f5e5275630b53721e8da5', '.cache/huggingface/download'),
    ('minimax-h3-ref2va', 'diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors', 20958205608,
     'f86f2f79ebd2d76eb8eeb46091e83982e6ff51d255747e7b16e92834b392b8e9', '.cache/huggingface/download/diffusion_models'),
)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def compare_prefix(partial, final, expected_size):
    partial, final = Path(partial), Path(final)
    before = [path.lstat() for path in (partial, final)]
    if (any(not stat.S_ISREG(info.st_mode) for info in before) or before[1].st_size != expected_size
            or before[0].st_size <= 0 or before[0].st_size >= before[1].st_size):
        raise ValueError('파일 종류 또는 크기를 확인할 수 없습니다.')
    with partial.open('rb') as reader, final.open('rb') as complete:
        if [_identity(os.fstat(file.fileno())) for file in (reader, complete)] != [_identity(info) for info in before]:
            raise ValueError('비교 전 파일이 변경됐습니다.')
        matched = True
        while chunk := reader.read(8*1024*1024):
            if complete.read(len(chunk)) != chunk:
                matched = False
                break
        if [_identity(os.fstat(file.fileno())) for file in (reader, complete)] != [_identity(info) for info in before]:
            raise ValueError('비교 중 파일이 변경됐습니다.')
    if [_identity(path.lstat()) for path in (partial, final)] != [_identity(info) for info in before]:
        raise ValueError('비교 중 파일이 교체됐습니다.')
    return {'status': 'matches' if matched else 'different', 'prefix_bytes': before[0].st_size,
            'final_bytes': before[1].st_size, 'partial_identity': list(_identity(before[0])),
            'final_identity': list(_identity(before[1]))}


def survey_partial_prefixes(model_root):
    root = Path(model_root).resolve(strict=True)
    records = []
    for model, relative, expected_size, etag, cache in CANDIDATES:
        result = {'model': model, 'final_path': f'{model}/{relative}', 'partial_path': None,
                  'status': 'unavailable', 'prefix_bytes': None, 'final_bytes': None}
        try:
            base = root/model
            final, directory = base/relative, base/cache
            for path in (base, final, directory):
                for parent in (path, *path.parents):
                    if parent == root: break
                    if parent.is_symlink(): raise ValueError('링크 경로')
            partials = [path for path in directory.glob('*.incomplete') if etag in path.name]
            if len(partials) != 1: raise ValueError('부분 파일 식별 불가')
            result.update(compare_prefix(partials[0], final, expected_size))
            result['partial_path'] = partials[0].relative_to(root).as_posix()
        except (OSError, ValueError):
            pass
        records.append(result)
    return {'version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(), 'records': records}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(survey_partial_prefixes(args.model_root), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
