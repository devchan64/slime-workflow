"""DWPose와 Wan 영상 작업을 기존 검증·GPU 대기열로 위임한다."""
import json
import os
import re
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason

from tools.review.common.source_history_catalog import SOURCE_HISTORY_VIDEO_SERVICES
HERMES_VIDEO_SERVICES = SOURCE_HISTORY_VIDEO_SERVICES
HERMES_VIDEO_REQUEST_LIMIT = 39_000_000


def validate_hermes_video_service(current_service_name):
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_VIDEO_SERVICES:
        raise ValueError('지원하는 동작·영상 생성 서비스가 아닙니다.')


def make_hermes_video_manager(current_service_name):
    validate_hermes_video_service(current_service_name)
    if current_service_name=='dwpose':
        from tools.review.domains.dwpose.generation import DwposeGenerationManager
        return DwposeGenerationManager()
    if current_service_name=='wan22-animate2':
        from tools.review.domains.wan_animate2.generation import AnimateTwoGenerationManager
        return AnimateTwoGenerationManager()
    if current_service_name=='wan22-fun-control':
        from tools.review.domains.wan_fun.generation import FunControlGenerationManager
        return FunControlGenerationManager()
    from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
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
    current_output_value={'status':current_status_value,'video':None,'image':None,'download':None,'result_status':'not_ready'}
    if current_status_value=='completed':
        current_attempt_values=set()
        if not current_job_value.get('result_error'):
            for current_field_name,current_file_name in (('video','preview.mp4'),('image','output-000.png'),('download','frames.zip')):
                current_path_value=current_job_value.get(current_field_name)
                current_path_pattern='/'+re.escape(current_service_name)+'/jobs/'+re.escape(current_receipt_value['job_id'])+r'/attempts/([a-f0-9]{32})/'+re.escape(current_file_name)
                current_path_match=re.fullmatch(current_path_pattern,current_path_value) if isinstance(current_path_value,str) else None
                if current_path_match:
                    current_output_value[current_field_name]=current_path_value
                    current_attempt_values.add(current_path_match.group(1))
        if len(current_attempt_values)>1:
            for current_field_name in ('video','image','download'):
                current_output_value[current_field_name]=None
        current_result_count=sum(current_output_value[current_field_name] is not None for current_field_name in ('video','image','download'))
        current_output_value['result_status']='available' if current_result_count==3 else 'partial' if current_result_count else 'unavailable'
    current_output_value.update(observe_hermes_failure_reason(current_status_value,current_job_value.get('error')))
    current_output_value['note']='상태 조회가 중단 작업 복구를 수행할 수 있습니다. 결과와 상세 로그는 해당 생성기에서 확인하세요.'
    return {'receipt':current_receipt_value,'job':current_output_value}


def list_hermes_video_receipts(current_service_name):
    validate_hermes_video_service(current_service_name)
    return HermesDelegationStore().list_service_delegations(current_service_name)


def cancel_hermes_video_request(current_request_identifier,current_service_name,current_job_identifier):
    validate_hermes_video_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('접수 기록과 확인한 영상 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_video_service(current_service_name,'cancel',{'id':current_job_identifier})
    if not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True:
        raise ValueError('영상 중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}
