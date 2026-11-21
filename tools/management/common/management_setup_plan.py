"""환경 준비의 변경 범위를 설치 전에 읽기 전용으로 설명한다."""
import json
import os
from pathlib import Path
import shutil
from tools.management.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment, resolve_management_ui_environment


def describe_management_setup(selected_setup_scope):
    current_management_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_ui_path = resolve_management_ui_environment()
    current_frontend_path = Path(os.environ.get('FRONTEND_REPOSITORY_PATH', WORKFLOW_ROOT_DIRECTORY.parent / 'slime-frontend')).expanduser().resolve()
    current_renderer_paths = [str(current_frontend_path / '.tmp/field-renderer'), 'tools/management/ui/map/vendor/field-renderer']
    current_scope_records = {
        'management': ([str(current_management_path), str(current_ui_path)], '관리 Python 패키지', '없음'),
        'image': (['.venv'], 'AMD ROCm 및 이미지 Python 패키지와 고정 소스', '없음'),
        'renderer': (current_renderer_paths, '없음; 기존 Node 의존성 사용', '없음'),
        'wan-fun-runtime': (['.local/venvs/wan-fun-rocm'], 'AMD ROCm 및 Wan Fun Python 패키지', '없음'),
        'sfx-runtime': (['.venv-sfx-dasheng'], 'AMD ROCm 및 효과음 Python 패키지', '없음'),
        'kimodo-runtime': (['.local/venvs/kimodo-rocm', '.local/kimodo/upstream', '.tmp/kimodo-source-build-*'], 'AMD ROCm 및 Kimodo Python 패키지, 부재 시 공식 고정 소스', '없음'),
        'heartmula-runtime': (['.venv-music-heartmula'], 'AMD ROCm 및 고정 HeartLib 소스와 Python 패키지', '없음'),
        'writer-runtime': (['.local/writer-agent', '.model/writer-agent', '.local/model-preparation/writer-model'], 'llama.cpp 고정 소스와 작가 Python 패키지', '작가 생성 모델과 임베딩 모델 두 개 (기존 파일 검증 후 재사용)'),
        'hermes-runtime': (['.local/hermes-agent-runtime'], '고정 Hermes 소스와 잠금 Python 패키지', '없음'),
        'hermes-mcp': (['.local/hermes-mcp'], 'MCP 잠금 Python 패키지', '없음'),
        'legacy': ([str(current_management_path), str(current_ui_path), '.venv', *current_renderer_paths], '관리 및 이미지 Python 패키지와 고정 소스', '없음'),
    }
    current_target_paths, current_download_description, current_model_description = current_scope_records[selected_setup_scope]
    current_missing_requirements = []
    current_existing_blockers = []
    current_protected_paths = {'kimodo-runtime': WORKFLOW_ROOT_DIRECTORY / '.local/venvs/kimodo-rocm',
                               'heartmula-runtime': WORKFLOW_ROOT_DIRECTORY / '.venv-music-heartmula'}
    current_protected_path = current_protected_paths.get(selected_setup_scope)
    if current_protected_path is not None and (current_protected_path.exists() or current_protected_path.is_symlink()):
        current_existing_blockers.append('기존 전용 환경은 자동 변경하지 않습니다: ' + str(current_protected_path))
    if (selected_setup_scope in ('renderer', 'kimodo-runtime', 'heartmula-runtime') or
            selected_setup_scope == 'writer-runtime' and not (WORKFLOW_ROOT_DIRECTORY / '.local/writer-agent/prepared.json').is_file()) and not (current_management_path / 'bin/python').is_file():
        current_missing_requirements.append('관리 Python이 없습니다: setup --scope management를 먼저 실행하세요.')
    if selected_setup_scope in ('renderer', 'legacy'):
        if not (current_frontend_path / 'packages/field-renderer/package.json').is_file():
            current_missing_requirements.append('프론트엔드 렌더러 package.json이 없습니다.')
        if not shutil.which('npm'):
            current_missing_requirements.append('npm 실행 파일이 없습니다.')
        for current_package_name in ('esbuild', 'phaser', 'yaml'):
            if not (current_frontend_path / 'node_modules' / current_package_name / 'package.json').is_file():
                current_missing_requirements.append(f'프론트엔드 Node 의존성이 없습니다: {current_package_name}. 프론트엔드에서 npm ci를 실행하세요.')
    current_hermes_path = WORKFLOW_ROOT_DIRECTORY / '.local/hermes-agent-runtime'
    current_writer_manifest = WORKFLOW_ROOT_DIRECTORY / '.local/writer-agent/prepared.json'
    current_requires_uv = (selected_setup_scope in ('kimodo-runtime', 'heartmula-runtime', 'sfx-runtime') or
        selected_setup_scope == 'hermes-runtime' and not (current_hermes_path.exists() or current_hermes_path.is_symlink()) or
        selected_setup_scope == 'writer-runtime' and not current_writer_manifest.is_file())
    if current_requires_uv:
        current_uv_path = current_management_path / 'bin/uv'
        if not (current_uv_path.is_file() and os.access(current_uv_path, os.X_OK)) and not shutil.which('uv'):
            current_missing_requirements.append('uv 실행 파일이 없습니다: setup --scope management를 확인하세요.')
    if selected_setup_scope in ('kimodo-runtime', 'heartmula-runtime', 'hermes-runtime') and not shutil.which('git'):
        current_missing_requirements.append('git 실행 파일이 없습니다.')
    try:
        current_workspace_free_mib = shutil.disk_usage(WORKFLOW_ROOT_DIRECTORY).free // (1024 * 1024)
    except OSError:
        current_workspace_free_mib = None
    return {'scope': selected_setup_scope, 'targets': list(dict.fromkeys(current_target_paths)),
            'workspace_free_mib': current_workspace_free_mib,
            'downloads': current_download_description, 'models': current_model_description,
            'download_size': '설치 상태와 패키지 배포에 따라 달라 사전 확인 불가',
            'missing_requirements': current_missing_requirements, 'existing_blockers': current_existing_blockers,
            'limitations': '경로는 저장소 기준이며 일부 로그·캐시·잠금 파일이 추가됩니다. 여유 공간은 워크플로우 저장소 기준이며 다른 저장 위치·캐시의 공간이나 설치 성공을 보장하지 않습니다.'}


def print_management_setup_plan(selected_setup_scope):
    print(json.dumps(describe_management_setup(selected_setup_scope), ensure_ascii=False, indent=2), flush=True)
