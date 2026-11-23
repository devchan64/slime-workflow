"""게이트웨이의 서비스 조립과 수명 관리. 명령 등록부는 공용 게이트웨이를 따른다."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, ManagementCommandGateway
from workflow.common.record_folders import handle_record_folder_request
from workflow.common.history_summaries import handle_history_summaries_request


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
        if current_http_handler.command == 'POST' and handle_history_summaries_request(current_http_handler, self.record_folder_routes):
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


def build_building_compatibility_handler(billboard_generation_service):
    """기존 건물 URL을 동일한 빌보드 작업 서비스로 연결한다."""
    def handle_building_compatibility_request(current_http_handler):
        original_request_path = current_http_handler.path
        current_http_handler.path = '/billboard-generator' + original_request_path[len('/building-generator'):]
        try:
            return billboard_generation_service.handle_image_request(current_http_handler)
        finally:
            current_http_handler.path = original_request_path
    return handle_building_compatibility_request


def create_management_runtime(writer_workspace_config=None):
    from workflow.domains.image.image_generation import ImageGenerationManager
    from workflow.domains.image.seamless_generation import SeamlessGenerationManager
    from workflow.domains.image.qwen_circular_generation import QwenCircularGenerationManager
    from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager
    from workflow.domains.image.billboard_generation import BillboardGuideGenerationManager
    from workflow.domains.image.prop_generation import PropGenerationManager
    from workflow.domains.image.vegetation_generation import VegetationGenerationManager
    from workflow.domains.image.mannequin_generation import MannequinGenerationManager
    from workflow.domains.image.expression_generation import ExpressionGenerationManager
    from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
    from workflow.domains.image.flux_image_generation import FluxImageGenerationManager, FLUX_IMAGE_PROFILE_RECORDS
    from generators.writer_agent.management import WriterAgentManager
    from generators.writer_agent.documents import DEFAULT_WORKSPACE_CONFIG
    from workflow.domains.tile.floor_generation import FloorGenerationManager
    from workflow.common.retired_momask import RetiredMoMaskHandler, reject_retired_record_access
    from workflow.domains.character_animation.character_animation import CharacterAnimationManager
    from workflow.domains.character_animation.character_animation_jobs import GENERATION_ROOT_DIRECTORY, resolve_generation_directory

    from workflow.domains.map_assets.resize import handle_map_resize_request, RESIZE_STORAGE_DIRECTORY
    from workflow.domains.map_review.capture import handle_map_capture_request
    from workflow.domains.character_review.capture import handle_character_capture_request, CAPTURE_STORAGE_DIRECTORY

    from workflow.domains.wan_animate2.generation import AnimateTwoGenerationManager
    from workflow.domains.dwpose.generation import DwposeGenerationManager
    from workflow.domains.wan_fun.generation import FunControlGenerationManager
    from workflow.domains.kimodo.generation import KimodoGenerationManager
    from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
    from generators.music.contracts import AUDIO_SERVICE_NAMES
    from workflow.domains.music.generation import MusicGenerationManager
    from workflow.domains.translation.service import TranslationServiceManager
    from workflow.domains.hermes_agent.service import HermesServiceManager
    from workflow.common.model_download_records import MODEL_DOWNLOAD_RECORD_ROOT
    writer_agent_service = WriterAgentManager(writer_workspace_config or DEFAULT_WORKSPACE_CONFIG)
    current_chat_dispatcher_stop = None
    current_handoff_scheduler_stop = None
    try:
        animate_two_service = AnimateTwoGenerationManager()
        dwpose_generation_service = DwposeGenerationManager()
        fun_generation_service = FunControlGenerationManager()
        kimodo_generation_service = KimodoGenerationManager()
        vace_generation_service = VaceVideoGenerationManager()
        seamless_generation_service = SeamlessGenerationManager()
        qwen_circular_service = QwenCircularGenerationManager()
        qwen_plain_service = QwenPlainGenerationManager()
        billboard_generation_service = BillboardGuideGenerationManager()
        prop_generation_service = PropGenerationManager()
        vegetation_generation_service = VegetationGenerationManager()
        mannequin_generation_service = MannequinGenerationManager()
        expression_generation_service = ExpressionGenerationManager()
        flux_expression_service = FluxExpressionGenerationManager()
        three_reference_service = ImageGenerationManager(three_reference_mode=True)
        floor_generation_service = FloorGenerationManager()
        momask_generation_service = RetiredMoMaskHandler()
        character_animation_service = CharacterAnimationManager()
        handle_building_compatibility_request = build_building_compatibility_handler(billboard_generation_service)
        def reject_writer_folder_access(current_record_identifier):
            raise ValueError('작가 기록은 writer-detail 명령으로 조회하세요.')
        def reject_model_download_folder(current_record_identifier):
            raise ValueError('모델 다운로드 기록은 상태 명령으로 조회하세요.')
        def handle_model_download_request(current_http_handler):
            return False
        service_binding_records = {
            'hermes-model': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'animationgpt': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'model-downloads': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'expression-lora': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'wan22-fighting-lora': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'wan22-vace-lightning': ManagementServiceBinding(handle_model_download_request, MODEL_DOWNLOAD_RECORD_ROOT, reject_model_download_folder),
            'writer-agent': ManagementServiceBinding(writer_agent_service.handle_writer_request,writer_agent_service.workspace_config_path.parent,reject_writer_folder_access),
            'wan22-animate2': bind_stored_management_service(animate_two_service.handle_image_request,animate_two_service.job_storage_root),
            'dwpose': bind_stored_management_service(dwpose_generation_service.handle_image_request,dwpose_generation_service.job_storage_root),
            'wan22-fun-control': bind_stored_management_service(fun_generation_service.handle_image_request,fun_generation_service.job_storage_root),
            'kimodo': bind_stored_management_service(kimodo_generation_service.handle_image_request,kimodo_generation_service.job_storage_root),
            'wan22-vace': bind_stored_management_service(vace_generation_service.handle_image_request,vace_generation_service.job_storage_root),
            'map-assets': bind_stored_management_service(handle_map_resize_request,RESIZE_STORAGE_DIRECTORY),
            'map-review': bind_stored_management_service(handle_map_capture_request,CAPTURE_STORAGE_DIRECTORY),
            'character-review': bind_stored_management_service(handle_character_capture_request,CAPTURE_STORAGE_DIRECTORY),
            'qwen-21-circular': bind_stored_management_service(qwen_circular_service.handle_image_request, qwen_circular_service.job_storage_root),
            'billboard-generator': bind_stored_management_service(billboard_generation_service.handle_image_request, billboard_generation_service.job_storage_root),
            'prop-generator': bind_stored_management_service(prop_generation_service.handle_image_request, prop_generation_service.job_storage_root),
            'mannequin-generator': bind_stored_management_service(mannequin_generation_service.handle_image_request, mannequin_generation_service.job_storage_root),
            'vegetation-generator': bind_stored_management_service(vegetation_generation_service.handle_image_request, vegetation_generation_service.job_storage_root),
            'building-generator': bind_stored_management_service(handle_building_compatibility_request, billboard_generation_service.job_storage_root),
            'qwen-21': bind_stored_management_service(qwen_plain_service.handle_image_request, qwen_plain_service.job_storage_root),
            'seamless-tile': bind_stored_management_service(seamless_generation_service.handle_image_request, seamless_generation_service.job_storage_root),
            'expression': bind_stored_management_service(expression_generation_service.handle_image_request, expression_generation_service.job_storage_root),
            'flux-expression': bind_stored_management_service(flux_expression_service.handle_image_request, flux_expression_service.job_storage_root),
            'floor-tile': bind_stored_management_service(floor_generation_service.handle_image_request, floor_generation_service.job_storage_root),
            'qwen-2511': bind_stored_management_service(three_reference_service.handle_image_request, three_reference_service.job_storage_root),
            'momask': ManagementServiceBinding(momask_generation_service.handle, Path(__file__).resolve().parents[2]/'.tmp/momask-generator/jobs', reject_retired_record_access),
            'character-animation': ManagementServiceBinding(character_animation_service.handle, GENERATION_ROOT_DIRECTORY, resolve_generation_directory),
        }
        current_translation_service = TranslationServiceManager()
        service_binding_records['prompt-translation'] = bind_stored_management_service(current_translation_service.handle_translation_request, current_translation_service.job_storage_root)
        current_hermes_service = HermesServiceManager()
        current_chat_dispatcher_stop = current_hermes_service.start_chat_queue_dispatcher()
        service_binding_records['hermes-agent'] = bind_stored_management_service(current_hermes_service.handle_hermes_request, current_hermes_service.hermes_storage_root)
        for current_flux_profile in FLUX_IMAGE_PROFILE_RECORDS:
            current_flux_manager = FluxImageGenerationManager(current_flux_profile)
            service_binding_records[current_flux_profile] = bind_stored_management_service(current_flux_manager.handle_image_request, current_flux_manager.job_storage_root)
        for current_service_name in AUDIO_SERVICE_NAMES:
            current_music_manager = MusicGenerationManager(current_service_name)
            service_binding_records[current_service_name] = bind_stored_management_service(current_music_manager.handle_music_request,current_music_manager.job_storage_root)
        def close_services():
            current_chat_dispatcher_stop.set()
            if current_handoff_scheduler_stop is not None:
                current_handoff_scheduler_stop.set()
            writer_agent_service.close_writer_worker()
        current_runtime = ManagementServiceRuntime(service_binding_records, writer_agent_service.handle_writer_request, close_services)
        from workflow.domains.hermes_agent.gpu_handoff_scheduler import start_gpu_handoff_scheduler
        current_handoff_scheduler_stop = start_gpu_handoff_scheduler(current_hermes_service)
        return current_runtime
    except BaseException:
        if current_chat_dispatcher_stop is not None:
            current_chat_dispatcher_stop.set()
        if current_handoff_scheduler_stop is not None:
            current_handoff_scheduler_stop.set()
        writer_agent_service.close_writer_worker()
        raise
