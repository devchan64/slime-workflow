"""명시적 setup 명령에서만 가상환경과 의존성을 준비한다."""
import os
import sys
import json
import shutil
import fcntl
import uuid
from contextlib import contextmanager
from pathlib import Path
from tools.management.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment, resolve_management_ui_environment
from tools.management.common.management_process import run_logged_management_command

IMAGE_ROCM_INDEX_URL = 'https://stable.repo.amd.com/rocm/whl-next/'
IMAGE_ENVIRONMENT_PATH = WORKFLOW_ROOT_DIRECTORY / '.venv'
IMAGE_CONSTRAINTS_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/constraints-rocm.txt'
IMAGE_REQUIREMENTS_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/requirements-runtime.txt'

MANAGEMENT_ENVIRONMENT_RECORDS = (
    ('VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/management/requirements.txt'),
)


def prepare_virtual_environment(environment_directory_path, launcher_trace_logger):
    selected_python_path = environment_directory_path / 'bin/python'
    if environment_directory_path.is_symlink():
        raise ValueError(f'가상환경 경로가 심볼릭 링크입니다: {environment_directory_path}. 자동으로 변경하지 않습니다.')
    if selected_python_path.is_file() and not (environment_directory_path / 'pyvenv.cfg').is_file():
        raise ValueError(f'가상환경 설정이 없습니다: {environment_directory_path}/pyvenv.cfg. 시스템 Python에는 설치하지 않습니다.')
    if not selected_python_path.is_file():
        if environment_directory_path.exists() and any(environment_directory_path.iterdir()):
            raise ValueError(f'기존 가상환경이 불완전하거나 비어 있지 않습니다: {environment_directory_path}. 자동으로 덮어쓰지 않습니다.')
        run_logged_management_command([sys.executable, '-m', 'venv', str(environment_directory_path)], launcher_trace_logger)
    run_logged_management_command([str(selected_python_path), '-m', 'ensurepip', '--upgrade'], launcher_trace_logger)
    return selected_python_path


def prepare_image_runtime_environment(image_python_path, launcher_trace_logger):
    """기존 PyTorch 빌드를 확인하고 고정된 gfx1151 ROCm 실행 환경을 준비한다."""
    current_preflight_code = (
        "import importlib.metadata as m, importlib.util; "
        "versions={n:m.version(n) for n in ('torch','torchvision') if importlib.util.find_spec(n)}; "
        "expected={'torch':'2.13.0+rocm10.0.0','torchvision':'0.28.0+rocm10.0.0'}; "
        "import sys; sys.exit(0 if all(expected[n] == v for n,v in versions.items()) else "
        "'기존 PyTorch 빌드를 교체하지 않습니다. 별도 환경에서 ROCm 설정을 확인하세요: '+str(versions))"
    )
    run_logged_management_command([str(image_python_path), '-c', current_preflight_code], launcher_trace_logger)
    current_platform_code = (
        "import sys, platform, subprocess; "
        "sys.exit('이미지 ROCm 자동 설치는 Linux x86_64 Python 3.14를 지원합니다') if not (sys.platform == 'linux' and platform.machine() == 'x86_64' and sys.version_info[:2] == (3,14)) else None; "
        "r=subprocess.run(['rocminfo'],capture_output=True,text=True,check=True,timeout=30); "
        "sys.exit('gfx1151 GPU를 확인할 수 없습니다. 호환되는 ROCm 환경을 별도로 구성하세요') if 'gfx1151' not in r.stdout else None"
    )
    run_logged_management_command([str(image_python_path), '-c', current_platform_code], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'install', '--disable-pip-version-check',
        '--index-url', IMAGE_ROCM_INDEX_URL, 'torch[device-gfx1151]==2.13.0+rocm10.0.0',
        'torchvision[device-gfx1151]==0.28.0+rocm10.0.0'], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'install', '--disable-pip-version-check',
        '-c', str(IMAGE_CONSTRAINTS_PATH), '-r', str(IMAGE_REQUIREMENTS_PATH)], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-c',
        "import sys, torch, accelerate, transformers, safetensors, einops, imageio, imageio_ffmpeg, ftfy, librosa, func_timeout, cv2, av; from diffusers import QwenImage21Pipeline, ModularPipeline; "
        "from diffusers.modular_pipelines.components_manager import ComponentsManager; "
        "from diffusers.models.transformers.transformer_flux3 import Flux3PosEmbed, _get_qkv_projections; "
        "sys.exit('ROCm PyTorch가 아닙니다') if not torch.version.hip else None; print('FLUX 및 기존 이미지 실행 의존성 확인 완료')"], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'check'], launcher_trace_logger)


@contextmanager
def hold_shared_environment_reservation():
    """공유 Python 설치 동안 GPU 대기열의 새 작업 시작을 막는다."""
    from tools.management.common.gpu_job_queue import GPU_QUEUE_DIRECTORY
    if GPU_QUEUE_DIRECTORY.is_symlink():
        raise ValueError('GPU 대기열 경로가 심볼릭 링크여서 환경 설치를 중단합니다.')
    GPU_QUEUE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    current_active_directory = GPU_QUEUE_DIRECTORY / 'active'
    if current_active_directory.is_symlink():
        raise ValueError('GPU 예약 경로가 심볼릭 링크여서 환경 설치를 중단합니다.')
    current_active_directory.mkdir(exist_ok=True)
    current_queue_lock_path = GPU_QUEUE_DIRECTORY / 'execution.lock'
    if current_queue_lock_path.is_symlink():
        raise ValueError('GPU 대기열 잠금 경로가 심볼릭 링크여서 환경 설치를 중단합니다.')
    current_reservation_path = current_active_directory / ('management-setup-' + uuid.uuid4().hex + '.json')
    current_process_fields = Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()
    current_reservation_record = {'pid': os.getpid(), 'pid_start_token': current_process_fields[19], 'service': 'management-setup', 'required_memory_mib': 0}
    with current_queue_lock_path.open('a') as current_queue_lock:
        fcntl.flock(current_queue_lock, fcntl.LOCK_EX)
        if any(current_active_directory.glob('*.json')):
            raise RuntimeError('GPU 작업 또는 확인되지 않은 예약이 있어 공유 환경을 변경하지 않습니다.')
        try:
            with current_reservation_path.open('x', encoding='utf-8') as current_reservation_stream:
                json.dump(current_reservation_record, current_reservation_stream)
        except BaseException:
            current_reservation_path.unlink(missing_ok=True)
            raise
    try:
        yield
    finally:
        with current_queue_lock_path.open('a') as current_queue_lock:
            fcntl.flock(current_queue_lock, fcntl.LOCK_EX)
            if current_reservation_path.is_symlink() or not current_reservation_path.is_file() or json.loads(current_reservation_path.read_text()) != current_reservation_record:
                raise RuntimeError('공유 환경 예약이 변경되어 자동 정리하지 않습니다. GPU 상태를 확인하세요.')
            current_reservation_path.unlink()


def prepare_management_environments(launcher_trace_logger, selected_setup_scope="legacy"):
    current_shared_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_ui_path = resolve_management_ui_environment()
    current_shared_image_path = IMAGE_ENVIRONMENT_PATH.resolve()
    current_modifies_shared_path = (selected_setup_scope in ('legacy', 'image', 'wan-fun-runtime', 'sfx-runtime', 'kimodo-runtime', 'heartmula-runtime', 'writer-runtime') or
        selected_setup_scope == 'management' and (current_shared_path.resolve() == current_shared_image_path or current_ui_path.resolve() == current_shared_image_path))
    if current_modifies_shared_path:
        with hold_shared_environment_reservation():
            return prepare_selected_management_environment(launcher_trace_logger, selected_setup_scope)
    return prepare_selected_management_environment(launcher_trace_logger, selected_setup_scope)


def prepare_selected_management_environment(launcher_trace_logger, selected_setup_scope):
    if selected_setup_scope not in ("legacy", "management", "image", "renderer", "hermes-runtime", "hermes-mcp", "wan-fun-runtime", "sfx-runtime", "kimodo-runtime", "heartmula-runtime", "writer-runtime"):
        raise ValueError(f"지원하지 않는 준비 범위: {selected_setup_scope}")
    if selected_setup_scope == "writer-runtime":
        return prepare_writer_runtime_environment(launcher_trace_logger)
    if selected_setup_scope == "heartmula-runtime":
        current_management_python = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
        if not current_management_python.is_file():
            raise ValueError('관리 Python이 없습니다. 먼저 setup --scope management를 실행하세요.')
        return run_logged_management_command([str(current_management_python), '-I', '-B', str(WORKFLOW_ROOT_DIRECTORY / 'generators/music/heartmula/setup_runtime.py')], launcher_trace_logger)
    if selected_setup_scope == "kimodo-runtime":
        current_management_python = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
        if not current_management_python.is_file():
            raise ValueError('관리 Python이 없습니다. 먼저 setup --scope management를 실행하세요.')
        return run_logged_management_command([str(current_management_python), '-I', '-B', str(WORKFLOW_ROOT_DIRECTORY / 'generators/kimodo/setup_runtime.py')], launcher_trace_logger)
    if selected_setup_scope == "sfx-runtime":
        from generators.sound_effects.setup_runtime import install_effects_runtime
        return install_effects_runtime()
    if selected_setup_scope == "wan-fun-runtime":
        from generators.wan_fun.setup_rocm import setup_fun_rocm_environment
        return setup_fun_rocm_environment(prepare_model_assets=False)
    if selected_setup_scope == "hermes-runtime":
        return prepare_hermes_runtime_environment(launcher_trace_logger)
    if selected_setup_scope == "hermes-mcp":
        return prepare_hermes_mcp_environment(launcher_trace_logger)
    if selected_setup_scope == "renderer":
        return prepare_management_renderer(launcher_trace_logger)
    if selected_setup_scope == "image":
        current_image_python = prepare_virtual_environment(IMAGE_ENVIRONMENT_PATH, launcher_trace_logger)
        return prepare_image_runtime_environment(current_image_python, launcher_trace_logger)
    current_environment_records = list(MANAGEMENT_ENVIRONMENT_RECORDS)
    if 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH' in os.environ:
        current_shared_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
        current_ui_path = resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv')
        if current_shared_path != current_ui_path:
            current_environment_records.append(('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/management/requirements.txt'))
    current_prepared_paths = set()
    # 이미지 작업자는 고정된 .venv를 사용한다. GUI 경로 설정과 구분한다.
    if selected_setup_scope == "legacy":
        current_image_python = prepare_virtual_environment(IMAGE_ENVIRONMENT_PATH, launcher_trace_logger)
        current_prepared_paths.add(IMAGE_ENVIRONMENT_PATH)
        prepare_image_runtime_environment(current_image_python, launcher_trace_logger)
    for environment_variable_name, default_directory_name, dependency_manifest_path in current_environment_records:
        environment_directory_path = resolve_management_environment(environment_variable_name, default_directory_name)
        selected_python_path = (environment_directory_path / 'bin/python' if environment_directory_path in current_prepared_paths
                                else prepare_virtual_environment(environment_directory_path, launcher_trace_logger))
        current_prepared_paths.add(environment_directory_path)
        current_install_command = [str(selected_python_path), '-m', 'pip', 'install', '--disable-pip-version-check']
        if environment_directory_path == IMAGE_ENVIRONMENT_PATH:
            current_install_command += ['-c', str(IMAGE_CONSTRAINTS_PATH)]
        current_install_command += ['-r', str(WORKFLOW_ROOT_DIRECTORY / dependency_manifest_path)]
        run_logged_management_command(current_install_command, launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'check'], launcher_trace_logger)
    if selected_setup_scope == "legacy":
        prepare_management_renderer(launcher_trace_logger)


def prepare_writer_runtime_environment(launcher_trace_logger):
    """기존 작가·Hermes 서버는 검증만 하고 빈 환경에 기존 준비 절차를 호출한다."""
    from generators.writer_agent import prepare as writer_prepare_module
    current_runtime_root = writer_prepare_module.RUNTIME_INSTALL_ROOT
    current_manifest_path = current_runtime_root / 'prepared.json'
    if current_runtime_root.is_symlink() or current_manifest_path.is_symlink():
        raise ValueError('작가 실행 환경 또는 준비 기록이 심볼릭 링크입니다. 자동 변경하지 않습니다.')
    if current_manifest_path.is_file():
        try:
            current_manifest_record = json.loads(current_manifest_path.read_text(encoding='utf-8'))
            current_expected_values = {'backend':'rocm', 'gpu_architecture':'gfx1151',
                'server_release_name':writer_prepare_module.SOURCE_RELEASE_NAME,
                'model_file_sha256':writer_prepare_module.MODEL_DOWNLOAD_SHA256,
                'embedding_file_sha256':writer_prepare_module.EMBEDDING_DOWNLOAD_SHA256,
                'requirements_file_sha256':writer_prepare_module.calculate_file_digest(writer_prepare_module.WORKFLOW_MODULE_ROOT / 'requirements.lock')}
            if not isinstance(current_manifest_record, dict) or any(current_manifest_record.get(current_key_name) != current_expected_value for current_key_name, current_expected_value in current_expected_values.items()):
                raise ValueError('준비 기록이 고정 구성과 다릅니다.')
            current_verified_files = ((writer_prepare_module.RUNTIME_SERVER_PATH, current_manifest_record.get('server_binary_sha256')),
                (writer_prepare_module.MODEL_DOWNLOAD_ROOT / writer_prepare_module.MODEL_DOWNLOAD_NAME, writer_prepare_module.MODEL_DOWNLOAD_SHA256),
                (writer_prepare_module.MODEL_DOWNLOAD_ROOT / writer_prepare_module.EMBEDDING_DOWNLOAD_NAME, writer_prepare_module.EMBEDDING_DOWNLOAD_SHA256))
            for current_file_path, current_expected_digest in current_verified_files:
                if current_file_path.is_symlink() or not current_file_path.is_file() or not isinstance(current_expected_digest, str) or writer_prepare_module.calculate_file_digest(current_file_path) != current_expected_digest:
                    raise ValueError(f'작가 실행 파일 또는 모델 해시가 다릅니다: {current_file_path.name}')
        except (OSError, ValueError, TypeError) as current_validation_error:
            raise ValueError(f'기존 작가 실행 환경을 확인하세요. 자동 변경하지 않습니다: {current_validation_error}') from current_validation_error
        current_writer_environment = writer_prepare_module.RUNTIME_PYTHON_PATH.parent.parent
        if current_writer_environment.is_symlink() or not (current_writer_environment / 'pyvenv.cfg').is_file() or not writer_prepare_module.RUNTIME_PYTHON_PATH.is_file():
            raise ValueError('기존 작가 Python 환경이 불완전합니다. 자동 변경하지 않습니다.')
        current_package_check_code = ("import importlib.metadata as m,pathlib,re,sys; "
            "entries=[re.match(r'^([A-Za-z0-9_.-]+)==([^\\s;]+)',line) for line in pathlib.Path(sys.argv[1]).read_text().splitlines()]; "
            "pairs=[(entry.group(1),entry.group(2)) for entry in entries if entry]; "
            "sys.exit('작가 Python 고정 패키지 버전 불일치') if not pairs or any(m.version(name)!=value for name,value in pairs) else None; "
            "import yaml,jsonschema; print('작가 Python 고정 패키지 확인 완료')")
        run_logged_management_command([str(writer_prepare_module.RUNTIME_PYTHON_PATH), '-I', '-B', '-c', current_package_check_code,
            str(writer_prepare_module.WORKFLOW_MODULE_ROOT / 'requirements.lock')], launcher_trace_logger)
        launcher_trace_logger.emit_launch_trace('ready', '기존 작가·Hermes ROCm 서버와 모델 해시·Python 버전 검증 완료')
        return
    current_managed_paths = (writer_prepare_module.RUNTIME_PYTHON_PATH.parent.parent,
        current_runtime_root / ('llama.cpp-' + writer_prepare_module.SOURCE_RELEASE_NAME),
        current_runtime_root / (writer_prepare_module.SOURCE_RELEASE_NAME + '.tar.gz'), current_manifest_path)
    if any(current_path_value.exists() or current_path_value.is_symlink() for current_path_value in current_managed_paths):
        raise ValueError('기존 작가 실행 환경이 불완전합니다. 확인 후 별도로 보존하세요. 자동 변경하지 않습니다.')
    current_management_python = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
    if not current_management_python.is_file():
        raise ValueError('관리 Python이 없습니다. 먼저 setup --scope management를 실행하세요.')
    current_run_directory = WORKFLOW_ROOT_DIRECTORY / '.tmp/writer-runtime-setup' / uuid.uuid4().hex
    current_bootstrap_code = "import os,runpy,sys; os.environ['PATH']=os.path.dirname(sys.executable)+os.pathsep+os.environ.get('PATH',''); sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('generators.writer_agent.prepare',run_name='__main__')"
    return run_logged_management_command([str(current_management_python), '-I', '-B', '-c', current_bootstrap_code,
        str(WORKFLOW_ROOT_DIRECTORY), '--new-only', '--run-dir', str(current_run_directory)], launcher_trace_logger)


def prepare_management_renderer(launcher_trace_logger):
    frontend_repository_path = Path(os.environ.get('FRONTEND_REPOSITORY_PATH', WORKFLOW_ROOT_DIRECTORY.parent / 'slime-frontend')).resolve()
    renderer_package_path = frontend_repository_path / 'packages/field-renderer/package.json'
    renderer_package_version = json.loads(renderer_package_path.read_text(encoding='utf-8'))['version']
    run_logged_management_command(['npm', '--prefix', str(frontend_repository_path), 'run', 'build:field-renderer'], launcher_trace_logger)
    renderer_bundle_directory = frontend_repository_path / '.tmp/field-renderer' / renderer_package_version
    shared_python_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
    run_logged_management_command([str(shared_python_path), str(WORKFLOW_ROOT_DIRECTORY / 'tools/management/install_field_renderer.py'), '--source', str(renderer_bundle_directory)], launcher_trace_logger)


def prepare_hermes_runtime_environment(launcher_trace_logger):
    """고정된 Hermes 소스를 준비하고 기존 디렉터리는 덮어쓰지 않는다."""
    from tools.management.domains.hermes_agent.runtime_integrity import (HERMES_RUNTIME_REVISION, HERMES_RUNTIME_RELEASE, HERMES_RUNTIME_SOURCE, verify_hermes_runtime_integrity)
    hermes_runtime_path = WORKFLOW_ROOT_DIRECTORY / '.local/hermes-agent-runtime'
    if hermes_runtime_path.exists() or hermes_runtime_path.is_symlink():
        verify_hermes_runtime_integrity(hermes_runtime_path)
        launcher_trace_logger.emit_launch_trace('ready', '기존 Hermes 소스 환경 검증 완료')
        return
    hermes_managed_uv = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/uv'
    hermes_uv_path = str(hermes_managed_uv) if hermes_managed_uv.is_file() and os.access(hermes_managed_uv, os.X_OK) else shutil.which('uv')
    if hermes_uv_path is None:
        raise ValueError('Hermes 준비에 uv가 필요합니다. setup --scope management 실행 후 다시 시도하세요.')
    if not Path(hermes_uv_path).is_file() or not os.access(hermes_uv_path, os.X_OK):
        raise ValueError('Hermes 준비에 uv가 필요합니다. uv 설치 후 다시 실행하세요.')
    hermes_runtime_path.parent.mkdir(parents=True, exist_ok=True)
    run_logged_management_command(['git', 'clone', '--no-checkout', HERMES_RUNTIME_SOURCE, str(hermes_runtime_path)], launcher_trace_logger)
    run_logged_management_command(['git', '-C', str(hermes_runtime_path), 'checkout', '--detach', HERMES_RUNTIME_REVISION], launcher_trace_logger)
    hermes_environment_setting = 'UV_PROJECT_ENVIRONMENT=' + str(hermes_runtime_path / '.venv')
    run_logged_management_command(['env', '-u', 'VIRTUAL_ENV', hermes_environment_setting, hermes_uv_path, 'sync', '--project', str(hermes_runtime_path), '--locked', '--no-dev'], launcher_trace_logger)
    hermes_marker_path = hermes_runtime_path / 'prepared-local.json'
    hermes_marker_value = {'revision': HERMES_RUNTIME_REVISION, 'release': HERMES_RUNTIME_RELEASE, 'source': HERMES_RUNTIME_SOURCE}
    with hermes_marker_path.open('x', encoding='utf-8') as hermes_marker_stream:
        json.dump(hermes_marker_value, hermes_marker_stream, ensure_ascii=False)
        hermes_marker_stream.write('\n')
    verify_hermes_runtime_integrity(hermes_runtime_path)


def prepare_hermes_mcp_environment(launcher_trace_logger):
    """별도 MCP 환경을 준비하며 기존 환경의 패키지는 자동 변경하지 않는다."""
    hermes_environment_path = WORKFLOW_ROOT_DIRECTORY / '.local/hermes-mcp'
    hermes_python_path = hermes_environment_path / 'bin/python'
    if hermes_environment_path.exists() or hermes_environment_path.is_symlink():
        if hermes_environment_path.is_symlink() or not (hermes_environment_path / 'pyvenv.cfg').is_file() or not hermes_python_path.is_file():
            raise ValueError('기존 MCP 환경이 불완전합니다. 경로를 확인하세요. 자동 삭제하거나 덮어쓰지 않습니다.')
        hermes_requirements_path = WORKFLOW_ROOT_DIRECTORY / 'generators/hermes_agent/requirements-mcp.lock'
        hermes_check_code = "import sys,importlib.metadata as m,pathlib; entries=(x.strip().split('==') for x in pathlib.Path(sys.argv[1]).read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')); sys.exit(0 if sys.version_info[:2] == (3,14) and all(m.version(n)==v for n,v in entries) else 'MCP Python 또는 고정 패키지 버전 불일치')"
        run_logged_management_command([str(hermes_python_path), '-c', hermes_check_code, str(hermes_requirements_path)], launcher_trace_logger)
        run_logged_management_command([str(hermes_python_path), '-m', 'pip', 'check'], launcher_trace_logger)
        return
    if sys.version_info[:2] != (3, 14):
        raise ValueError('Hermes MCP 준비에는 Python 3.14가 필요합니다.')
    hermes_python_path = prepare_virtual_environment(hermes_environment_path, launcher_trace_logger)
    hermes_requirements_path = WORKFLOW_ROOT_DIRECTORY / 'generators/hermes_agent/requirements-mcp.lock'
    run_logged_management_command([str(hermes_python_path), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(hermes_requirements_path)], launcher_trace_logger)
    run_logged_management_command([str(hermes_python_path), '-m', 'pip', 'check'], launcher_trace_logger)
