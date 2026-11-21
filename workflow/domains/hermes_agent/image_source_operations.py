"""기존 이미지 생성기의 원본 작업을 복구 없이 관측한다."""
from importlib import import_module
from pathlib import Path
from workflow.common.source_history_catalog import SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES,SOURCE_HISTORY_SERVICE_ALIASES
from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record,validate_service_job_identifier
from workflow.domains.hermes_agent.failure_observer import observe_hermes_generator_failure

IMAGE_SOURCE_SERVICES=(*SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES,'floor-tile')
IMAGE_SOURCE_MANAGER_RECORDS={
    'qwen-21':('workflow.domains.image.qwen_21_generation','QwenPlainGenerationManager'),
    'qwen-21-circular':('workflow.domains.image.qwen_circular_generation','QwenCircularGenerationManager'),
    'mannequin-generator':('workflow.domains.image.mannequin_generation','MannequinGenerationManager'),
    'billboard-generator':('workflow.domains.image.billboard_generation','BillboardGuideGenerationManager'),
    'prop-generator':('workflow.domains.image.prop_generation','PropGenerationManager'),
    'vegetation-generator':('workflow.domains.image.vegetation_generation','VegetationGenerationManager'),
    'expression':('workflow.domains.image.expression_generation','ExpressionGenerationManager'),
    'seamless-tile':('workflow.domains.image.seamless_generation','SeamlessGenerationManager'),
    'floor-tile':('workflow.domains.tile.floor_generation','FloorGenerationManager'),
}


def resolve_image_source_service(current_service_name,current_job_identifier):
    if not isinstance(current_service_name,str) or current_service_name not in IMAGE_SOURCE_SERVICES or not validate_service_job_identifier(current_service_name,current_job_identifier):raise ValueError('이미지 원본 서비스 또는 작업 ID 오류')
    current_owner_name=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
    if current_owner_name not in IMAGE_SOURCE_MANAGER_RECORDS:raise ValueError('이미지 원본 소유 서비스 오류')
    return current_owner_name


def make_image_source_manager(current_owner_name):
    current_module_name,current_class_name=IMAGE_SOURCE_MANAGER_RECORDS[current_owner_name]
    return getattr(import_module(current_module_name),current_class_name)()


def read_hermes_image_source_job(current_service_name,current_job_identifier):
    current_owner_name=resolve_image_source_service(current_service_name,current_job_identifier)
    current_manager_value=make_image_source_manager(current_owner_name)
    current_storage_root=Path(current_manager_value.job_storage_root)
    current_job_root=current_storage_root/current_job_identifier
    if current_storage_root.is_symlink() or not current_storage_root.is_dir() or current_job_root.is_symlink() or not current_job_root.is_dir() or current_job_root.resolve().parent!=current_storage_root.resolve():raise ValueError('이미지 원본 작업 경로 오류')
    current_status_path=current_job_root/'status.json'
    current_status_record=read_bounded_delegation_record(current_status_path)
    if not isinstance(current_status_record,dict):raise ValueError('이미지 원본 상태 형식 오류')
    current_status_value=current_status_record.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):current_status_value='unknown'
    current_image_path=current_job_root/'result.png'
    current_image_url=MANAGEMENT_SERVICE_ROUTES[current_owner_name]+'/jobs/'+current_job_identifier+'/result.png' if current_status_value=='completed' and not current_image_path.is_symlink() and current_image_path.is_file() else None
    if read_bounded_delegation_record(current_status_path)!=current_status_record:raise ValueError('이미지 상태가 조회 중 변경되었습니다.')
    return {'source_service':current_owner_name,'status':current_status_value,'image':current_image_url,'result_status':'available' if current_image_url else 'unavailable' if current_status_value=='completed' else 'not_ready','note':'기록과 조회 시점의 파일 존재만 확인합니다. 이미지 내용·품질과 프로세스 생존은 별도 확인하세요.',**observe_hermes_generator_failure(current_status_value,current_status_record.get('error'))}


def validate_hermes_image_source_response(current_service_name,current_job_identifier,current_response_value):
    current_owner_name=resolve_image_source_service(current_service_name,current_job_identifier)
    if not isinstance(current_response_value,dict) or current_response_value.get('service')!=current_service_name or current_response_value.get('job_id')!=current_job_identifier or not isinstance(current_response_value.get('job'),dict):raise ValueError('이미지 원본 상태 응답 불일치')
    current_job_record=current_response_value['job']
    if current_job_record.get('source_service')!=current_owner_name or current_job_record.get('status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):raise ValueError('이미지 소유 서비스 또는 상태 오류')
    current_expected_path=MANAGEMENT_SERVICE_ROUTES[current_owner_name]+'/jobs/'+current_job_identifier+'/result.png'
    current_image_path=current_job_record.get('image')
    if current_image_path is not None and (current_job_record['status']!='completed' or current_image_path!=current_expected_path):raise ValueError('이미지 결과 경로 오류')
    current_expected_status=('available' if current_image_path else 'unavailable') if current_job_record['status']=='completed' else 'not_ready'
    if current_job_record.get('result_status')!=current_expected_status:raise ValueError('이미지 결과 상태 오류')
    return current_job_record
