"""DB 폐기 검수와 확인된 요청의 멱등 실행."""
import hashlib
import json
from uuid import uuid4
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.domains.map_assets.editor import EDITOR_STORAGE_DIRECTORY


def preview_database_asset_retirement(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture'}:
        raise ValueError('revision·texture가 필요합니다.')
    current_asset_revisions=json.loads(current_request_payload['revision'])
    current_asset_identifier=current_request_payload['texture']
    if current_asset_identifier not in current_asset_revisions:raise ValueError('목록에서 에셋을 다시 선택하세요.')
    current_plan_record=execute_content_api_request('POST','/internal/v1/content/retirement-preview',
        {'assetId':current_asset_identifier,'expectedRevision':current_asset_revisions[current_asset_identifier]})
    current_backend_request={current_field_name:current_plan_record[current_field_name] for current_field_name in ('assetId','expectedRevision','expectedGeneration')}
    current_backend_request['requestId']='retire-'+uuid4().hex
    current_prepared_record={'input':current_request_payload,'request':current_backend_request}
    current_prepared_bytes=json.dumps(current_prepared_record,sort_keys=True).encode()
    current_preview_token=hashlib.sha256(current_prepared_bytes).hexdigest()
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    (EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-database-retire.json')).write_bytes(current_prepared_bytes)
    return {**current_plan_record,'texture':current_asset_identifier,'token':current_preview_token,'storage':'database'}


def execute_database_asset_retirement(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','texture','token'}:
        raise ValueError('검수한 revision·texture·token이 필요합니다.')
    current_preview_token=current_request_payload['token']
    if not isinstance(current_preview_token,str) or len(current_preview_token)!=64 or any(current_character not in '0123456789abcdef' for current_character in current_preview_token):
        raise ValueError('폐기 확인 토큰 오류')
    current_prepared_bytes=(EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-database-retire.json')).read_bytes()
    if hashlib.sha256(current_prepared_bytes).hexdigest()!=current_preview_token:raise ValueError('폐기 확인 기록 변경')
    current_prepared_record=json.loads(current_prepared_bytes)
    if current_prepared_record['input']!={current_field_name:current_request_payload[current_field_name] for current_field_name in ('revision','texture')}:
        raise ValueError('폐기 확인 대상이 변경되었습니다.')
    return execute_content_api_request('POST','/internal/v1/content/retirement',current_prepared_record['request'])
