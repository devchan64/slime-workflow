"""검수 스냅샷 사이에서 동일 파일의 디스크 중복을 줄인다."""
from pathlib import Path
import os
import shutil


def link_or_copy_review_file(source_file_path: Path, destination_file_path: Path):
    destination_file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source_file_path, destination_file_path)
    except OSError:
        shutil.copy2(source_file_path, destination_file_path)
