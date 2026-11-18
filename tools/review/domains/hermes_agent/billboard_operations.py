"""빌보드 공용 속성을 기존 편집기로 검토하고 중복 없이 저장한다."""
import hashlib
import json
import re

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.field_map_operations import call_field_map_editor, HERMES_FIELD_TOKEN_PATTERN
from tools.review.domains.map_assets.editor import EDITOR_MUTABLE_FIELDS, hash_billboard_review_result

BILLBOARD_IDENTIFIER_PATTERN = re.compile(r'[a-z][a-z0-9-]{0,95}')


def validate_billboard_edit_draft(current_draft_record):
    if not isinstance(current_draft_record,dict) or set(current_draft_record)!={'revision','changes'}:
        raise ValueError('revision·changes가 필요합니다.')
    if not isinstance(current_draft_record['revision'],str) or not 1<=len(current_draft_record['revision'])<=100000:
        raise ValueError('빌보드 revision 오류')
    current_change_records=current_draft_record['changes']
    if not isinstance(current_change_records,list) or not 1<=len(current_change_records)<=20:
        raise ValueError('빌보드 변경은 1~20개입니다.')
    current_identifiers=set()
    for current_change_record in current_change_records:
        if not isinstance(current_change_record,dict) or set(current_change_record)!={'texture','values'}:
            raise ValueError('변경 항목 오류')
        current_asset_identifier=current_change_record['texture']
        current_change_values=current_change_record['values']
        if not isinstance(current_asset_identifier,str) or not BILLBOARD_IDENTIFIER_PATTERN.fullmatch(current_asset_identifier) or current_asset_identifier in current_identifiers:
            raise ValueError('빌보드 ID 오류 또는 중복')
        if not isinstance(current_change_values,dict) or not current_change_values or set(current_change_values)-EDITOR_MUTABLE_FIELDS:
            raise ValueError('허용되지 않은 공용 속성')
        current_identifiers.add(current_asset_identifier)
    try:
        current_request_bytes=json.dumps(current_draft_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as current_error_value:
        raise ValueError('빌보드 초안 JSON 오류') from current_error_value
    if len(current_request_bytes)>200000:
        raise ValueError('빌보드 초안 크기 초과')
    return hashlib.sha256(current_request_bytes).hexdigest()


def load_hermes_billboard_edit(current_asset_identifier):
    if not isinstance(current_asset_identifier,str) or not BILLBOARD_IDENTIFIER_PATTERN.fullmatch(current_asset_identifier):
        raise ValueError('빌보드 ID 오류')
    current_catalog_record=call_field_map_editor('asset-list',{})
    if not isinstance(current_catalog_record,dict) or not isinstance(current_catalog_record.get('assets'),list):
        raise ValueError('빌보드 목록 응답 오류')
    current_match_records=[current_asset_record for current_asset_record in current_catalog_record['assets'] if isinstance(current_asset_record,dict) and current_asset_record.get('texture')==current_asset_identifier]
    if len(current_match_records)!=1:
        raise ValueError('등록된 빌보드를 하나 찾지 못했습니다.')
    current_revision_value=current_catalog_record.get('revision')
    current_property_values=current_match_records[0].get('properties')
    if not isinstance(current_revision_value,str) or len(current_revision_value)>100000 or not isinstance(current_property_values,dict):
        raise ValueError('빌보드 속성 또는 revision을 확인할 수 없습니다.')
    return {'texture':current_asset_identifier,'revision':current_revision_value,'properties':current_property_values}


def preview_hermes_billboard_edit(current_draft_record):
    current_expected_token=validate_billboard_edit_draft(current_draft_record)
    current_preview_record=call_field_map_editor('asset-preview',current_draft_record)
    if not isinstance(current_preview_record,dict) or current_preview_record.get('token')!=current_expected_token:
        raise ValueError('빌보드 미리보기 토큰 오류')
    current_review_record={current_field_name:current_preview_record.get(current_field_name) for current_field_name in ('changes','maps','map_warnings','note')}
    if not isinstance(current_review_record['changes'],list) or len(current_review_record['changes'])!=len(current_draft_record['changes']) or not isinstance(current_review_record['maps'],list) or not isinstance(current_review_record['map_warnings'],list) or not isinstance(current_review_record['note'],str):
        raise ValueError('빌보드 미리보기 응답 오류')
    if any(not isinstance(current_map_path,str) or not re.fullmatch(r'assets/maps/(?:field_tiles|city_layouts)/[a-z][a-z0-9-]*\.yaml',current_map_path) for current_map_path in current_review_record['maps']):
        raise ValueError('빌보드 영향 맵 경로 오류')
    if any(not isinstance(current_warning_record,dict) or set(current_warning_record)!={'map','message'} or current_warning_record['map'] not in current_review_record['maps'] or not isinstance(current_warning_record['message'],str) or re.search(r'(?<![\w.])/(?:home|tmp|root|opt|srv)/',current_warning_record['message']) for current_warning_record in current_review_record['map_warnings']):
        raise ValueError('빌보드 맵 경고 형식 오류')
    if any(not isinstance(current_change_record,dict) or set(current_change_record)!={'texture','before','after'} or not isinstance(current_change_record['before'],dict) or not isinstance(current_change_record['after'],dict) for current_change_record in current_review_record['changes']):
        raise ValueError('빌보드 변경 비교 형식 오류')
    if [current_change_record['texture'] for current_change_record in current_review_record['changes']] != [current_change_record['texture'] for current_change_record in current_draft_record['changes']]:
        raise ValueError('빌보드 변경 비교 ID 불일치')
    current_review_bytes=json.dumps(current_review_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
    if len(current_review_bytes)>300000:
        raise ValueError('빌보드 미리보기 응답 크기 초과')
    return {**current_review_record,'token':current_expected_token,'review_sha256':hash_billboard_review_result(current_review_record)}


def inspect_billboard_edit_receipt(current_receipt_record,current_request_identifier):
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('version')!=7 or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed'):
        raise ValueError('빌보드 저장 접수 기록 오류')
    current_state_value='unknown' if current_receipt_record['state']=='dispatching' else 'completed'
    if current_state_value=='completed' and type(current_receipt_record.get('saved')) is not bool:
        raise ValueError('빌보드 저장 접수 상태 오류')
    return {'request_id':current_request_identifier,'state':current_state_value,'saved':current_receipt_record.get('saved')}


def save_hermes_billboard_edit_once(current_request_identifier,current_draft_record,current_preview_token,current_review_digest):
    current_expected_token=validate_billboard_edit_draft(current_draft_record)
    if current_preview_token!=current_expected_token or not isinstance(current_review_digest,str) or not HERMES_FIELD_TOKEN_PATTERN.fullmatch(current_review_digest):
        raise ValueError('검토한 빌보드 초안과 검수 결과가 필요합니다.')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if current_receipt_path.exists():
            current_receipt_record=json.loads(current_receipt_path.read_text(encoding='utf-8'))
            current_result_record=inspect_billboard_edit_receipt(current_receipt_record,current_request_identifier)
            if current_receipt_record.get('token')!=current_preview_token or current_receipt_record.get('review_sha256')!=current_review_digest:
                raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        current_review_record=preview_hermes_billboard_edit(current_draft_record)
        if current_review_record['review_sha256']!=current_review_digest:
            raise ValueError('맵 경고 또는 검수 결과가 변경되었습니다. 다시 확인하세요.')
        current_receipt_record={'version':7,'id':current_request_identifier,'token':current_preview_token,'review_sha256':current_review_digest,'state':'dispatching'}
        write_record_atomically(current_receipt_path,current_receipt_record)
        current_save_record=call_field_map_editor('asset-save-reviewed',{**current_draft_record,'token':current_preview_token,'review_sha256':current_review_digest})
        if not isinstance(current_save_record,dict) or type(current_save_record.get('saved')) is not bool:
            raise ValueError('빌보드 저장 결과 확인 필요. 자동 재접수하지 않습니다.')
        current_receipt_record.update(state='completed',saved=current_save_record['saved'])
        write_record_atomically(current_receipt_path,current_receipt_record)
        return {**inspect_billboard_edit_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_hermes_billboard_edit_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not current_receipt_path.exists():
            return {'state':'not_found'}
        return inspect_billboard_edit_receipt(json.loads(current_receipt_path.read_text(encoding='utf-8')),current_request_identifier)
