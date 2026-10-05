"""게이트웨이의 서비스 조립과 수명 관리. 명령 등록부는 공용 게이트웨이를 따른다."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, ManagementCommandGateway
from tools.review.common.record_folders import handle_record_folder_request


@dataclass(frozen=True)
class ManagementServiceBinding:
    """한 서비스의 HTTP 처리와 기존 기록 저장소를 함께 연결한다."""

    request_handler_callback: Callable
    record_storage_root: Path
    record_path_resolver: Callable


class ManagementServiceRuntime:
    def __init__(self, service_binding_records, legacy_request_handler, runtime_cleanup_callback):
        expected_service_names = set(MANAGEMENT_SERVICE_ROUTES)
        actual_service_names = set(service_binding_records)
        if actual_service_names != expected_service_names:
            raise ValueError(f'관리 서비스 연결 불일치: missing={sorted(expected_service_names - actual_service_names)}, unknown={sorted(actual_service_names - expected_service_names)}')
        self.service_binding_records = dict(service_binding_records)
        self.legacy_request_handler = legacy_request_handler
        self.runtime_cleanup_callback = runtime_cleanup_callback
        self.runtime_closed_flag = False
        self.management_command_gateway = ManagementCommandGateway({
            service_command_name: service_binding_record.request_handler_callback
            for service_command_name, service_binding_record in self.service_binding_records.items()
        })
        self.record_folder_routes = {
            MANAGEMENT_SERVICE_ROUTES[service_command_name]: (service_binding_record.record_storage_root, service_binding_record.record_path_resolver)
            for service_command_name, service_binding_record in self.service_binding_records.items()
        }

    def dispatch_runtime_request(self, current_http_handler):
        if self.runtime_closed_flag:
            raise RuntimeError('종료된 관리 서비스에는 요청할 수 없습니다.')
        if current_http_handler.command == 'POST' and handle_record_folder_request(current_http_handler, self.record_folder_routes):
            return True
        if self.management_command_gateway.handle(current_http_handler):
            return True
        request_route_path = urlsplit(current_http_handler.path).path
        for service_command_name, service_route_prefix in MANAGEMENT_SERVICE_ROUTES.items():
            if request_route_path == service_route_prefix or request_route_path.startswith(service_route_prefix + '/'):
                return self.service_binding_records[service_command_name].request_handler_callback(current_http_handler)
        # 작가 에이전트는 기존 별도 HTTP 계약을 보존한다.
        return self.legacy_request_handler(current_http_handler)

    def close_runtime_services(self):
        if not self.runtime_closed_flag:
            self.runtime_closed_flag = True
            self.runtime_cleanup_callback()


def bind_stored_management_service(request_handler_callback, record_storage_root):
    """저장 루트 바로 아래에 생성 ID를 두는 서비스의 경로 계약."""
    def resolve_stored_record(record_identifier_value):
        return record_storage_root / record_identifier_value
    return ManagementServiceBinding(request_handler_callback, record_storage_root, resolve_stored_record)


def create_management_runtime(writer_workspace_config=None):
    from tools.review.domains.image.image_generation import ImageGenerationManager
    from tools.review.domains.image.seamless_generation import SeamlessGenerationManager
    from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
    from tools.review.domains.image.pose_transfer_generation import PoseTransferGenerationManager
    from tools.review.domains.image.outfit_transfer_generation import OutfitTransferGenerationManager
    from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager
    from tools.review.domains.image.animation_separation import AnimationSeparationManager
    from tools.review.domains.image.expression_generation import ExpressionGenerationManager
    from generators.writer_agent.management import WriterAgentManager
    from generators.writer_agent.documents import DEFAULT_WORKSPACE_CONFIG
    from tools.review.domains.tile.floor_generation import FloorGenerationManager
    from tools.review.domains.anny.anny_attributes import AnnyAttributeManager, JOBS as ANNY_RECORD_DIRECTORY
    from tools.review.domains.momask.momask_generation import MoMaskGenerationManager
    from tools.review.domains.character_animation.character_animation import CharacterAnimationManager
    from tools.review.domains.character_animation.character_animation_jobs import GENERATION_ROOT_DIRECTORY, resolve_generation_directory
    from tools.review.domains.momask.momask_jobs import GENERATION_JOB_DIRECTORY as MOMASK_RECORD_DIRECTORY, resolve_generation_directory as resolve_momask_record_directory

    writer_agent_service = WriterAgentManager(writer_workspace_config or DEFAULT_WORKSPACE_CONFIG)
    try:
        image_generation_service = ImageGenerationManager()
        seamless_generation_service = SeamlessGenerationManager()
        qwen_circular_service = QwenCircularGenerationManager()
        qwen_plain_service = QwenPlainGenerationManager()
        pose_transfer_service = PoseTransferGenerationManager()
        outfit_transfer_service = OutfitTransferGenerationManager()
        animation_separation_service = AnimationSeparationManager()
        expression_generation_service = ExpressionGenerationManager()
        three_reference_service = ImageGenerationManager(three_reference_mode=True)
        floor_generation_service = FloorGenerationManager()
        anny_attribute_service = AnnyAttributeManager()
        momask_generation_service = MoMaskGenerationManager()
        character_animation_service = CharacterAnimationManager()
        service_binding_records = {
            'outfit-transfer': bind_stored_management_service(outfit_transfer_service.handle_image_request, outfit_transfer_service.job_storage_root),
            'pose-transfer': bind_stored_management_service(pose_transfer_service.handle_image_request, pose_transfer_service.job_storage_root),
            'animation-separation': bind_stored_management_service(animation_separation_service.handle_image_request, animation_separation_service.job_storage_root),
            'qwen-21-circular': bind_stored_management_service(qwen_circular_service.handle_image_request, qwen_circular_service.job_storage_root),
            'qwen-21': bind_stored_management_service(qwen_plain_service.handle_image_request, qwen_plain_service.job_storage_root),
            'seamless-tile': bind_stored_management_service(seamless_generation_service.handle_image_request, seamless_generation_service.job_storage_root),
            'expression': bind_stored_management_service(expression_generation_service.handle_image_request, expression_generation_service.job_storage_root),
            'floor-tile': bind_stored_management_service(floor_generation_service.handle_image_request, floor_generation_service.job_storage_root),
            'qwen-2512': bind_stored_management_service(image_generation_service.handle_image_request, image_generation_service.job_storage_root),
            'qwen-2511': bind_stored_management_service(three_reference_service.handle_image_request, three_reference_service.job_storage_root),
            'anny': bind_stored_management_service(anny_attribute_service.handle, ANNY_RECORD_DIRECTORY),
            'momask': ManagementServiceBinding(momask_generation_service.handle, MOMASK_RECORD_DIRECTORY, resolve_momask_record_directory),
            'character-animation': ManagementServiceBinding(character_animation_service.handle, GENERATION_ROOT_DIRECTORY, resolve_generation_directory),
        }
        return ManagementServiceRuntime(service_binding_records, writer_agent_service.handle_writer_request, writer_agent_service.close_writer_worker)
    except BaseException:
        writer_agent_service.close_writer_worker()
        raise
