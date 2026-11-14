"""소품 전용 Qwen 작업·이력. GPU 실행기는 공용으로 유지한다."""
import subprocess
from urllib.parse import urlsplit

from generators.image.qwen_21_runtime import validate_qwen_model_assets
from tools.review.common.management_transport import send_management_json_response
from tools.review.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT


class PropGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/prop-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/prop-generator'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'prop-generator'

    def validate_prop_rocm_runtime(self):
        current_runtime_probe = [
            str(self.select_generation_python()), '-c',
            'import torch; from diffusers import QwenImage21Pipeline; '
            'import accelerate, transformers, safetensors; raise SystemExit(0 if torch.version.hip and torch.cuda.is_available() else 1)',
        ]
        try:
            subprocess.run(current_runtime_probe, capture_output=True, check=True, timeout=15)
        except (OSError, subprocess.SubprocessError) as current_probe_error:
            raise ValueError('AMD ROCm 실행 환경 준비 필요. .venv의 ROCm PyTorch, GPU 접근 권한, QwenImage21Pipeline을 확인하세요.') from current_probe_error

    def validate_generation_runtime(self, saved_request_record=None):
        try:
            validate_qwen_model_assets()
        except (OSError, ValueError, KeyError, TypeError) as current_model_error:
            raise ValueError(f'소품 모델 파일 준비 필요: {current_model_error}') from current_model_error
        self.validate_prop_rocm_runtime()

    def inspect_prop_model_status(self):
        with self.current_request_lock:
            current_download_status = inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'qwen-21')
        if current_download_status == 'running':
            return {'ready': False, 'message': '공식 비양자화 모델 다운로드 중입니다.', 'preparation_status': current_download_status}
        try:
            validate_qwen_model_assets()
        except (OSError, ValueError, KeyError, TypeError) as current_model_error:
            current_status_message = str(current_model_error)
            if current_download_status == 'failed':
                current_status_message = '모델 다운로드 실패. 모델 준비 로그를 확인한 뒤 다시 시도하세요. ' + current_status_message
            return {'ready': False, 'message': current_status_message, 'preparation_status': current_download_status}
        current_status_message = '공식 비양자화 모델 파일 준비 완료.'
        try:
            self.validate_prop_rocm_runtime()
        except ValueError as current_runtime_error:
            current_status_message += ' ' + str(current_runtime_error)
            current_generation_ready = False
        else:
            current_status_message += ' AMD ROCm GPU와 Qwen 파이프라인을 확인했습니다.'
            current_generation_ready = True
        return {'ready': True, 'generation_ready': current_generation_ready, 'message': current_status_message, 'preparation_status': current_download_status}

    def start_prop_model_download(self):
        with self.current_request_lock:
            if inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'qwen-21') == 'running':
                return {'preparation_status': 'running'}
            try:
                validate_qwen_model_assets()
            except (OSError, ValueError, KeyError, TypeError):
                try:
                    return start_registered_preparation(WORKFLOW_ROOT_PATH, 'qwen-21')
                except OSError as current_start_error:
                    raise ValueError('모델 다운로드를 시작할 수 없습니다.') from current_start_error
            return {'preparation_status': 'completed'}

    def handle_image_request(self, current_http_handler):
        current_request_path = urlsplit(current_http_handler.path).path
        current_command_payload = getattr(current_http_handler, 'management_command_payload', None)
        if current_command_payload is not None:
            if current_http_handler.command == 'GET' and current_request_path == self.route_prefix_value+'/model-status':
                send_management_json_response(current_http_handler, 200, self.inspect_prop_model_status())
                return True
            if current_http_handler.command == 'POST' and current_request_path == self.route_prefix_value+'/jobs' and isinstance(current_command_payload, dict) and current_command_payload.get('action') == 'prepare':
                if current_command_payload != {'action': 'prepare'}:
                    raise ValueError('소품 모델 준비는 추가 입력을 받지 않습니다.')
                send_management_json_response(current_http_handler, 200, self.start_prop_model_download())
                return True
        return super().handle_image_request(current_http_handler)
