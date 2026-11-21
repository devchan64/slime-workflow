"""설치나 프로세스 제어 없이 관리 환경의 기본 조건을 점검한다."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from urllib.request import ProxyHandler, build_opener

from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment, resolve_management_ui_environment


def inspect_management_python(environment_directory_path, required_module_names):
    """대상 가상환경에서 패키지 발견 여부만 확인하고 파일을 생성하지 않는다."""
    environment_python_path = environment_directory_path / 'bin/python'
    if not environment_python_path.is_file():
        return {'status': 'missing', 'path': str(environment_directory_path)}
    environment_path_values, environment_reference_record = collect_environment_site_paths(environment_directory_path)
    environment_probe_code = "import importlib.machinery,json,sys; paths=json.loads(sys.argv[1]); print(json.dumps({n:importlib.machinery.PathFinder.find_spec(n, paths + sys.path) is not None for n in sys.argv[2:]}))"
    try:
        environment_probe_result = subprocess.run([str(environment_python_path), '-I', '-S', '-B', '-c', environment_probe_code, json.dumps(environment_path_values), *required_module_names], capture_output=True, text=True, check=True, timeout=10)
        environment_module_values = json.loads(environment_probe_result.stdout)
        if not isinstance(environment_module_values, dict) or set(environment_module_values) != set(required_module_names) or any(type(current_module_value) is not bool for current_module_value in environment_module_values.values()):
            raise ValueError('패키지 검사 응답 형식 오류')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unknown', 'path': str(environment_directory_path)}
    missing_module_names = [current_module_name for current_module_name, current_module_value in environment_module_values.items() if not current_module_value]
    environment_probe_incomplete = bool(environment_reference_record['executable_lines'] or environment_reference_record['unreadable'])
    environment_probe_status = ('unknown' if missing_module_names and environment_probe_incomplete else 'missing_packages' if missing_module_names else 'present')
    return {'status': environment_probe_status, 'path': str(environment_directory_path), 'missing_modules': missing_module_names, 'path_setup_code_skipped': environment_probe_incomplete}


def inspect_registered_model_inventory(environment_python_path):
    """기존 모델 인벤토리를 읽어 파일 수만 요약하며 준비 완료로 해석하지 않는다."""
    if not environment_python_path.is_file():
        return {'status': 'unavailable', 'detail': '관리 Python 환경이 없습니다.'}
    inventory_site_paths, _ = collect_environment_site_paths(environment_python_path.parent.parent)
    inventory_probe_code = "import json,sys; sys.path[:0]=[sys.argv[1]]+json.loads(sys.argv[2]); from tools.review.common.model_file_inventory import list_model_inventory_files; r=list_model_inventory_files(); print(json.dumps({n:{'count':v['count'],'total_bytes':v['total_bytes'],'incomplete':v['incomplete']} for n,v in r.items()}))"
    try:
        inventory_probe_result = subprocess.run([str(environment_python_path), '-I', '-S', '-B', '-c', inventory_probe_code, str(WORKFLOW_ROOT_DIRECTORY), json.dumps(inventory_site_paths)], capture_output=True, text=True, check=True, timeout=60)
        inventory_model_values = json.loads(inventory_probe_result.stdout)
        if not isinstance(inventory_model_values, dict):
            raise ValueError('모델 인벤토리 응답 형식 오류')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unavailable', 'detail': '모델 인벤토리를 읽지 못했습니다.'}
    return {'status': 'file_inventory', 'detail': '파일 존재·크기만 표시하며 모델 준비 완료나 해시 일치를 의미하지 않습니다.', 'models': inventory_model_values}


def collect_environment_site_paths(environment_directory_path):
    """site 설정 코드를 실행하지 않고 경로만 수집한다."""
    current_site_directories = [str(current_site_path) for current_site_path in environment_directory_path.glob('lib/python*/site-packages') if current_site_path.is_dir()]
    reference_counts_record = {'files': 0, 'present': 0, 'missing': 0, 'executable_lines': 0, 'unreadable': 0}
    for reference_file_path in environment_directory_path.glob('lib/python*/site-packages/*.pth'):
        reference_counts_record['files'] += 1
        try:
            if reference_file_path.is_symlink() or reference_file_path.stat().st_size > 1048576:
                raise ValueError('경로 설정을 읽을 수 없습니다.')
            reference_lines_value = reference_file_path.read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeError, ValueError):
            reference_counts_record['unreadable'] += 1
            continue
        for reference_line_value in reference_lines_value:
            reference_line_value = reference_line_value.strip()
            if not reference_line_value or reference_line_value.startswith('#'):
                continue
            if reference_line_value.startswith(('import ', 'import\t')):
                reference_counts_record['executable_lines'] += 1
                continue
            reference_target_path = Path(reference_line_value)
            if not reference_target_path.is_absolute():
                reference_target_path = reference_file_path.parent / reference_target_path
            reference_counts_record['present' if reference_target_path.exists() else 'missing'] += 1
            if reference_target_path.is_dir():
                current_site_directories.append(str(reference_target_path))
    return current_site_directories, reference_counts_record


def inspect_environment_path_references(environment_directory_path):
    return collect_environment_site_paths(environment_directory_path)[1]


def inspect_environment_dependencies(environment_directory_path):
    """site 실행문을 건너뛰고 설치된 배포판 메타데이터만 검사한다."""
    current_python_path = environment_directory_path / 'bin/python'
    if not current_python_path.is_file():
        return {'status': 'unavailable', 'detail': '가상환경 Python이 없습니다.'}
    current_site_paths, current_references_record = collect_environment_site_paths(environment_directory_path)
    current_checker_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_checker_paths, _ = collect_environment_site_paths(current_checker_path)
    # pip 모듈을 불러온 뒤 검사기 경로를 제거해 검사 대상 패키지와 섞이지 않게 한다.
    current_probe_code = "import json,runpy,sys; target=json.loads(sys.argv.pop(1)); checker=json.loads(sys.argv.pop(1)); sys.path[:0]=target+checker; import pip; del sys.path[len(target):len(target)+len(checker)]; sys.argv=['pip','check','--disable-pip-version-check']; runpy.run_module('pip',run_name='__main__')"
    current_probe_environment = {current_key_name: current_value_text for current_key_name, current_value_text in os.environ.items() if not current_key_name.startswith('PIP_')}
    current_probe_environment.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONDONTWRITEBYTECODE='1')
    try:
        current_probe_result = subprocess.run([str(current_python_path), '-I', '-S', '-B', '-c', current_probe_code, json.dumps(current_site_paths), json.dumps(current_checker_paths)],
            capture_output=True, text=True, check=False, timeout=20, env=current_probe_environment)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return {'status': 'unavailable', 'detail': '의존성 메타데이터 검사 실패 또는 시간 초과'}
    if current_probe_result.returncode not in (0, 1) or (current_probe_result.returncode == 1 and not current_probe_result.stdout.strip()):
        return {'status': 'unavailable', 'detail': 'pip 의존성 검사기를 실행할 수 없습니다.'}
    current_incomplete_scan = bool(current_references_record['executable_lines'] or current_references_record['unreadable'] or current_references_record['missing'])
    current_issue_lines = [current_line_text[:500] for current_line_text in current_probe_result.stdout.splitlines() if current_line_text.strip()]
    if current_probe_result.returncode == 0:
        current_issue_lines = []
    current_status_value = 'unknown' if current_incomplete_scan else 'inconsistent' if current_issue_lines else 'consistent'
    return {'status': current_status_value, 'issues': current_issue_lines[:20], 'truncated': len(current_issue_lines) > 20,
            'detail': '설치 메타데이터만 검사; 건너뛴 site 실행문·누락 경로가 있으면 확정하지 않음'}


def inspect_kimodo_environment(environment_python_path, include_dependency_check=False):
    """Kimodo 소유 경로 계약으로 전용 환경을 찾고 패키지 발견 여부를 확인한다."""
    if not environment_python_path.is_file():
        return {'status': 'unknown', 'detail': '관리 Python이 없어 Kimodo 경로 계약을 읽지 못했습니다.'}
    kimodo_site_paths, _ = collect_environment_site_paths(environment_python_path.parent.parent)
    kimodo_probe_code = "import json,sys; sys.path[:0]=[sys.argv[1]]+json.loads(sys.argv[2]); from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON; print(KIMODO_ENVIRONMENT_PYTHON)"
    try:
        kimodo_probe_result = subprocess.run([str(environment_python_path), '-I', '-S', '-B', '-c', kimodo_probe_code, str(WORKFLOW_ROOT_DIRECTORY), json.dumps(kimodo_site_paths)], capture_output=True, text=True, check=True, timeout=10)
        kimodo_python_path = Path(kimodo_probe_result.stdout.strip())
        if not kimodo_python_path.is_absolute() or kimodo_python_path.name != 'python':
            raise ValueError('Kimodo Python 경로 형식 오류')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unknown', 'detail': 'Kimodo 경로 계약을 읽지 못했습니다.'}
    kimodo_environment_record = inspect_management_python(kimodo_python_path.parent.parent, ('torch', 'transformers', 'peft'))
    kimodo_environment_record['path_references'] = inspect_environment_path_references(kimodo_python_path.parent.parent)
    kimodo_environment_record['detail'] = '패키지 발견 여부만 확인; 버전·ROCm·모델·GPU 실행은 별도 검증'
    kimodo_environment_record['optional_for'] = 'kimodo'
    if include_dependency_check:
        kimodo_environment_record['dependencies'] = inspect_environment_dependencies(kimodo_python_path.parent.parent)
    return kimodo_environment_record


def inspect_generator_environment(environment_python_path, selected_service_name, include_dependency_check=False):
    """기존 서비스 계약에서 전용 Python을 찾고 패키지와 선택적 메타데이터를 검사한다."""
    current_service_probes = {
        'wan22-fun-control': ("from generators.wan_fun.contracts import FUN_PYTHON_EXECUTABLE; print(FUN_PYTHON_EXECUTABLE)", ('torch', 'migraphx', 'onnxruntime')),
        'music-heartmula': ("from generators.music.contracts import resolve_music_paths; print(resolve_music_paths('music-heartmula')[2])", ('torch', 'transformers', 'heartlib')),
        'sfx-dasheng-audiogen': ("from generators.music.contracts import resolve_music_paths; print(resolve_music_paths('sfx-dasheng-audiogen')[2])", ('torch', 'transformers', 'soundfile')),
    }
    if selected_service_name not in current_service_probes or not environment_python_path.is_file():
        return {'status': 'unknown', 'detail': '서비스 Python 경로 계약을 읽을 수 없습니다.'}
    current_site_paths, _ = collect_environment_site_paths(environment_python_path.parent.parent)
    current_contract_code, current_required_modules = current_service_probes[selected_service_name]
    current_probe_code = "import json,sys; sys.path[:0]=[sys.argv[1]]+json.loads(sys.argv[2]); " + current_contract_code
    try:
        current_probe_result = subprocess.run([str(environment_python_path), '-I', '-S', '-B', '-c', current_probe_code,
            str(WORKFLOW_ROOT_DIRECTORY), json.dumps(current_site_paths)], capture_output=True, text=True, check=True, timeout=10)
        current_runtime_python = Path(current_probe_result.stdout.strip())
        if not current_runtime_python.is_absolute() or current_runtime_python.name != 'python':
            raise ValueError('서비스 Python 경로 형식 오류')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unknown', 'detail': '서비스 Python 경로 계약을 읽을 수 없습니다.'}
    current_environment_path = current_runtime_python.parent.parent
    current_environment_record = inspect_management_python(current_environment_path, current_required_modules)
    current_environment_record['path_references'] = inspect_environment_path_references(current_environment_path)
    current_environment_record['optional_for'] = selected_service_name
    current_environment_record['detail'] = '패키지 발견 여부만 확인; 버전·ROCm·모델·GPU 실행은 별도 검증'
    if include_dependency_check:
        current_environment_record['dependencies'] = inspect_environment_dependencies(current_environment_path)
    return current_environment_record


def inspect_image_worker_environment(include_dependency_check=False):
    """관리 Python 설정과 별개인 이미지·영상 작업자의 고정 환경을 확인한다."""
    current_image_path = WORKFLOW_ROOT_DIRECTORY / '.venv'
    current_image_modules = ('torch', 'diffusers', 'transformers', 'accelerate', 'safetensors',
                             'einops', 'imageio', 'imageio_ffmpeg', 'ftfy', 'librosa', 'func_timeout', 'cv2', 'av')
    current_image_record = inspect_management_python(current_image_path, current_image_modules)
    current_image_record.update({'optional_for': 'image, wan22-vace, wan22-animate2',
                                 'next': './scripts/workflow.sh setup --scope image',
                                 'detail': '패키지 발견 여부만 확인; 버전·공식 소스·모델·GPU 실행은 별도 검증'})
    if include_dependency_check:
        current_image_record['dependencies'] = inspect_environment_dependencies(current_image_path)
    return current_image_record


def inspect_system_memory(current_memory_path=Path('/proc/meminfo')):
    """시스템 메모리·스왑을 읽기만 하며 GPU 유휴 여부와 구분한다."""
    from tools.review.common.host_memory_guard import read_memory_field_kib
    try:
        current_total_kib = read_memory_field_kib(current_memory_path, 'MemTotal')
        current_available_kib = read_memory_field_kib(current_memory_path, 'MemAvailable')
        current_swap_total_kib = read_memory_field_kib(current_memory_path, 'SwapTotal')
        current_swap_free_kib = read_memory_field_kib(current_memory_path, 'SwapFree')
        if not 0 <= current_available_kib <= current_total_kib or not 0 <= current_swap_free_kib <= current_swap_total_kib:
            raise ValueError('시스템 메모리 수치 범위 오류')
    except (OSError, ValueError):
        return {'status': 'unknown', 'detail': '시스템 메모리 정보를 읽을 수 없습니다.'}
    return {'status': 'observed', 'total_mib': current_total_kib // 1024,
            'available_mib': current_available_kib // 1024,
            'swap_total_mib': current_swap_total_kib // 1024,
            'swap_used_mib': (current_swap_total_kib - current_swap_free_kib) // 1024,
            'detail': '관측 시점의 시스템 RAM·스왑이며 실행 가능 여부를 보장하지 않습니다.'}


def inspect_gpu_queue_reservations():
    """예약 파일을 수정하지 않고 작업과 설치 예약을 관찰한다."""
    from tools.review.common.gpu_job_queue import GPU_QUEUE_DIRECTORY, is_gpu_queue_executor_alive
    current_active_directory = GPU_QUEUE_DIRECTORY / 'active'
    if current_active_directory.is_symlink():
        return {'status': 'unknown', 'detail': '예약 디렉터리가 심볼릭 링크입니다.'}
    if not current_active_directory.exists():
        return {'status': 'available', 'reservations': []}
    current_reservation_values = []
    try:
        for current_reservation_path in sorted(current_active_directory.glob('*.json')):
            try:
                if current_reservation_path.is_symlink() or current_reservation_path.stat().st_size > 1048576:
                    raise ValueError('예약 파일 형식 오류')
                current_reservation_record = json.loads(current_reservation_path.read_text(encoding='utf-8'))
                current_process_identifier = current_reservation_record.get('pid')
                current_start_token = current_reservation_record.get('pid_start_token')
                current_service_name = current_reservation_record.get('service')
                if type(current_process_identifier) is not int or current_process_identifier <= 1 or not isinstance(current_service_name, str):
                    raise ValueError('예약 식별자 오류')
                if not isinstance(current_start_token, str):
                    current_process_status = 'identity_unknown'
                else:
                    current_process_status = ('observed' if is_gpu_queue_executor_alive(current_process_identifier, current_start_token)
                                              else 'not_seen_check_host')
                current_reservation_values.append({'reservation_file': current_reservation_path.name, 'service': current_service_name, 'pid': current_process_identifier, 'process': current_process_status})
            except (OSError, ValueError, TypeError, AttributeError):
                current_reservation_values.append({'reservation_file': current_reservation_path.name, 'service': 'unknown', 'process': 'unreadable'})
    except OSError:
        return {'status': 'unknown', 'detail': 'GPU 예약 목록을 읽지 못했습니다.'}
    return {'status': 'available', 'reservations': current_reservation_values,
            'detail': '프로세스가 보이지 않아도 호스트에서 자식 작업을 확인하기 전 예약을 삭제하지 마세요.'}


def attach_environment_recovery_guidance(current_checks_record):
    """진단 결과에 실제 지원하는 선택 준비 명령과 보존 조건을 덧붙인다."""
    current_setup_scopes = {'management_ui_python': 'management', 'frontend_source': 'renderer',
        'hermes_mcp': 'hermes-mcp', 'writer_server': 'writer-runtime', 'kimodo_python': 'kimodo-runtime',
        'wan_fun_python': 'wan-fun-runtime', 'heartmula_python': 'heartmula-runtime', 'sfx_python': 'sfx-runtime'}
    for current_check_name, current_scope_name in current_setup_scopes.items():
        current_checks_record[current_check_name]['next'] = './scripts/workflow.sh setup --scope ' + current_scope_name
    current_checks_record['hermes_model']['next'] = './scripts/workflow.sh model status hermes-model'
    current_checks_record['hermes_model']['prepare'] = './scripts/workflow.sh model prepare hermes-model'
    for current_check_name in ('kimodo_python', 'heartmula_python'):
        current_checks_record[current_check_name]['recovery_note'] = '기존 전용 환경은 자동 변경하지 않습니다. 불일치 시 먼저 상태와 기존 파일을 확인·보존하세요.'
    current_checks_record['frontend_source']['recovery_note'] = '렌더러 준비에는 인접 프론트엔드와 Node 의존성이 필요합니다.'
    current_checks_record['writer_server']['recovery_note'] = '준비 범위에는 서버와 작가 모델 두 개가 포함됩니다.'
    return current_checks_record


def inspect_management_port_identity(current_port_number, current_health_path):
    """로컬 서비스가 자체 보고한 역할만 표시하며 프로세스 소유권을 보증하지 않는다."""
    try:
        current_http_opener = build_opener(ProxyHandler({}))
        with current_http_opener.open(f'http://127.0.0.1:{current_port_number}{current_health_path}', timeout=1) as current_http_response:
            if current_http_response.status != 200:
                return {'identity': 'unknown'}
            current_health_record = json.loads(current_http_response.read(4097))
        if not isinstance(current_health_record, dict) or current_health_record.get('status') != 'ok':
            return {'identity': 'unknown'}
        current_reported_role = current_health_record.get('role')
        current_reported_pid = current_health_record.get('pid')
        if current_reported_role not in ('management-gui', 'management-gateway') or type(current_reported_pid) is not int or current_reported_pid <= 1:
            return {'identity': 'unknown'}
        current_identity_record = {'identity': 'self_reported', 'reported_role': current_reported_role, 'reported_pid': current_reported_pid}
        if current_reported_role == 'management-gateway':
            current_feature_values = current_health_record.get('features')
            if isinstance(current_feature_values,list) and len(current_feature_values)<=64 and all(isinstance(current_feature_value,str) and len(current_feature_value)<=100 for current_feature_value in current_feature_values):
                current_identity_record['hermes_gpu_queue'] = 'supported' if 'hermes-gpu-queue-v1' in current_feature_values else 'not_reported'
            else:
                current_identity_record['hermes_gpu_queue'] = 'unknown'
        return current_identity_record
    except (OSError, ValueError, TypeError, UnicodeError):
        return {'identity': 'unknown'}


def inspect_management_environment(include_model_inventory=False, include_dependency_check=False):
    """기본 의존성과 선택 기능의 파일 존재를 보고하며 변경하지 않는다."""
    from generators.writer_agent.prepare import RUNTIME_SERVER_PATH
    from tools.review.common.hermes_model_download import HERMES_MODEL_DIRECTORY, HERMES_MODEL_FILENAME, inspect_hermes_model_files
    from tools.review.domains.hermes_agent.runtime_integrity import verify_hermes_runtime_integrity
    current_runtime_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_ui_path = resolve_management_ui_environment()
    current_frontend_path = Path(os.environ.get('FRONTEND_REPOSITORY_PATH', WORKFLOW_ROOT_DIRECTORY.parent / 'slime-frontend')).expanduser()
    current_hermes_path = WORKFLOW_ROOT_DIRECTORY / '.local/hermes-agent-runtime'
    current_model_path = HERMES_MODEL_DIRECTORY / HERMES_MODEL_FILENAME
    if not current_hermes_path.exists() and not current_hermes_path.is_symlink():
        hermes_source_record = {'status': 'missing'}
    else:
        try:
            verify_hermes_runtime_integrity(current_hermes_path)
            hermes_source_record = {'status': 'source_verified', 'detail': '소스 리비전·변경 여부만 검사; Python 패키지 해시는 미검사'}
        except ValueError as hermes_source_error:
            hermes_source_record = {'status': 'invalid', 'detail': str(hermes_source_error)}
    current_model_status = ('marker_valid' if inspect_hermes_model_files() else
                            'present_unverified' if current_model_path.is_file() else 'missing')
    current_uv_path = current_runtime_path / 'bin/uv'
    current_checks_record = {
        'python': {'status': 'available', 'version': sys.version.split()[0]},
        'management_python': {**inspect_management_python(current_runtime_path, ('yaml', 'jsonschema')), 'next': './scripts/workflow.sh setup --scope management'},
        'management_ui_python': inspect_management_python(current_ui_path, ('fastapi', 'uvicorn', 'psutil')),
        'image_worker_python': inspect_image_worker_environment(include_dependency_check),
        'frontend_source': {'status': 'present' if (current_frontend_path / 'packages/field-renderer/package.json').is_file() else 'missing', 'path': str(current_frontend_path)},
        'bubblewrap': {'status': 'present' if shutil.which('bwrap') else 'missing', 'optional_for': 'hermes'},
        'uv': {'status': 'present' if current_uv_path.is_file() and os.access(current_uv_path, os.X_OK) or shutil.which('uv') else 'missing', 'optional_for': 'hermes'},
        'hermes_source': {**hermes_source_record, 'optional_for': 'hermes', 'next': './scripts/workflow.sh setup --scope hermes-runtime'},
        'hermes_mcp': {**inspect_management_python(WORKFLOW_ROOT_DIRECTORY / '.local/hermes-mcp', ('mcp',)), 'optional_for': 'codex'},
        'hermes_model': {'status': current_model_status, 'detail': 'marker_valid는 이전 해시 검증 후 크기·수정 시각 일치이며 전체 해시는 실행 시 검사', 'optional_for': 'hermes'},
        'writer_server': {'status': 'present_unverified' if RUNTIME_SERVER_PATH.is_file() else 'missing', 'detail': '파일 존재만 확인; 바이너리 해시·GPU 구동은 미검사', 'optional_for': 'hermes'},
        'kimodo_python': inspect_kimodo_environment(current_runtime_path / 'bin/python', include_dependency_check),
        'wan_fun_python': inspect_generator_environment(current_runtime_path / 'bin/python', 'wan22-fun-control', include_dependency_check),
        'heartmula_python': inspect_generator_environment(current_runtime_path / 'bin/python', 'music-heartmula', include_dependency_check),
        'sfx_python': inspect_generator_environment(current_runtime_path / 'bin/python', 'sfx-dasheng-audiogen', include_dependency_check),
        'system_memory': inspect_system_memory(),
        'gpu_reservations': inspect_gpu_queue_reservations(),
    }
    attach_environment_recovery_guidance(current_checks_record)
    for current_port_name, current_port_variable, current_default_port in (('gui_port', 'REVIEW_SERVER_PORT', 8770), ('gateway_port', 'MANAGEMENT_GATEWAY_PORT', 8771)):
        try:
            current_port_value = int(os.environ.get(current_port_variable, current_default_port))
            if not 1 <= current_port_value <= 65535:
                raise ValueError('포트 범위 오류')
            with socket.socket() as current_probe_socket:
                current_probe_socket.settimeout(.2)
                current_connection_result = current_probe_socket.connect_ex(('127.0.0.1', current_port_value))
            current_port_status = 'listening' if current_connection_result == 0 else 'not_listening' if current_connection_result == 111 else 'unknown'
            current_checks_record[current_port_name] = {'status': current_port_status, 'port': current_port_value}
            if current_port_status == 'listening':
                current_health_path = '/management/gui-health' if current_port_name == 'gui_port' else '/management/health'
                current_checks_record[current_port_name].update(inspect_management_port_identity(current_port_value, current_health_path))
        except (ValueError, OSError):
            current_checks_record[current_port_name] = {'status': 'unknown'}
    from tools.review.common.gpu_status import read_gpu_status
    current_gpu_status = read_gpu_status()
    current_checks_record['gpu'] = {'status': current_gpu_status.get('status', 'unavailable')}
    if current_gpu_status.get('status') in ('idle', 'busy'):
        current_checks_record['gpu']['process_count'] = len(current_gpu_status.get('processes', []))
        current_checks_record['gpu']['gtt_free_mib'] = current_gpu_status.get('gtt_free_mib')
        current_checks_record['gpu']['vram_free_mib'] = current_gpu_status.get('vram_free_mib')
    if include_model_inventory:
        current_checks_record['model_inventory'] = inspect_registered_model_inventory(current_runtime_path / 'bin/python')
    print(json.dumps(current_checks_record, ensure_ascii=False, indent=2))
    current_core_ready = current_checks_record['management_python']['status'] == 'present' and current_checks_record['management_ui_python']['status'] == 'present'
    current_inventory_ready = not include_model_inventory or current_checks_record['model_inventory']['status'] == 'file_inventory'
    return 0 if current_core_ready and current_inventory_ready else 1
