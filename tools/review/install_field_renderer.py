"""프론트엔드가 빌드한 렌더러를 Git 제외 로컬 배포 경로에 설치한다."""
import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
import yaml

RENDERER_VENDOR_DIRECTORY = Path(__file__).resolve().parent / 'ui/map/vendor/field-renderer'
RENDERER_EXPECTED_FILES = {'field-renderer.mjs', 'town-renderer.mjs', 'game-render-profile.mjs', 'phaser.mjs', 'LICENSE.phaser.md'}


def install_renderer_bundle(current_source_directory):
    current_manifest_path = RENDERER_VENDOR_DIRECTORY / 'manifest.yaml'
    current_expected_manifest = yaml.safe_load(current_manifest_path.read_text())
    current_source_manifest = yaml.safe_load((current_source_directory / 'manifest.yaml').read_text())
    if current_source_manifest != current_expected_manifest:
        raise ValueError('배포 manifest가 고정된 버전·해시와 일치하지 않습니다. 채택할 manifest를 먼저 갱신하세요.')
    if set(current_source_manifest['files']) != RENDERER_EXPECTED_FILES:
        raise ValueError('렌더러 배포 파일 목록 오류')
    for current_file_name, current_expected_hash in current_source_manifest['files'].items():
        current_source_path = current_source_directory / current_file_name
        if hashlib.sha256(current_source_path.read_bytes()).hexdigest() != current_expected_hash:
            raise ValueError('렌더러 해시 불일치: ' + current_file_name)
    for current_file_name in current_source_manifest['files']:
        shutil.copy2(current_source_directory / current_file_name, RENDERER_VENDOR_DIRECTORY / current_file_name)
    print(f'{datetime.now().isoformat()}/field-renderer/install/complete {current_source_manifest["version"]}')


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--source', type=Path, required=True)
    current_argument_values = current_argument_parser.parse_args()
    print(f'{datetime.now().isoformat()}/field-renderer/install/start {current_argument_values.source}')
    try:
        install_renderer_bundle(current_argument_values.source.resolve())
    except Exception as current_install_error:
        print(f'{datetime.now().isoformat()}/field-renderer/install/error {current_install_error}')
        raise
