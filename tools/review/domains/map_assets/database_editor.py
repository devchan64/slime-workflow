"""기존 에셋 편집 계약을 DB 콘텐츠 API에 연결한다."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode, quote
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.domains.map_assets.editor import EDITOR_MUTABLE_FIELDS, EDITOR_STORAGE_DIRECTORY
from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
from tools.review.common.sprite_display_properties import normalize_sprite_property_precision, calculate_billboard_intersection_properties


def load_database_editor_catalog(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)-{'category'}:
        raise ValueError('목록 조회에는 category만 지정하세요.')
    current_type_records=execute_content_api_request('GET','/internal/v1/content/types')['types']
    current_requested_type=current_request_payload.get('category')
    if current_requested_type is not None and current_requested_type not in current_type_records:
        raise ValueError('등록된 에셋 타입을 선택하세요.')
    current_selected_types=[current_requested_type] if current_requested_type is not None else list(current_type_records)
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
    current_asset_rows=[]
    current_asset_revisions={}
    for current_asset_type in current_selected_types:
        current_page_cursor=''
        while True:
            current_page_record=execute_content_api_request('GET','/internal/v1/content/billboards?'+urlencode(
                {'type':current_asset_type,'cursor':current_page_cursor,'limit':500}))
            for current_asset_record in current_page_record['assets']:
                current_image_path=(current_asset_root/current_asset_record['image']['path']).resolve()
                if not current_image_path.is_relative_to(current_asset_root):
                    raise ValueError('등록 이미지 경로 이탈')
                current_asset_revisions[current_asset_record['assetId']]=current_asset_record['revision']
                current_asset_rows.append({'texture':current_asset_record['assetId'],'name':current_asset_record['name'],
                    'category':current_asset_record['assetType'],'image':str(current_image_path),
                    'size':[current_asset_record['image']['width'],current_asset_record['image']['height']],
                    'properties':current_asset_record['properties'],'maps':current_asset_record['metadata'].get('mapReferences',[]),
                    'modeling':current_asset_record['metadata']['modeling'],'metadata':current_asset_record['metadata'].get('metadataReferences',[]),
                    'databaseRevision':current_asset_record['revision']})
            current_page_cursor=current_page_record['nextCursor']
            if current_page_cursor is None:break
    return {'revision':json.dumps(current_asset_revisions,sort_keys=True,separators=(',',':')),'assets':current_asset_rows,'storage':'database'}


def preview_database_editor_changes(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','changes'}:
        raise ValueError('revision·changes가 필요합니다.')
    current_revision_records=json.loads(current_request_payload['revision'])
    current_change_records=current_request_payload['changes']
    if not isinstance(current_change_records,list) or not 1<=len(current_change_records)<=1000:
        raise ValueError('변경할 에셋 1~1000개가 필요합니다.')
    current_preview_token=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    current_backend_changes=[]
    current_preview_changes=[]
    current_seen_identifiers=set()
    for current_change_record in current_change_records:
        if set(current_change_record)!={'texture','values'} or not isinstance(current_change_record['values'],dict) or set(current_change_record['values'])-EDITOR_MUTABLE_FIELDS:
            raise ValueError('허용되지 않은 에셋 변경 필드')
        current_asset_identifier=current_change_record['texture']
        if current_asset_identifier in current_seen_identifiers or current_asset_identifier not in current_revision_records:
            raise ValueError('에셋 ID 중복 또는 기준 revision 누락')
        current_seen_identifiers.add(current_asset_identifier)
        current_asset_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_asset_identifier,safe=''))
        if current_asset_record['revision']!=current_revision_records[current_asset_identifier]:
            raise ValueError('에셋이 변경되었습니다. 최신 값을 조회하세요: '+current_asset_identifier)
        current_updated_values=normalize_sprite_property_precision(calculate_billboard_intersection_properties(
            {**current_asset_record['properties'],**current_change_record['values']}))
        current_backend_changes.append({'assetId':current_asset_identifier,'requestId':current_preview_token+':'+current_asset_identifier,
            'expectedRevision':current_asset_record['revision'],'properties':current_updated_values})
        current_preview_changes.append({'texture':current_asset_identifier,'before':current_asset_record['properties'],'after':current_updated_values})
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    current_pending_path=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-database.json')
    current_pending_path.write_text(json.dumps({'changes':current_backend_changes},ensure_ascii=False))
    return {'token':current_preview_token,'changes':current_preview_changes,'maps':[],'map_warnings':[],
        'note':'DB에 즉시 저장하며 파일은 주기적으로 스냅샷됩니다.'}


def save_database_editor_changes(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','changes','token'}:
        raise ValueError('revision·changes·token이 필요합니다.')
    current_validation_payload={current_field_name:current_request_payload[current_field_name] for current_field_name in ('revision','changes')}
    current_preview_token=hashlib.sha256(json.dumps(current_validation_payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    if current_preview_token!=current_request_payload['token']:
        raise ValueError('검증 후 입력이 변경되었습니다.')
    current_pending_path=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-database.json')
    if not current_pending_path.is_file():raise ValueError('먼저 변경 검증을 실행하세요.')
    current_backend_payload=json.loads(current_pending_path.read_text())
    return execute_content_api_request('POST','/internal/v1/content/billboard-changes',current_backend_payload)


def save_database_sprite_anchor(current_request_payload):
    """이전 앵커 저장 명령도 공용 DB 속성·revision 저장 경로를 사용한다."""
    import re
    current_required_fields={'map','kind','texture','anchorX','anchorY','expected','requestId','expectedRevision'}
    if not isinstance(current_request_payload,dict) or set(current_request_payload) not in (current_required_fields,current_required_fields|{'layout'}):
        raise ValueError('DB 앵커 저장은 맵·종류·텍스처·앵커·expected·requestId·expectedRevision이 필요합니다.')
    if (not isinstance(current_request_payload['requestId'],str) or not 1<=len(current_request_payload['requestId'])<=128
            or type(current_request_payload['expectedRevision']) is not int or current_request_payload['expectedRevision']<1):
        raise ValueError('requestId와 양의 정수 expectedRevision이 필요합니다.')
    current_texture_key=current_request_payload['texture']
    current_map_identifier=current_request_payload['map']
    if (not isinstance(current_texture_key,str) or not re.fullmatch('[a-z][a-z0-9-]*',current_texture_key)
            or not isinstance(current_map_identifier,str) or not re.fullmatch('[a-z0-9-]+',current_map_identifier)
            or current_request_payload['kind'] not in ('town','field')):
        raise ValueError('맵·종류·텍스처 ID 오류')
    current_request_digest=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
    current_pending_path=EDITOR_STORAGE_DIRECTORY/(current_request_digest+'-anchor-database.json')
    if not current_pending_path.exists():
        current_asset_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_texture_key,safe=''))
        if (current_asset_record['retired'] or current_asset_record['properties']!=current_request_payload['expected']
                or current_asset_record['revision']!=current_request_payload['expectedRevision']):
            raise ValueError('공용 속성이 변경되었거나 폐기된 에셋입니다. 새로고침하세요.')
        current_map_path='assets/maps/'+('city_layouts' if current_request_payload['kind']=='town' else 'field_tiles')+'/'+current_map_identifier+'.yaml'
        if not any(current_usage_record['path']==current_map_path for current_usage_record in current_asset_record['metadata']['mapReferences']):
            raise ValueError('선택 맵에서 사용하지 않는 빌보드입니다.')
        current_layout_values=current_request_payload.get('layout',{})
        if not isinstance(current_layout_values,dict) or (current_layout_values and set(current_layout_values)!={'groundFootprintColumns','groundFootprintRows','displayHeight'}):
            raise ValueError('바닥 열·행과 표시 높이가 필요합니다.')
        current_updated_values=normalize_sprite_property_precision(calculate_billboard_intersection_properties(
            {**current_asset_record['properties'],**current_layout_values,
             'anchorX':current_request_payload['anchorX'],'anchorY':current_request_payload['anchorY']}))
        current_backend_payload={'changes':[{'assetId':current_texture_key,
            'requestId':'anchor:'+current_request_payload['requestId'],
            'expectedRevision':current_asset_record['revision'],'properties':current_updated_values}]}
        EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
        current_pending_path.write_text(json.dumps(current_backend_payload,ensure_ascii=False,allow_nan=False))
    current_save_result=execute_content_api_request('POST','/internal/v1/content/billboard-changes',json.loads(current_pending_path.read_text()))
    return {**current_save_result,'map':current_map_identifier,'scope':'asset','texture':current_texture_key}
