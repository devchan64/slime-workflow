"""Verified, fixed-origin Wan 2.1 video model downloads."""
import hashlib


def inspect_files(directory, entries):
    for relative, _, _, _, size, digest in entries:
        path = directory / relative
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                return False
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    return False
        except OSError:
            return False
    return True


def prepare_files(directory, entries, profile):
    from workflow.common.model_http_download import download_verified_http
    for relative, repo, revision, remote, size, digest in entries:
        download_verified_http(f'https://huggingface.co/{repo}/resolve/{revision}/{remote}', directory / relative, digest, profile + '/' + relative, expected_total_bytes=size)
    if not inspect_files(directory, entries):
        raise ValueError('Wan 2.1 모델 파일 검증 실패')
