"""야외 맵 편집기의 읽기·초안 검증과 확인된 저장을 연결한다."""
import hashlib
import json
import os
import re

from tools.review.common.generation_records import write_record_atomically
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, list_delegation_record_paths, check_delegation_record_exists

HERMES_FIELD_MAP_PATTERN = re.compile(r'[a-z0-9][a-z0-9-]{0,95}')
HERMES_FIELD_TOKEN_PATTERN = re.compile(r'[a-f0-9]{64}')
HERMES_FIELD_MAX_BYTES = 1_000_000


def call_field_map_editor(current_command_name, current_payload_record):
    current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('map-assets', current_command_name, current_payload_record, current_gateway_address)


def validate_field_map_draft(current_draft_record):
    if not isinstance(current_draft_record, dict) or set(current_draft_record) - {'terrainEffects','ambientTint'} != {'map','revision','cells','objects'}:
        raise ValueError('야외 맵 초안의 map·revision·cells·objects가 필요합니다.')
    if not isinstance(current_draft_record['map'], str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_draft_record['map']):
        raise ValueError('맵 ID 형식 오류')
    if not isinstance(current_draft_record['revision'], str) or not 0 < len(current_draft_record['revision']) <= 4096:
        raise ValueError('원본 리비전 형식 오류')
    if not isinstance(current_draft_record['cells'], list) or not isinstance(current_draft_record['objects'], list):
        raise ValueError('셀·오브젝트는 목록이어야 합니다.')
    try:
        current_request_bytes = json.dumps(current_draft_record, sort_keys=True, allow_nan=False).encode()
    except (TypeError, ValueError) as current_draft_error:
        raise ValueError('맵 초안을 JSON으로 인코딩할 수 없습니다.') from current_draft_error
    if len(current_request_bytes) > HERMES_FIELD_MAX_BYTES:
        raise ValueError('맵 초안 크기 초과')
    return hashlib.sha256(current_request_bytes).hexdigest()


def load_hermes_field_map(current_map_identifier):
    if not isinstance(current_map_identifier, str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_map_identifier):
        raise ValueError('맵 ID 형식 오류')
    current_source_value = call_field_map_editor('map-edit-load', {'map':current_map_identifier})
    if not isinstance(current_source_value,dict) or current_source_value.get('map') != current_map_identifier or not isinstance(current_source_value.get('revision'),str):
        raise ValueError('맵 편집 응답 형식 오류')
    current_result_value = {key:current_source_value[key] for key in ('map','revision','tiles','terrain','textures','codes')}
    if len(json.dumps(current_result_value,ensure_ascii=False,allow_nan=False).encode()) > HERMES_FIELD_MAX_BYTES:
        raise ValueError('맵 편집 응답 크기 초과')
    return current_result_value


def preview_hermes_field_map(current_draft_record):
    current_expected_token = validate_field_map_draft(current_draft_record)
    current_preview_value = call_field_map_editor('map-edit-preview', current_draft_record)
    if not isinstance(current_preview_value,dict) or current_preview_value.get('token') != current_expected_token or type(current_preview_value.get('changed')) is not bool:
        raise ValueError('맵 미리보기 응답 형식 오류')
    for current_count_name in ('reachable','objects','cells'):
        if type(current_preview_value.get(current_count_name)) is not int or current_preview_value[current_count_name] < 0:
            raise ValueError('맵 미리보기 수량 오류')
    current_save_available=current_preview_value.get('save_available')
    if current_save_available is not None and type(current_save_available) is not bool:raise ValueError('맵 저장 가능 상태 형식 오류')
    current_result_record={**{key:current_preview_value[key] for key in ('token','changed','reachable','objects','cells')},'save_available':current_save_available}
    current_block_reason=current_preview_value.get('save_block_reason')
    if current_block_reason not in (None,'database','interrupted'):raise ValueError('맵 저장 차단 사유 형식 오류')
    if current_block_reason is not None:
        if current_save_available is not False:raise ValueError('맵 저장 차단 상태 불일치')
        current_result_record['save_block_reason']=current_block_reason
    if current_save_available is False and current_block_reason=='database':
        current_alignment_record={'status':'unavailable','note':'야외 맵 DB 문서와 에셋 원본의 일치를 확인할 수 없습니다.'}
        try:
            from pathlib import Path
            from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
            from tools.review.domains.map_assets.source_consistency import inspect_field_source_alignment
            current_database_record=load_hermes_field_map(current_draft_record['map'])
            if current_database_record['revision']==current_draft_record['revision']:
                current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
                current_alignment_record=inspect_field_source_alignment(current_asset_root,current_asset_root.parent/'slime-backend/map-data.lock.yaml',current_draft_record['map'],current_database_record['tiles'],current_database_record['terrain'])
                current_final_database=load_hermes_field_map(current_draft_record['map'])
                if current_final_database['revision']!=current_database_record['revision']:
                    current_alignment_record={'status':'unavailable','note':'야외 맵 DB 문서가 비교 중 변경되어 확인할 수 없습니다.'}
        except (OSError,ValueError,TypeError,KeyError):
            pass
        current_result_record['source_alignment']=current_alignment_record
    return current_result_record


def save_hermes_field_map_once(current_request_identifier, current_draft_record, current_preview_token):
    current_expected_token = validate_field_map_draft(current_draft_record)
    if not isinstance(current_preview_token,str) or not HERMES_FIELD_TOKEN_PATTERN.fullmatch(current_preview_token) or current_preview_token != current_expected_token:
        raise ValueError('검토한 초안과 미리보기 토큰이 일치하지 않습니다.')
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path = current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_record_path):
            current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
            if not isinstance(current_record_value,dict) or current_record_value.get('version') != 4 or current_record_value.get('id') != current_request_identifier or current_record_value.get('token') != current_preview_token or current_record_value.get('map') != current_draft_record['map']:
                raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            if current_record_value.get('state') == 'dispatching':
                return {'request_id':current_request_identifier,'state':'unknown','duplicate':True,'map':current_draft_record['map']}
            if current_record_value.get('state') != 'completed' or type(current_record_value.get('saved')) is not bool:
                raise ValueError('맵 저장 접수 기록 오류')
            return {'request_id':current_request_identifier,'state':'completed','duplicate':True,'map':current_record_value['map'],'saved':current_record_value['saved']}
        current_validation_value = preview_hermes_field_map(current_draft_record)
        if current_validation_value['token'] != current_preview_token:
            raise ValueError('맵 초안 검증이 일치하지 않습니다.')
        if current_validation_value['save_available'] is not True:
            if current_validation_value.get('save_block_reason')=='interrupted':raise ValueError('이전 야외 맵 저장이 중단되어 신규 저장을 보류합니다. 백업과 원본 상태를 확인하세요.')
            if current_validation_value.get('save_block_reason')=='database':raise ValueError('DB 모드의 신규 저장은 중단되었습니다. 원본과 등록부·백엔드 잠금의 동기화를 확인하세요.')
            raise ValueError('야외 맵 저장 가능 상태 또는 차단 사유를 확인할 수 없어 신규 저장을 보류합니다. 원 서비스의 상태를 확인하세요.')
        current_record_value = {'version':4,'id':current_request_identifier,'token':current_preview_token,'map':current_draft_record['map'],'state':'dispatching'}
        write_record_atomically(current_record_path,current_record_value)
        current_result_value = call_field_map_editor('map-edit-save', {**current_draft_record,'token':current_preview_token})
        if not isinstance(current_result_value,dict) or type(current_result_value.get('saved')) is not bool:
            raise ValueError('맵 저장 결과 확인 필요. 자동 재접수하지 않습니다.')
        if json.loads(current_record_path.read_text(encoding='utf-8')) != current_record_value:
            raise ValueError('저장 중 접수 기록이 변경됐습니다. 맵 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_record_value.update(state='completed',saved=current_result_value['saved'])
        write_record_atomically(current_record_path,current_record_value)
        return {'request_id':current_request_identifier,'state':'completed','duplicate':False,'map':current_draft_record['map'],'saved':current_record_value['saved']}


def inspect_hermes_field_receipt(current_record_value, current_request_identifier):
    """초안·경로를 제외한 접수 상태를 검증해 반환한다."""
    if (not isinstance(current_record_value,dict) or current_record_value.get('version') != 4
            or current_record_value.get('id') != current_request_identifier
            or not isinstance(current_record_value.get('map'),str)
            or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_record_value['map'])
            or not isinstance(current_record_value.get('token'),str)
            or not HERMES_FIELD_TOKEN_PATTERN.fullmatch(current_record_value['token'])):
        raise ValueError('맵 저장 접수 기록 오류')
    if current_record_value.get('state') == 'dispatching':
        return {'request_id':current_request_identifier,'map':current_record_value['map'],'state':'unknown','saved':None}
    if current_record_value.get('state') != 'completed' or type(current_record_value.get('saved')) is not bool:
        raise ValueError('맵 저장 접수 상태 오류')
    return {'request_id':current_request_identifier,'map':current_record_value['map'],'state':'completed','saved':current_record_value['saved']}


def read_hermes_field_receipt(current_request_identifier):
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path = current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_record_path):
            return {'state':'not_found'}
        return inspect_hermes_field_receipt(json.loads(current_record_path.read_text(encoding='utf-8')),current_request_identifier)


def list_hermes_field_receipts():
    from datetime import datetime, timezone
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_records_list = []
        for current_record_path in list_delegation_record_paths(current_storage_value.delegation_storage_root):
            if current_record_path.is_symlink() or not current_record_path.is_file():
                continue
            try:
                current_request_identifier = current_record_path.stem
                current_storage_value.resolve_delegation_record_path(current_request_identifier)
                current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_record_value,dict) or current_record_value.get('version') != 4:
                    continue
                current_receipt_value = inspect_hermes_field_receipt(current_record_value,current_request_identifier)
                current_update_time = current_record_path.stat().st_mtime
                current_records_list.append({**current_receipt_value,'updated_at':datetime.fromtimestamp(current_update_time,timezone.utc).isoformat(),'_sort_time':current_update_time})
            except (OSError,ValueError,TypeError,KeyError):
                continue
        current_records_list.sort(key=lambda current_record_value:(current_record_value['_sort_time'],current_record_value['request_id']),reverse=True)
        for current_receipt_value in current_records_list:
            current_receipt_value.pop('_sort_time')
        return {'records':current_records_list[:100],'truncated':len(current_records_list)>100,'note':'손상된 기록은 제외됩니다. 확인 불가는 원본 상태를 별도로 확인하세요.'}


def load_hermes_field_region_source(current_map_identifier):
    """편집 DB 없이 등록된 야외 맵과 타일 코드의 조회 스냅샷을 만든다."""
    import yaml
    from tools.review.common.map_asset_sources import UniqueMapSourceLoader, normalize_field_surface_data, open_registered_map_source_snapshot
    from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
    if not isinstance(current_map_identifier,str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_map_identifier):
        raise ValueError('맵 ID 형식 오류')
    with open_registered_map_source_snapshot():
        current_asset_root,current_asset_records=load_registered_tiles()
        current_relative_paths=[f'field_tiles/{current_map_identifier}.yaml',f'terrain/maps/{current_map_identifier}.yaml','field_tiles/codes.yaml']
        current_source_values=[]
        current_source_hashes={}
        for current_relative_path in current_relative_paths:
            current_source_path,current_source_record=resolve_registered_asset('assets/maps/'+current_relative_path,current_asset_root,current_asset_records,'assets/maps')
            current_source_bytes=current_source_path.read_bytes()
            current_source_hash=hashlib.sha256(current_source_bytes).hexdigest()
            if current_source_hash!=current_source_record['sha256']:raise ValueError('맵 원본이 조회 중 변경되었습니다.')
            current_source_document=yaml.load(current_source_bytes,Loader=UniqueMapSourceLoader)
            if not isinstance(current_source_document,dict) or set(current_source_document)!={'managementId','data'} or current_source_document['managementId']!=current_source_record['managementId'] or not isinstance(current_source_document['data'],dict):
                raise ValueError('맵 원본 관리 문서 오류')
            current_source_values.append(current_source_document['data'])
            current_source_hashes[current_relative_path]=current_source_hash
        current_tiles_value,current_terrain_value,current_codes_value=current_source_values
        normalize_field_surface_data(current_terrain_value)
        current_revision_bytes=json.dumps(current_source_hashes,sort_keys=True,separators=(',',':')).encode()
        return {'map':current_map_identifier,'revision':'asset:'+hashlib.sha256(current_revision_bytes).hexdigest(),'tiles':current_tiles_value,'terrain':current_terrain_value,'codes':current_codes_value}


def read_hermes_field_region(current_request_record):
    """원본 리비전에 고정한 제한 영역과 장식 목록 일부를 반환한다."""
    current_allowed_fields = {'map','column','row','width','height','offset','limit','revision'}
    if not isinstance(current_request_record,dict) or 'map' not in current_request_record or set(current_request_record)-current_allowed_fields:
        raise ValueError('맵과 영역·페이지 조회 필드만 지정하세요.')
    current_column_start = current_request_record.get('column',0)
    current_row_start = current_request_record.get('row',0)
    current_width_value = current_request_record.get('width',8)
    current_height_value = current_request_record.get('height',8)
    current_offset_value = current_request_record.get('offset',0)
    current_limit_value = current_request_record.get('limit',20)
    for current_number_value,current_minimum_value,current_maximum_value in ((current_column_start,0,10000),(current_row_start,0,10000),(current_width_value,1,16),(current_height_value,1,16),(current_offset_value,0,100000),(current_limit_value,1,30)):
        if type(current_number_value) is not int or not current_minimum_value<=current_number_value<=current_maximum_value:
            raise ValueError('맵 영역 또는 페이지 범위 오류')
    current_revision_filter = current_request_record.get('revision')
    if current_revision_filter is not None and (not isinstance(current_revision_filter,str) or not 0<len(current_revision_filter)<=4096):
        raise ValueError('맵 리비전 형식 오류')
    if current_offset_value>0 and current_revision_filter is None:
        raise ValueError('다음 배치 페이지에는 첫 조회의 revision이 필요합니다.')
    current_map_value = load_hermes_field_region_source(current_request_record['map'])
    if current_revision_filter is not None and current_revision_filter != current_map_value['revision']:
        raise ValueError('원본 리비전이 변경됐습니다. 처음부터 다시 조회하세요.')
    current_tiles_value,current_terrain_value = current_map_value['tiles'],current_map_value['terrain']
    if not isinstance(current_tiles_value,dict) or not isinstance(current_terrain_value,dict):
        raise ValueError('맵 데이터 형식 오류')
    current_column_count,current_row_count = current_terrain_value.get('columns'),current_terrain_value.get('rows')
    current_tile_rows,current_elevation_rows = current_tiles_value.get('rows'),current_terrain_value.get('elevations')
    current_blocked_values,current_object_values = current_terrain_value.get('blocked'),current_tiles_value.get('objects',[])
    if (type(current_column_count) is not int or type(current_row_count) is not int or not 1<=current_column_count<=10000 or not 1<=current_row_count<=10000
            or not isinstance(current_tile_rows,list) or len(current_tile_rows)!=current_row_count
            or not isinstance(current_elevation_rows,list) or len(current_elevation_rows)!=current_row_count
            or not isinstance(current_blocked_values,list) or not isinstance(current_object_values,list) or len(current_object_values)>10000):
        raise ValueError('맵 배열 형식 오류')
    if current_column_start>=current_column_count or current_row_start>=current_row_count:
        raise ValueError('맵 영역 시작점이 범위를 벗어났습니다.')
    current_column_end = min(current_column_count,current_column_start+current_width_value)
    current_row_end = min(current_row_count,current_row_start+current_height_value)
    current_blocked_cells = set()
    for current_position_value in current_blocked_values:
        if not isinstance(current_position_value,list) or len(current_position_value)!=2 or any(type(item) is not int for item in current_position_value):
            raise ValueError('차단 좌표 형식 오류')
        current_blocked_cells.add(tuple(current_position_value))
    current_cells_list = []
    for current_row_index in range(current_row_start,current_row_end):
        current_tile_line,current_elevation_line = current_tile_rows[current_row_index],current_elevation_rows[current_row_index]
        if not isinstance(current_tile_line,str) or len(current_tile_line)!=current_column_count or not isinstance(current_elevation_line,list) or len(current_elevation_line)!=current_column_count:
            raise ValueError('맵 행 형식 오류')
        for current_column_index in range(current_column_start,current_column_end):
            current_height_number = current_elevation_line[current_column_index]
            if type(current_height_number) is not int or not 0<=current_height_number<=20:
                raise ValueError('맵 고도 형식 오류')
            current_tile_code = current_tile_line[current_column_index]
            current_codes_value = current_map_value['codes']
            current_tile_name = current_codes_value.get(current_tile_code) if isinstance(current_codes_value,dict) else None
            if not isinstance(current_tile_name,str) or len(current_tile_name)>128:
                raise ValueError('맵 타일 코드 형식 오류')
            current_cells_list.append({'column':current_column_index,'row':current_row_index,'tile':current_tile_code,'terrain':current_tile_name,'height':current_height_number,'blocked':(current_column_index,current_row_index) in current_blocked_cells})
    current_objects_list = []
    for current_object_value in current_object_values:
        if not isinstance(current_object_value,dict) or not isinstance(current_object_value.get('id'),str) or not isinstance(current_object_value.get('kind'),str) or len(current_object_value['id'])>128 or len(current_object_value['kind'])>128:
            raise ValueError('맵 오브젝트 형식 오류')
        current_position_value = current_object_value.get('position')
        if not isinstance(current_position_value,dict) or any(type(current_position_value.get(key)) is not int for key in ('column','row')):
            raise ValueError('맵 오브젝트 좌표 오류')
        current_output_value = {'id':current_object_value['id'],'kind':current_object_value['kind'],'position':{'column':current_position_value['column'],'row':current_position_value['row']}}
        for current_field_name in ('textureKey','tileAnchor'):
            current_field_value = current_object_value.get(current_field_name)
            if current_field_value is not None:
                if not isinstance(current_field_value,str) or len(current_field_value)>128:
                    raise ValueError('맵 오브젝트 속성 오류')
                current_output_value[current_field_name] = current_field_value
        current_objects_list.append(current_output_value)
    from collections import Counter
    current_terrain_counts = dict(sorted(Counter(current_cell_value['terrain'] for current_cell_value in current_cells_list).items()))
    current_height_counts = {str(key):value for key,value in sorted(Counter(current_cell_value['height'] for current_cell_value in current_cells_list).items())}
    current_blocked_count = sum(current_cell_value['blocked'] for current_cell_value in current_cells_list)
    current_total_value = len(current_objects_list)
    return {'map':current_map_value['map'],'revision':current_map_value['revision'],'columns':current_column_count,'rows':current_row_count,
            'region':{'column':current_column_start,'row':current_row_start,'width':current_column_end-current_column_start,'height':current_row_end-current_row_start},
            'cells':current_cells_list,'summary':{'cell_count':len(current_cells_list),'terrain_counts':current_terrain_counts,'height_counts':current_height_counts,'source_blocked_count':current_blocked_count},
            'objects':current_objects_list[current_offset_value:current_offset_value+current_limit_value],
            'object_total':current_total_value,'object_offset':current_offset_value,
            'object_next_offset':current_offset_value+current_limit_value if current_offset_value+current_limit_value<current_total_value else None,
            'note':'blocked는 지형 원본의 차단 값입니다. 빌보드 점유·지형 종류·고도와 실제 통행 판정은 기존 맵 검증에서 별도 확인하세요. 페이지를 이어 읽을 때 revision을 전달하세요. 이 값은 에셋 조회 지문이며 편집 리비전이 아닙니다.'}
