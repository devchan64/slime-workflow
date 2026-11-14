"""공식 실행 소스·토크나이저를 고정 해시로 준비한다. 모델 양자화는 변경하지 않는다."""
import hashlib
import io
import tarfile
from pathlib import Path
import yaml
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION

VACE_OFFICIAL_MANIFEST_PATH = Path(__file__).parent/'config/official-runtime.yaml'
VACE_OFFICIAL_INSTALL_ROOT = VACE_WORKSPACE_ROOT/'.local/videox-fun-vace-pinned'
VACE_OFFICIAL_TOKENIZER_ROOT = VACE_WORKSPACE_ROOT/'.model/wan22-vace/official-tokenizer'


def verify_official_runtime():
    current_manifest_record=yaml.safe_load(VACE_OFFICIAL_MANIFEST_PATH.read_text())
    for current_relative_name,current_expected_hash in current_manifest_record['source_files'].items():
        current_input_path=VACE_OFFICIAL_INSTALL_ROOT/current_relative_name
        if not current_input_path.is_file() or hashlib.sha256(current_input_path.read_bytes()).hexdigest()!=current_expected_hash:
            raise ValueError(f'공식 소스 누락·변조: {current_input_path}')
    for current_file_name,current_expected_hash in current_manifest_record['tokenizer_files'].items():
        current_input_path=VACE_OFFICIAL_TOKENIZER_ROOT/current_file_name
        if not current_input_path.is_file() or hashlib.sha256(current_input_path.read_bytes()).hexdigest()!=current_expected_hash:
            raise ValueError(f'공식 토크나이저 누락·변조: {current_input_path}')


def prepare_official_runtime():
    current_manifest_record=yaml.safe_load(VACE_OFFICIAL_MANIFEST_PATH.read_text())
    current_revision_text=current_manifest_record['source_revision']
    from tools.review.common.model_http_download import download_verified_http
    current_archive_path = VACE_OFFICIAL_INSTALL_ROOT.parent/'videox-fun-vace-downloads'/(current_revision_text+'.tar.gz')
    download_verified_http(f'https://github.com/aigc-apps/VideoX-Fun/archive/{current_revision_text}.tar.gz', current_archive_path, current_manifest_record['archive_sha256'], 'wan-vace/official-source')
    current_archive_bytes = current_archive_path.read_bytes()
    if hashlib.sha256(current_archive_bytes).hexdigest()!=current_manifest_record['archive_sha256']:
        raise ValueError('공식 소스 압축파일 해시 불일치')
    VACE_OFFICIAL_INSTALL_ROOT.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(current_archive_bytes),mode='r:gz') as current_archive_file:
        for current_member_record in current_archive_file.getmembers():
            if not current_member_record.isfile():continue
            current_relative_path=Path(*Path(current_member_record.name).parts[1:])
            if current_relative_path.is_absolute() or '..' in current_relative_path.parts:raise ValueError('소스 경로 이탈')
            current_output_path=VACE_OFFICIAL_INSTALL_ROOT/current_relative_path
            current_output_path.parent.mkdir(parents=True,exist_ok=True)
            current_output_path.write_bytes(current_archive_file.extractfile(current_member_record).read())
    VACE_OFFICIAL_TOKENIZER_ROOT.mkdir(parents=True,exist_ok=True)
    for current_file_name,current_expected_hash in current_manifest_record['tokenizer_files'].items():
        current_tokenizer_path = VACE_OFFICIAL_TOKENIZER_ROOT/current_file_name
        download_verified_http(f'https://huggingface.co/{VACE_ENCODER_IDENTIFIER}/resolve/{VACE_ENCODER_REVISION}/google/umt5-xxl/{current_file_name}', current_tokenizer_path, current_expected_hash, 'wan-vace/tokenizer/'+current_file_name)
    (VACE_OFFICIAL_INSTALL_ROOT/'PINNED_REVISION').write_text(current_revision_text+'\n')
    verify_official_runtime()
