"""H3 Image requests use the common image history and GPU queue."""
import json
from urllib.parse import urlsplit

from generators.minimax_h3_image.contracts import STORAGE, PYTHON, inspect_runtime, validate_request
from workflow.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT
from workflow.common.management_transport import send_management_json_response


class MiniMaxH3ImageManager(ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/minimax-h3-image'
        self.job_storage_root = STORAGE

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/minimax_h3_image/worker.py'

    def select_generation_python(self, saved_request_record=None):
        return PYTHON

    def select_generation_service(self, saved_request_record=None):
        return 'minimax-h3-image'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'minimax-h3-image'

    def validate_generation_request(self, request):
        return validate_request(request)

    def validate_generation_runtime(self, saved_request_record=None):
        state = inspect_runtime()
        if not state['generation_ready']:
            raise ValueError(state['message'])

    def enrich_generation_status(self, job_root, status):
        path = job_root / 'request.json'
        if path.is_symlink() or not path.is_file():
            raise ValueError('저장된 입력을 확인할 수 없습니다.')
        return {**status, 'id': job_root.name, 'request': json.loads(path.read_text(encoding='utf-8'))}

    def handle_image_request(self, handler):
        path = urlsplit(handler.path).path
        if handler.command == 'POST' and path in (self.route_prefix_value + '/building-review/send', self.route_prefix_value + '/building-review/read'):
            try:
                from workflow.domains.minimax_h3_image.building_candidates import send_candidate, read_candidate
                payload = getattr(handler, 'management_command_payload', None)
                if not isinstance(payload, dict):
                    raise ValueError('요청을 확인하세요.')
                candidate_root = self.job_storage_root.parent / 'building-review-candidates'
                result = send_candidate(self.job_storage_root, candidate_root, payload.get('id')) if path.endswith('/send') else read_candidate(candidate_root, payload.get('id'), payload.get('sha256'))
                send_management_json_response(handler, 200, result)
            except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
                send_management_json_response(handler, 400, {'error': str(error)})
            return True
        if handler.command == 'GET' and urlsplit(handler.path).path == self.route_prefix_value + '/model-status':
            send_management_json_response(handler, 200, inspect_runtime())
            return True
        if handler.command == 'POST' and urlsplit(handler.path).path == self.route_prefix_value + '/preview':
            try:
                payload = getattr(handler, 'management_command_payload', None)
                if payload is None:
                    size = int(handler.headers.get('Content-Length', '0'))
                    if not 0 < size <= 40200000:
                        raise ValueError('요청 크기 오류')
                    from workflow.common.management_gateway import parse_management_request_json
                    payload = parse_management_request_json(handler.rfile.read(size))
                result = validate_request(payload)
                send_management_json_response(handler, 200, {'prompt': result['prompt'], 'prompt_sha256': result['prompt_sha256']})
            except (ValueError, TypeError, UnicodeError) as error:
                send_management_json_response(handler, 400, {'error': str(error)})
            return True
        return super().handle_image_request(handler)
