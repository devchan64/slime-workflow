"""DWPose와 Wan 영상 작업을 기존 검증·GPU 대기열로 위임한다."""
import json
import os
import re
from tools.management.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.management.common.management_gateway import execute_management_command
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.management.domains.hermes_agent.failure_observer import observe_hermes_generator_failure

from tools.management.common.source_history_catalog import SOURCE_HISTORY_VIDEO_SERVICES
HERMES_VIDEO_SERVICES = SOURCE_HISTORY_VIDEO_SERVICES
HERMES_VIDEO_SOURCE_SERVICES = (*HERMES_VIDEO_SERVICES,'kimodo')
HERMES_VIDEO_REQUEST_LIMIT = 39_000_000


def validate_hermes_video_service(current_service_name):
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_VIDEO_SERVICES:
        raise ValueError('지원하는 동작·영상 생성 서비스가 아닙니다.')


def make_hermes_video_manager(current_service_name):
    validate_hermes_video_service(current_service_name)
    if current_service_name=='dwpose':
        from tools.management.domains.dwpose.generation import DwposeGenerationManager
        return DwposeGenerationManager()
    if current_service_name=='wan22-animate2':
        from tools.management.domains.wan_animate2.generation import AnimateTwoGenerationManager
        return AnimateTwoGenerationManager()
    if current_service_name=='wan22-fun-control':
        from tools.management.domains.wan_fun.generation import FunControlGenerationManager
        return FunControlGenerationManager()
    from tools.management.domains.wan_vace.generation import VaceVideoGenerationManager
    return VaceVideoGenerationManager()


def validate_hermes_video_request(current_service_name,current_request_record):
    validate_hermes_video_service(current_service_name)
    if not isinstance(current_request_record,dict) or current_request_record.get('action')!='generate':
        raise ValueError('동작·영상 위임에는 생성 요청만 허용합니다.')
    try:
        current_encoded_size=len(json.dumps(current_request_record,ensure_ascii=False,allow_nan=False).encode())
    except (TypeError,ValueError) as current_request_error:
        raise ValueError('동작·영상 요청 JSON 오류') from current_request_error
    if current_encoded_size>HERMES_VIDEO_REQUEST_LIMIT:
        raise ValueError('첨부를 포함한 요청은 39MB 이하여야 합니다.')
    return make_hermes_video_manager(current_service_name).validate_generation_request(current_request_record)


def call_hermes_video_service(current_service_name,current_command_name,current_payload_record):
    validate_hermes_video_service(current_service_name)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command(current_service_name,current_command_name,current_payload_record,current_gateway_address)


def submit_hermes_video_request(current_request_identifier,current_service_name,current_request_record):
    validate_hermes_video_service(current_service_name)
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,current_service_name,current_request_record,
        lambda current_request_value:call_hermes_video_service(current_service_name,'generate',current_request_value),
        lambda current_request_value:validate_hermes_video_request(current_service_name,current_request_value))


def read_hermes_video_status(current_request_identifier,current_service_name):
    validate_hermes_video_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    current_job_value=call_hermes_video_service(current_service_name,'status',{'id':current_receipt_value['job_id']})
    if not isinstance(current_job_value,dict) or ('id' in current_job_value and current_job_value['id']!=current_receipt_value['job_id']):
        raise ValueError('동작·영상 상태 응답 또는 작업 ID 오류')
    current_status_value=current_job_value.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):
        current_status_value='unknown'
    from tools.management.domains.hermes_agent.media_result_paths import validate_hermes_video_result_paths
    current_result_paths=validate_hermes_video_result_paths(current_service_name,current_receipt_value['job_id'],{**current_job_value,'status':current_status_value})
    current_result_count=sum(current_value is not None for current_value in current_result_paths.values())
    current_result_status=('available' if current_result_count==3 else 'partial' if current_result_count else 'unavailable') if current_status_value=='completed' else 'not_ready'
    current_output_value={'status':current_status_value,**current_result_paths,'result_status':current_result_status}
    current_output_value.update(observe_hermes_generator_failure(current_status_value,current_job_value.get('error')))
    current_output_value['note']='상태 조회가 중단 작업 복구를 수행할 수 있습니다. 결과와 상세 로그는 해당 생성기에서 확인하세요.'
    return {'receipt':current_receipt_value,'job':current_output_value}


def validate_hermes_video_source_service(current_service_name):
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_VIDEO_SOURCE_SERVICES:
        raise ValueError('지원하는 동작·영상 원본 서비스가 아닙니다.')


def make_hermes_video_source_manager(current_service_name):
    validate_hermes_video_source_service(current_service_name)
    if current_service_name=='kimodo':
        from tools.management.domains.kimodo.generation import KimodoGenerationManager
        return KimodoGenerationManager()
    return make_hermes_video_manager(current_service_name)


def read_hermes_video_source_job(current_service_name,current_job_identifier):
    """원본 상태·결과 파일만 관측하며 중단 작업 복구를 실행하지 않는다."""
    from pathlib import Path
    from tools.management.domains.hermes_agent.delegation_store import read_bounded_delegation_record,validate_service_job_identifier
    validate_hermes_video_source_service(current_service_name)
    if not validate_service_job_identifier(current_service_name,current_job_identifier):raise ValueError('영상 원본 작업 ID 형식 오류')
    current_manager_value=make_hermes_video_source_manager(current_service_name)
    current_storage_root=Path(current_manager_value.job_storage_root)
    current_job_root=current_storage_root/current_job_identifier
    if current_storage_root.is_symlink() or not current_storage_root.is_dir() or current_job_root.is_symlink() or not current_job_root.is_dir() or current_job_root.resolve().parent!=current_storage_root.resolve():raise ValueError('영상 원본 작업 경로 오류')
    current_status_path=current_job_root/'status.json'
    current_status_record=read_bounded_delegation_record(current_status_path)
    if not isinstance(current_status_record,dict):raise ValueError('영상 원본 상태 형식 오류')
    current_status_value=current_status_record.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):current_status_value='unknown'
    current_result_paths={'video':None,'image':None,'download':None}
    current_result_record=None
    if current_status_value=='completed':
        try:
            current_result_record=read_bounded_delegation_record(current_job_root/'result.json')
            current_attempt_identifier=current_result_record.get('attempt') if isinstance(current_result_record,dict) else None
            if not isinstance(current_attempt_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_attempt_identifier):raise ValueError('영상 실행 시도 오류')
            current_attempts_root=current_job_root/'attempts'
            current_attempt_root=current_attempts_root/current_attempt_identifier
            if current_attempts_root.is_symlink() or current_attempt_root.is_symlink() or not current_attempt_root.is_dir() or current_attempt_root.resolve().parent!=current_attempts_root.resolve():raise ValueError('영상 결과 폴더 오류')
            for current_result_name in ('preview.mp4','output-000.png','frames.zip'):
                current_result_path=current_attempt_root/current_result_name
                if current_result_path.is_symlink() or not current_result_path.is_file():raise ValueError('영상 결과 파일 오류')
            current_result_base='/'+current_service_name+'/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/'
            current_result_paths={'video':current_result_base+'preview.mp4','image':current_result_base+'output-000.png','download':current_result_base+'frames.zip'}
        except (OSError,ValueError,TypeError,KeyError):
            pass
    if read_bounded_delegation_record(current_status_path)!=current_status_record:raise ValueError('영상 상태가 조회 중 변경되었습니다.')
    if all(current_result_paths.values()) and read_bounded_delegation_record(current_job_root/'result.json')!=current_result_record:raise ValueError('영상 결과가 조회 중 변경되었습니다.')
    current_result_status=('available' if all(current_result_paths.values()) else 'unavailable') if current_status_value=='completed' else 'not_ready'
    return {'status':current_status_value,**current_result_paths,'result_status':current_result_status,'note':'기록만 조회하며 중단 상태 복구는 하지 않습니다. 파일 존재는 조회 시점 기준이며 내용·재생과 프로세스 생존은 별도 확인하세요.',**observe_hermes_generator_failure(current_status_value,current_status_record.get('error'))}


def validate_hermes_video_source_response(current_service_name,current_job_identifier,current_response_value):
    """원본 영상 응답의 서비스·작업·상태와 결과 경로를 검사한다."""
    from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
    from tools.management.domains.hermes_agent.media_result_paths import validate_hermes_video_result_paths
    validate_hermes_video_source_service(current_service_name)
    if not validate_service_job_identifier(current_service_name,current_job_identifier):raise ValueError('영상 원본 작업 ID 오류')
    if not isinstance(current_response_value,dict) or current_response_value.get('service')!=current_service_name or current_response_value.get('job_id')!=current_job_identifier or not isinstance(current_response_value.get('job'),dict):raise ValueError('영상 원본 상태 응답 불일치')
    current_job_record=current_response_value['job']
    if current_job_record.get('status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):raise ValueError('영상 상태 오류')
    current_result_paths=validate_hermes_video_result_paths(current_service_name,current_job_identifier,current_job_record)
    if any(current_job_record.get(current_field_name)!=current_result_paths[current_field_name] for current_field_name in current_result_paths):raise ValueError('영상 결과 경로 오류')
    current_expected_status=('available' if all(current_result_paths.values()) else 'unavailable') if current_job_record['status']=='completed' else 'not_ready'
    if current_job_record.get('result_status')!=current_expected_status:raise ValueError('영상 결과 상태 오류')
    return current_job_record


def list_hermes_video_receipts(current_service_name):
    validate_hermes_video_service(current_service_name)
    return HermesDelegationStore().list_service_delegations(current_service_name)


def cancel_hermes_video_request(current_request_identifier,current_service_name,current_job_identifier):
    validate_hermes_video_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('접수 기록과 확인한 영상 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_video_service(current_service_name,'cancel',{'id':current_job_identifier})
    if (not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True
            or ('id' in current_cancel_value and current_cancel_value['id']!=current_job_identifier)):
        raise ValueError('영상 중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}
