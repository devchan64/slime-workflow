"""이미지 작업 접수 전에 가상환경 버전과 필수 의존성을 검사한다."""
import json
from pathlib import Path
import subprocess

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
IMAGE_RUNTIME_TIMEOUT_SECONDS = 15


def validate_image_runtime(environment_root_path=None):
    environment_root_path = environment_root_path or WORKFLOW_ROOT_DIRECTORY / '.venv'
    environment_python_path = environment_root_path / 'bin/python'
    environment_config_values = dict(
        current_config_line.split(' = ', 1)
        for current_config_line in (environment_root_path / 'pyvenv.cfg').read_text().splitlines()
        if ' = ' in current_config_line
    )
    configured_python_version = environment_config_values.get('version') or environment_config_values.get('version_info')
    if not configured_python_version:
        raise ValueError(f'가상환경 Python 버전 정보 누락: {environment_root_path}')
    expected_python_version = '.'.join(configured_python_version.split('.')[:2])
    runtime_probe_result = subprocess.run(
        [str(environment_python_path), '-c',
         'import sys,json,importlib.util; print(json.dumps({"version":"%s.%s"%sys.version_info[:2],"missing":[name for name in ("torch","diffusers","transformers","accelerate","safetensors") if importlib.util.find_spec(name) is None]}))'],
        capture_output=True, text=True, timeout=IMAGE_RUNTIME_TIMEOUT_SECONDS, check=True,
    )
    runtime_probe_record = json.loads(runtime_probe_result.stdout)
    if runtime_probe_record['version'] != expected_python_version:
        raise ValueError(f'이미지 실행 환경 버전 불일치: {environment_python_path}, 필요 Python {expected_python_version}, 현재 {runtime_probe_record["version"]}. 가상환경 Python 링크를 원래 버전으로 복구하세요.')
    if runtime_probe_record['missing']:
        raise ValueError(f'이미지 실행 환경 의존성 누락: {environment_python_path}: {", ".join(runtime_probe_record["missing"])}. 해당 가상환경에 이미지 생성 의존성을 설치하세요.')
