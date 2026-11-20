"""건물 앵커만 검토하고 원 서비스의 세대 조건부 저장을 사용한다."""
import hashlib
import json
import re

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record
from tools.review.domains.hermes_agent.field_map_operations import call_field_map_editor
from tools.review.domains.map_assets.building_editor import validate_building_editor_anchor


def inspect_hermes_building_draft(current_draft_record):
    validate_building_editor_anchor(current_draft_record)
    if current_draft_record['generation']<0:
        raise ValueError('콘텐츠 세대 오류')
    current_before_values=current_draft_record['expected']
    current_after_values=current_draft_record['properties']
    if set(current_before_values)!=set(current_after_values) or any(current_before_values[current_field_name]!=current_after_values[current_field_name] for current_field_name in set(current_before_values)-{'anchorX','anchorY'}):
        raise ValueError('건물 크기와 그림자 속성은 변경할 수 없습니다. 앵커 X·Y만 변경하세요.')
    if current_before_values==current_after_values:
        raise ValueError('변경된 건물 앵커가 없습니다.')
    return hashlib.sha256(json.dumps(current_draft_record,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def preview_hermes_building_anchor(current_draft_record):
    current_draft_digest=inspect_hermes_building_draft(current_draft_record)
    current_catalog_record=call_field_map_editor('building-list',{})
    if not isinstance(current_catalog_record,dict) or current_catalog_record.get('generation')!=current_draft_record['generation'] or not isinstance(current_catalog_record.get('assets'),list):
        raise ValueError('건물 목록 또는 콘텐츠 세대가 변경됐습니다. 다시 조회하세요.')
    current_matching_records=[current_asset_record for current_asset_record in current_catalog_record['assets'] if isinstance(current_asset_record,dict) and current_asset_record.get('texture')==current_draft_record['texture']]
    if len(current_matching_records)!=1 or current_matching_records[0].get('properties')!=current_draft_record['expected']:
        raise ValueError('건물 현재 속성이 변경됐습니다. 다시 조회하세요.')
    current_usage_values=current_matching_records[0].get('maps')
    if not isinstance(current_usage_values,list) or any(not isinstance(current_usage_record,dict) or not isinstance(current_usage_record.get('map'),str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_usage_record['map']) for current_usage_record in current_usage_values):
        raise ValueError('건물 사용 맵을 확인할 수 없습니다.')
    current_review_record={'texture':current_draft_record['texture'],'generation':current_draft_record['generation'],'before':current_draft_record['expected'],'after':current_draft_record['properties'],'maps':sorted({current_usage_record['map'] for current_usage_record in current_usage_values}),'draft_sha256':current_draft_digest}
    current_review_record['review_sha256']=hashlib.sha256(json.dumps(current_review_record,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return current_review_record


def inspect_hermes_building_receipt(current_receipt_record,current_request_identifier):
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('version')!=11 or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed'):
        raise ValueError('건물 앵커 접수 기록 오류')
    if current_receipt_record['state']=='completed' and current_receipt_record.get('saved') is not True:
        raise ValueError('건물 앵커 저장 결과 오류')
    current_texture_value=current_receipt_record.get('texture')
    if current_texture_value is not None and (not isinstance(current_texture_value,str) or not re.fullmatch(r'(?:town-[a-z0-9-]+-v[1-9][0-9]*|ward-tower-v1)',current_texture_value)):
        raise ValueError('건물 앵커 접수 대상 오류')
    current_result_record={'request_id':current_request_identifier,'state':'unknown' if current_receipt_record['state']=='dispatching' else 'completed','saved':current_receipt_record.get('saved'),**({'texture':current_texture_value} if current_texture_value is not None else {})}
    current_generation_value=current_receipt_record.get('generation')
    if type(current_generation_value) is int and current_generation_value>=1 and current_receipt_record.get('ledger_status_at_save')=='pending':
        current_result_record.update(generation=current_generation_value,ledger_status_at_save='pending')
    return current_result_record


def save_hermes_building_anchor(current_request_identifier,current_draft_record,current_review_digest):
    current_draft_digest=inspect_hermes_building_draft(current_draft_record)
    if not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('검토 해시 오류')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_record=read_bounded_delegation_record(current_receipt_path)
            current_result_record=inspect_hermes_building_receipt(current_receipt_record,current_request_identifier)
            if current_receipt_record.get('draft_sha256')!=current_draft_digest or current_receipt_record.get('review_sha256')!=current_review_digest:raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        if preview_hermes_building_anchor(current_draft_record)['review_sha256']!=current_review_digest:
            raise ValueError('건물 검토 결과가 변경됐습니다. 다시 검토하세요.')
        current_receipt_record={'version':11,'id':current_request_identifier,'state':'dispatching','draft_sha256':current_draft_digest,'review_sha256':current_review_digest,'texture':current_draft_record['texture']}
        write_record_atomically(current_receipt_path,current_receipt_record)
        current_save_record=call_field_map_editor('building-save',current_draft_record)
        if (not isinstance(current_save_record,dict) or current_save_record.get('saved') is not True
                or ('asset' in current_save_record and current_save_record['asset']!=current_draft_record['texture'])):
            raise ValueError('건물 저장 결과 확인 필요. 자동 재접수하지 않습니다.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_record:raise ValueError('저장 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_receipt_record.update(state='completed',saved=True)
        if type(current_save_record.get('generation')) is int and current_save_record['generation']>=1 and current_save_record.get('snapshot')=='pending':
            current_receipt_record.update(generation=current_save_record['generation'],ledger_status_at_save='pending')
        write_record_atomically(current_receipt_path,current_receipt_record)
        return {**inspect_hermes_building_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_hermes_building_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'state':'not_found'}
        return inspect_hermes_building_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)
