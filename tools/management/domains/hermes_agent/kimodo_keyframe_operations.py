"""검토한 Kimodo 프레임을 접수 ID로 중복 없이 저장한다."""
import hashlib
import json
import os
import re

from tools.management.common.generation_records import write_record_atomically
from tools.management.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.management.common.management_gateway import execute_management_command
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record, validate_service_job_identifier


def validate_hermes_keyframe_request(current_request_record):
    """검토한 원본 신원과 확인값을 고정한다."""
    if not isinstance(current_request_record,dict) or set(current_request_record)!={'job_id','attempt_id','frame','tag','review_sha256'}:raise ValueError('키프레임 저장 입력 형식 오류')
    current_tag_value=current_request_record['tag']
    if not validate_service_job_identifier('kimodo',current_request_record['job_id']) or not isinstance(current_request_record['attempt_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',current_request_record['attempt_id']) or type(current_request_record['frame']) is not int or not 1<=current_request_record['frame']<=1000 or not isinstance(current_tag_value,str) or not current_tag_value.strip() or len(current_tag_value.strip())>80 or any(ord(current_character)<32 for current_character in current_tag_value) or not isinstance(current_request_record['review_sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_request_record['review_sha256']):raise ValueError('키프레임 저장 입력 값 오류')
    current_canonical_record={**current_request_record,'tag':current_tag_value.strip()}
    return hashlib.sha256(json.dumps(current_canonical_record,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def inspect_hermes_keyframe_receipt(current_receipt_record,current_request_identifier):
    """접수 결과가 불확실하면 재실행하지 않는다."""
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('version')!=14 or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed') or not isinstance(current_receipt_record.get('request_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_receipt_record['request_sha256']):raise ValueError('키프레임 접수 기록 오류')
    current_source_record=current_receipt_record.get('source')
    if current_source_record is not None:
        if not isinstance(current_source_record,dict) or set(current_source_record)!={'job_id','attempt_id','frame','tag'}:raise ValueError('키프레임 접수 원본 형식 오류')
        validate_hermes_keyframe_request({**current_source_record,'review_sha256':'0'*64})
    current_source_result={'source':current_source_record} if current_source_record is not None else {}
    if current_receipt_record['state']=='dispatching':return {'request_id':current_request_identifier,'state':'unknown','message':'원 서비스의 키프레임 목록을 확인하고 자동 재저장하지 마세요.',**current_source_result}
    current_saved_identifier=current_receipt_record.get('keyframe_id')
    if not isinstance(current_saved_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_saved_identifier):raise ValueError('키프레임 저장 결과 오류')
    return {'request_id':current_request_identifier,'state':'completed','keyframe_id':current_saved_identifier,**current_source_result}


def inspect_legacy_keyframe_receipts(current_storage_value):
    """확인해야 할 이전 대화 접수 ID와 제한된 상태를 반환한다."""
    current_record_paths=[]
    with os.scandir(current_storage_value.delegation_storage_root) as current_directory_entries:
        for current_entry_count,current_directory_entry in enumerate(current_directory_entries,1):
            if current_entry_count>10000:raise ValueError('접수 기록이 너무 많아 기존 키프레임 접수를 확인할 수 없습니다.')
            if re.fullmatch(r'keyframe_[a-f0-9]{64}\.json',current_directory_entry.name):current_record_paths.append(current_storage_value.delegation_storage_root/current_directory_entry.name)
    current_blocker_records=[]
    for current_record_path in current_record_paths:
        if not re.fullmatch(r'keyframe_[a-f0-9]{64}',current_record_path.stem):continue
        try:
            current_receipt_record=read_bounded_delegation_record(current_record_path)
            if not isinstance(current_receipt_record,dict):raise ValueError('이전 키프레임 접수 형식 오류')
            if current_receipt_record.get('version')!=14:continue
            current_checked_value=inspect_hermes_keyframe_receipt(current_receipt_record,current_record_path.stem)
            if isinstance(current_receipt_record.get('source'),dict):continue
            current_state_value=current_checked_value['state']
        except (OSError,ValueError,TypeError,KeyError):
            current_state_value='unavailable'
        current_blocker_records.append({'request_id':current_record_path.stem,'state':current_state_value})
    current_blocker_records.sort(key=lambda current_record_value:current_record_value['request_id'])
    return {'records':current_blocker_records[:20],'truncated':len(current_blocker_records)>20}


def check_legacy_keyframe_receipts(current_storage_value):
    """원본 신원이 없는 이전 대화 접수가 있으면 새 대화 저장을 보류한다."""
    current_blocker_value=inspect_legacy_keyframe_receipts(current_storage_value)
    if current_blocker_value['records'] or current_blocker_value['truncated']:raise ValueError('원본 신원이 없거나 확인할 수 없는 이전 키프레임 접수가 있습니다. 저장 전에 원 서비스와 기존 접수를 확인하세요.')


def save_hermes_keyframe_once(current_request_identifier,current_request_record):
    """원 서비스 호출 전에 접수를 기록하고 불확실한 결과를 보존한다."""
    current_request_hash=validate_hermes_keyframe_request(current_request_record)
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_record=read_bounded_delegation_record(current_receipt_path)
            current_result_record=inspect_hermes_keyframe_receipt(current_receipt_record,current_request_identifier)
            if current_receipt_record['request_sha256']!=current_request_hash:raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        if re.fullmatch(r'keyframe_[a-f0-9]{64}',current_request_identifier):check_legacy_keyframe_receipts(current_storage_value)
        current_receipt_record={'version':14,'id':current_request_identifier,'request_sha256':current_request_hash,'state':'dispatching','source':{current_key_name:current_request_record[current_key_name].strip() if current_key_name=='tag' else current_request_record[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag')}}
        write_record_atomically(current_receipt_path,current_receipt_record)
        current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
        current_result_value=execute_management_command('kimodo','keyframe-save-reviewed',current_request_record,current_gateway_address)
        if not isinstance(current_result_value,dict) or not isinstance(current_result_value.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',current_result_value['id']) or current_result_value.get('source_job')!=current_request_record['job_id'] or current_result_value.get('source_attempt')!=current_request_record['attempt_id'] or type(current_result_value.get('source_frame')) is not int or current_result_value['source_frame']!=current_request_record['frame'] or current_result_value.get('tag')!=current_request_record['tag'].strip():raise ValueError('키프레임 저장 결과를 확인할 수 없습니다. 자동 재저장하지 마세요.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_record:raise ValueError('저장 중 접수 기록이 변경됐습니다. 자동 재저장하지 마세요.')
        current_receipt_record.update(state='completed',keyframe_id=current_result_value['id'])
        write_record_atomically(current_receipt_path,current_receipt_record)
        return {**inspect_hermes_keyframe_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_hermes_keyframe_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'request_id':current_request_identifier,'state':'not_found'}
        return inspect_hermes_keyframe_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)


def preview_hermes_keyframe_source(current_job_identifier,current_attempt_identifier,current_frame_number,current_tag_text):
    """원 서비스의 검토 결과 신원과 경로를 확인한다."""
    current_request_record={'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':current_frame_number,'tag':current_tag_text,'review_sha256':'0'*64}
    validate_hermes_keyframe_request(current_request_record)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_review_value=execute_management_command('kimodo','keyframe-source-review',{current_key_name:current_request_record[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag')},current_gateway_address)
    current_expected_image='/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-'+format(current_frame_number-1,'03d')+'.png'
    if not isinstance(current_review_value,dict) or current_review_value.get('job_id')!=current_job_identifier or current_review_value.get('attempt_id')!=current_attempt_identifier or type(current_review_value.get('frame')) is not int or current_review_value['frame']!=current_frame_number or current_review_value.get('tag')!=current_tag_text.strip() or type(current_review_value.get('frame_count')) is not int or not current_frame_number<=current_review_value['frame_count']<=1000 or current_review_value.get('source_motion') not in ('motion.npz','motion-in-place.npz') or current_review_value.get('image')!=current_expected_image or any(not isinstance(current_review_value.get(current_hash_name),str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_value[current_hash_name]) for current_hash_name in ('image_sha256','review_sha256')):raise ValueError('키프레임 원본 검토 응답 오류')
    current_readiness_value='ready'
    current_blocker_value={'records':[],'truncated':False}
    try:
        current_storage_value=HermesDelegationStore()
        with current_storage_value.hold_delegation_storage_lock():current_blocker_value=inspect_legacy_keyframe_receipts(current_storage_value)
        if current_blocker_value['records'] or current_blocker_value['truncated']:current_readiness_value='check_required'
    except (OSError,ValueError,TypeError,KeyError):
        current_readiness_value='check_required'
        current_blocker_value=None
    return {**{current_key_name:current_review_value[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag','frame_count','source_motion','image','image_sha256','review_sha256')},'chat_save_readiness':current_readiness_value,'legacy_receipts':current_blocker_value}
