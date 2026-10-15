"""검수 이미지 게시 중 독자가 미완성 파일을 읽지 않도록 한다."""
import hashlib
from pathlib import Path
import re
import uuid


def publish_review_image_asset(current_source_path, current_output_directory, current_asset_name):
    current_source_path = Path(current_source_path)
    current_output_directory = Path(current_output_directory)
    if not re.fullmatch(r'[a-z0-9-]+', current_asset_name):
        raise ValueError('검수 이미지 게시 이름 형식 오류')
    current_image_bytes = current_source_path.read_bytes()
    current_image_digest = hashlib.sha256(current_image_bytes).hexdigest()
    current_output_path = current_output_directory / (current_asset_name + '-' + current_image_digest + current_source_path.suffix)
    current_output_directory.mkdir(parents=True, exist_ok=True)
    if current_output_path.exists():
        if current_output_path.read_bytes() != current_image_bytes:
            raise ValueError('해시 파일명의 검수 이미지 내용이 일치하지 않습니다.')
        return current_output_path
    current_pending_path = current_output_path.with_name(current_output_path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        current_pending_path.write_bytes(current_image_bytes)
        current_pending_path.replace(current_output_path)
    finally:
        current_pending_path.unlink(missing_ok=True)
    return current_output_path
