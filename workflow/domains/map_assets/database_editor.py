"""기존 에셋 편집 계약을 DB 콘텐츠 API에 연결한다."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode, quote
from workflow.domains.map_assets.database_client import execute_content_api_request
from workflow.domains.map_assets.editor import EDITOR_MUTABLE_FIELDS, EDITOR_STORAGE_DIRECTORY
from workflow.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
from workflow.common.sprite_display_properties import normalize_sprite_property_precision, calculate_billboard_intersection_properties


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



def inspect_database_billboard_maps(current_asset_records, current_preview_changes):
    """DB 사용 맵별 스냅샷에서 변경 후 접지와 장식 간 충돌을 검사한다."""
    from workflow.domains.map_assets.placement import validate_scenery_object_collisions
    current_map_paths=set()
    for current_asset_record in current_asset_records:
        current_reference_records=current_asset_record.get('metadata',{}).get('mapReferences')
        if not isinstance(current_reference_records,list):
            raise ValueError('DB 사용 맵 목록을 확인할 수 없습니다.')
        for current_reference_record in current_reference_records:
            current_map_path=current_reference_record.get('path') if isinstance(current_reference_record,dict) else None
            if not isinstance(current_map_path,str) or not re.fullmatch(r'assets/maps/(field_tiles|city_layouts)/[a-z][a-z0-9-]*\.yaml',current_map_path):
                raise ValueError('지원하지 않는 빌보드 사용 맵 경로입니다.')
            current_map_paths.add(current_map_path)
    current_map_warnings=[]
    for current_map_path in sorted(current_map_paths):
        current_relative_path=current_map_path.removeprefix('assets/maps/')
        current_map_identifier=Path(current_map_path).stem
        current_bundle_record=execute_content_api_request('GET','/internal/v1/content/review-bundle?'+urlencode({'map':current_map_identifier}))
        current_documents_record=current_bundle_record['documents']
        current_property_catalog=dict(current_documents_record['sprite-display-properties.yaml']['data'])
        for current_change_record in current_preview_changes:
            if current_property_catalog.get(current_change_record['texture'])!=current_change_record['before']:
                raise ValueError('에셋 속성이 맵 검수 중 변경되었습니다. 다시 검증하세요.')
            current_property_catalog[current_change_record['texture']]=current_change_record['after']
        current_map_data=current_documents_record[current_relative_path]['data']
        current_object_records=current_map_data.get('objects',[])
        if current_relative_path.startswith('field_tiles/'):
            current_elevation_rows=current_documents_record['terrain/maps/'+current_map_identifier+'.yaml']['data']['elevations']
        else:
            current_elevation_rows=current_map_data.get('elevations')
            if current_elevation_rows is None:
                current_elevation_rows=[[0]*current_map_data['columns'] for current_row_index in range(current_map_data['rows'])]
        try:
            validate_scenery_object_collisions(current_object_records,current_property_catalog,current_elevation_rows)
        except (ValueError,KeyError,TypeError,IndexError) as current_map_error:
            current_map_warnings.append({'map':current_map_path,'message':str(current_map_error)})
    return sorted(current_map_paths),current_map_warnings


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
    current_asset_records=[]
    current_seen_identifiers=set()
    for current_change_record in current_change_records:
        if (not isinstance(current_change_record,dict) or set(current_change_record)!={'texture','values'}
                or not isinstance(current_change_record['values'],dict) or not current_change_record['values']
                or set(current_change_record['values'])-EDITOR_MUTABLE_FIELDS):
            raise ValueError('허용되지 않은 에셋 변경 필드')
        current_asset_identifier=current_change_record['texture']
        if current_asset_identifier in current_seen_identifiers or current_asset_identifier not in current_revision_records:
            raise ValueError('에셋 ID 중복 또는 기준 revision 누락')
        current_seen_identifiers.add(current_asset_identifier)
        current_asset_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_asset_identifier,safe=''))
        if current_asset_record['revision']!=current_revision_records[current_asset_identifier]:
            raise ValueError('에셋이 변경되었습니다. 최신 값을 조회하세요: '+current_asset_identifier)
        current_asset_records.append(current_asset_record)
        current_original_values=current_asset_record['properties']
        if not isinstance(current_original_values,dict):
            raise ValueError('공용 속성이 없는 에셋은 최초 등록 절차를 확인하세요.')
        if (current_original_values.get('billboardAnchorMode') in ('tile-bottom-center','tile-intersection')
                and 'billboardPlacementAnchor' in current_change_record['values']):
            raise ValueError('상하 배치는 앵커에서 자동 판정됩니다.')
        current_updated_values=normalize_sprite_property_precision(calculate_billboard_intersection_properties(
            {**current_original_values,**current_change_record['values']}))
        if current_updated_values==current_original_values:
            raise ValueError('변경 없는 에셋은 제외하세요: '+current_asset_identifier)
        current_backend_changes.append({'assetId':current_asset_identifier,'requestId':current_preview_token+':'+current_asset_identifier,
            'expectedRevision':current_asset_record['revision'],'properties':current_updated_values})
        current_preview_changes.append({'texture':current_asset_identifier,'before':current_asset_record['properties'],'after':current_updated_values})
    current_affected_maps,current_map_warnings=inspect_database_billboard_maps(current_asset_records,current_preview_changes)
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    current_pending_path=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-database.json')
    current_pending_path.write_text(json.dumps({'changes':current_backend_changes},ensure_ascii=False))
    return {'token':current_preview_token,'changes':current_preview_changes,'maps':current_affected_maps,'map_warnings':current_map_warnings,
        'note':'각 맵의 미리보기 시점 접지·장식 충돌만 검사합니다. 이후 맵 변경이나 전체 게임 통행 검증은 보장하지 않습니다. DB 저장 후 파일은 주기적으로 스냅샷됩니다.'}


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
