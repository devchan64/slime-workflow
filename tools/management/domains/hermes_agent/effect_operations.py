"""이펙트 공용 좌표 변경 검토와 조건부 저장."""
import hashlib
import json
import math
import re
import uuid

from tools.management.common.generation_records import write_record_atomically
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record, HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
from tools.management.domains.hermes_agent.effect_observer import EFFECT_IDENTIFIER_PATTERN, call_hermes_effect_editor, read_hermes_effect_detail


def write_bounded_effect_receipt(current_receipt_path,current_receipt_record):
    """접수 전에 완료 기록에 필요한 여유를 포함해 크기를 제한한다."""
    current_record_bytes=(json.dumps(current_receipt_record,ensure_ascii=False)+'\n').encode('utf-8')
    current_maximum_bytes=HERMES_DELEGATION_RECORD_MAXIMUM_BYTES-(16384 if current_receipt_record.get('state')=='dispatching' else 0)
    if len(current_record_bytes)>current_maximum_bytes:
        raise ValueError('이펙트 접수 기록 크기 초과')
    write_record_atomically(current_receipt_path,current_receipt_record)


def validate_hermes_effect_edit(current_draft_record):
    if not isinstance(current_draft_record,dict) or set(current_draft_record)!={'id','revision','target','alpha','frames'}:
        raise ValueError('이펙트 ID·revision·target·alpha·frames가 필요합니다.')
    if not isinstance(current_draft_record['id'],str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_draft_record['id']):
        raise ValueError('이펙트 ID 오류')
    if not isinstance(current_draft_record['revision'],str) or not re.fullmatch(r'[a-f0-9]{64}',current_draft_record['revision']):
        raise ValueError('이펙트 revision 오류')
    current_alpha_value=current_draft_record['alpha']
    if type(current_alpha_value) not in (int,float) or not math.isfinite(current_alpha_value) or not 0<=current_alpha_value<=1:
        raise ValueError('불투명도는 0~1입니다.')
    current_frames_value=current_draft_record['frames']
    if not isinstance(current_frames_value,list) or not 1<=len(current_frames_value)<=256:
        raise ValueError('프레임 목록 오류')
    for current_rectangle_value in [current_draft_record['target'],*current_frames_value]:
        if not isinstance(current_rectangle_value,list) or len(current_rectangle_value)!=4 or any(type(current_number_value) not in (int,float) or not math.isfinite(current_number_value) or not 0<=current_number_value<=1 for current_number_value in current_rectangle_value):
            raise ValueError('사각형 좌표는 0~1의 숫자 네 개여야 합니다.')
        if current_rectangle_value[0]>=current_rectangle_value[2] or current_rectangle_value[1]>=current_rectangle_value[3]:
            raise ValueError('사각형의 폭과 높이는 양수여야 합니다.')
    return hashlib.sha256(json.dumps(current_draft_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def preview_hermes_effect_edit(current_draft_record):
    current_preview_token=validate_hermes_effect_edit(current_draft_record)
    current_original_record=read_hermes_effect_detail(current_draft_record['id'])
    if current_original_record['revision']!=current_draft_record['revision']:
        raise ValueError('이펙트가 변경되었습니다. 다시 조회하세요.')
    current_original_values=current_original_record['alignment']
    if not isinstance(current_original_values,dict):
        raise ValueError('공용 좌표 편집을 지원하지 않는 이펙트입니다.')
    if len(current_draft_record['frames'])!=current_original_record['frames']:
        raise ValueError('이펙트의 프레임 수가 일치하지 않습니다.')
    current_updated_values={**current_original_values,**{current_field_name:current_draft_record[current_field_name] for current_field_name in ('target','alpha','frames')}}
    if current_updated_values==current_original_values:
        raise ValueError('변경된 좌표가 없습니다.')
    return {'id':current_draft_record['id'],'revision':current_draft_record['revision'],'before':current_original_values,'after':current_updated_values,'token':current_preview_token,'note':'공용 좌표 변경은 같은 이펙트를 사용하는 맵에 영향을 줄 수 있습니다. DB 저장 후 원장 동기화와 실행 중인 서비스 반영, 이미지와 실제 배치는 별도로 확인하세요.'}


def inspect_hermes_effect_receipt(current_receipt_record,current_request_identifier):
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('version')!=8 or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed'):
        raise ValueError('이펙트 저장 접수 기록 오류')
    current_effect_identifier=current_receipt_record.get('effect_id')
    if current_effect_identifier is not None and (not isinstance(current_effect_identifier,str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_effect_identifier)):
        raise ValueError('이펙트 접수 대상 오류')
    current_target_record={'effect_id':current_effect_identifier} if current_effect_identifier is not None else {}
    if current_receipt_record['state']=='dispatching':
        return {'request_id':current_request_identifier,'state':'unknown','saved':None,**current_target_record}
    if current_receipt_record.get('saved') is not True:
        raise ValueError('이펙트 저장 접수 상태 오류')
    current_result_record={'request_id':current_request_identifier,'state':'completed','saved':True,'revision':current_receipt_record['revision'],**current_target_record}
    current_generation_value=current_receipt_record.get('generation')
    if type(current_generation_value) is int and current_generation_value>=1 and current_receipt_record.get('ledger_status_at_save')=='pending':
        current_result_record.update(generation=current_generation_value,ledger_status_at_save='pending')
    return current_result_record


def save_hermes_effect_edit_once(current_request_identifier,current_draft_record,current_preview_token):
    if current_preview_token!=validate_hermes_effect_edit(current_draft_record):
        raise ValueError('검토한 좌표와 토큰이 일치하지 않습니다.')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_record=read_bounded_delegation_record(current_receipt_path)
            current_result_record=inspect_hermes_effect_receipt(current_receipt_record,current_request_identifier)
            if current_receipt_record.get('token')!=current_preview_token:
                raise ValueError('같은 접수 ID를 다른 변경에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        current_preview_record=preview_hermes_effect_edit(current_draft_record)
        current_receipt_record={'version':8,'id':current_request_identifier,'token':current_preview_token,'state':'dispatching','effect_id':current_draft_record['id']}
        write_bounded_effect_receipt(current_receipt_path,current_receipt_record)
        current_database_request_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'slime-hermes-effect:'+current_request_identifier))
        current_save_record=call_hermes_effect_editor('effect-save',{'id':current_draft_record['id'],'expectedRevision':current_draft_record['revision'],'requestId':current_database_request_id,'alignment':current_preview_record['after']})
        if not isinstance(current_save_record,dict) or current_save_record.get('saved') is not True or not isinstance(current_save_record.get('revision'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_save_record['revision']):
            raise ValueError('이펙트 저장 결과 확인 필요. 자동 재접수하지 않습니다.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_record:raise ValueError('저장 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_receipt_record.update(state='completed',saved=True,revision=current_save_record['revision'])
        if type(current_save_record.get('generation')) is int and current_save_record['generation']>=1 and current_save_record.get('snapshot')=='pending':
            current_receipt_record.update(generation=current_save_record['generation'],ledger_status_at_save='pending')
        write_bounded_effect_receipt(current_receipt_path,current_receipt_record)
        return {**inspect_hermes_effect_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_hermes_effect_edit_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):
            return {'state':'not_found'}
        return inspect_hermes_effect_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)


def validate_hermes_waypoint_asset_files(current_source_paths,current_sources_value,current_expected_frames):
    """등록된 원본 해시와 시트·프레임 범위를 확인한다."""
    from PIL import Image
    from tools.management.common.management_gateway import parse_management_request_json
    current_metadata_bytes=current_source_paths['animation'].read_bytes()
    if hashlib.sha256(current_metadata_bytes).hexdigest()!=current_sources_value['animation']['sha256']:
        raise ValueError('애니메이션 원본이 검토 중 변경됐습니다.')
    current_metadata_value=parse_management_request_json(current_metadata_bytes.decode('utf-8'))
    if not isinstance(current_metadata_value,dict) or not isinstance(current_metadata_value.get('frames'),list) or len(current_metadata_value['frames'])!=current_expected_frames:
        raise ValueError('웨이포인트 애니메이션 프레임 수가 일치하지 않습니다.')
    current_image_bytes=current_source_paths['image'].read_bytes()
    if hashlib.sha256(current_image_bytes).hexdigest()!=current_sources_value['image']['sha256']:
        raise ValueError('이미지 원본이 검토 중 변경됐습니다.')
    import io
    with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
        if current_image_value.format!='PNG':
            raise ValueError('웨이포인트 이미지는 PNG여야 합니다.')
        current_sheet_size=current_image_value.size
        current_image_value.verify()
    current_sheet_value=current_metadata_value.get('sheet')
    if not isinstance(current_sheet_value,dict) or (current_sheet_value.get('width'),current_sheet_value.get('height'))!=current_sheet_size:
        raise ValueError('웨이포인트 시트 크기가 애니메이션 메타데이터와 일치하지 않습니다.')
    for current_frame_value in current_metadata_value['frames']:
        current_rectangle_value=current_frame_value.get('rect') if isinstance(current_frame_value,dict) else None
        if not isinstance(current_rectangle_value,dict) or set(current_rectangle_value)!={'x','y','width','height'} or any(type(current_rectangle_value[key]) is not int for key in ('x','y','width','height')):
            raise ValueError('웨이포인트 프레임 좌표 형식 오류')
        if current_rectangle_value['x']<0 or current_rectangle_value['y']<0 or current_rectangle_value['width']<1 or current_rectangle_value['height']<1 or current_rectangle_value['x']+current_rectangle_value['width']>current_sheet_size[0] or current_rectangle_value['y']+current_rectangle_value['height']>current_sheet_size[1]:
            raise ValueError('웨이포인트 프레임이 이미지 범위를 벗어났습니다.')
    return current_sheet_size


def preview_hermes_waypoint_replacement(current_draft_record):
    """등록된 새 원본과 기존 웨이포인트 리비전을 함께 검토한다."""
    from tools.management.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
    if not isinstance(current_draft_record,dict) or set(current_draft_record)!={'id','revision','effect'}:
        raise ValueError('교체 대상 ID·revision·새 이펙트가 필요합니다.')
    current_identifier_value=current_draft_record['id']
    current_revision_value=current_draft_record['revision']
    current_effect_value=current_draft_record['effect']
    if not isinstance(current_identifier_value,str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_identifier_value):
        raise ValueError('기존 이펙트 ID 오류')
    if not isinstance(current_revision_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_revision_value):
        raise ValueError('이펙트 revision 오류')
    if not isinstance(current_effect_value,dict) or set(current_effect_value)!={'id','name','image','animation','renderer','columns','rows','frames'}:
        raise ValueError('새 웨이포인트 필드 오류')
    current_new_identifier=current_effect_value['id']
    if not isinstance(current_new_identifier,str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_new_identifier) or current_new_identifier==current_identifier_value:
        raise ValueError('새 이펙트 ID 오류')
    if not isinstance(current_effect_value['name'],str) or not 1<=len(current_effect_value['name'])<=200:
        raise ValueError('새 이펙트 이름 오류')
    if current_effect_value['renderer']!='waypoint-animation' or any(type(current_effect_value[key]) is not int for key in ('columns','rows','frames')) or (current_effect_value['columns'],current_effect_value['rows'],current_effect_value['frames'])!=(4,2,8):
        raise ValueError('새 웨이포인트는 4×2 8프레임이어야 합니다.')
    check_hermes_effect_registration(current_effect_value)
    current_original_value=read_hermes_effect_detail(current_identifier_value)
    if current_original_value['revision']!=current_revision_value or current_original_value['renderer']!='waypoint-animation':
        raise ValueError('기존 웨이포인트 또는 리비전이 변경되었습니다.')
    current_asset_root,current_asset_records=load_registered_tiles()
    current_sources_value={}
    current_source_paths={}
    for current_field_name in ('image','animation'):
        current_source_path,current_provenance_value=resolve_registered_asset(current_effect_value[current_field_name],current_asset_root,current_asset_records,'assets/sprites/effects')
        current_sources_value[current_field_name]=current_provenance_value
        current_source_paths[current_field_name]=current_source_path
    current_sheet_size=validate_hermes_waypoint_asset_files(current_source_paths,current_sources_value,current_effect_value['frames'])
    current_review_value={'before':current_original_value,'after':current_effect_value,'sources':current_sources_value,'sheet_pixels':{'width':current_sheet_size[0],'height':current_sheet_size[1]},'metadata_frames':current_effect_value['frames']}
    current_review_hash=hashlib.sha256(json.dumps(current_review_value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {**current_review_value,'review_sha256':current_review_hash,'note':'교체는 콘텐츠 DB의 기존 이펙트 ID를 제거합니다. 게임은 에셋 저장소 원본을 직접 참조하므로 이 교체만으로 게임 표시는 변경되지 않습니다. 실제 외형과 사용 맵, 게임 참조·잠금 목록의 별도 갱신을 확인하세요.'}


def replace_hermes_waypoint_once(current_request_identifier,current_draft_record,current_review_hash):
    """검토 결과가 유지될 때만 기존 원장 교체를 한 번 요청한다."""
    if not isinstance(current_review_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_hash):
        raise ValueError('검토 해시 오류')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_value=read_bounded_delegation_record(current_receipt_path)
            if not isinstance(current_receipt_value,dict) or current_receipt_value.get('version')!=9 or current_receipt_value.get('id')!=current_request_identifier or current_receipt_value.get('review_sha256')!=current_review_hash or current_receipt_value.get('draft')!=current_draft_record:
                raise ValueError('기존 접수 기록과 교체 입력이 일치하지 않습니다.')
            if current_receipt_value.get('state')=='dispatching':
                return {'request_id':current_request_identifier,'state':'unknown','duplicate':True}
            if current_receipt_value.get('state')!='completed' or current_receipt_value.get('result_id')!=current_draft_record.get('effect',{}).get('id'):
                raise ValueError('이펙트 교체 접수 기록 오류')
            return {'request_id':current_request_identifier,'state':'completed','id':current_receipt_value['result_id'],'generation':current_receipt_value.get('generation'),'ledger_status_at_save':current_receipt_value.get('ledger_status_at_save','unknown'),'duplicate':True}
        current_review_value=preview_hermes_waypoint_replacement(current_draft_record)
        if current_review_value['review_sha256']!=current_review_hash:
            raise ValueError('원본 또는 검토 내용이 변경됐습니다. 다시 검토하세요.')
        current_receipt_value={'version':9,'id':current_request_identifier,'review_sha256':current_review_hash,'draft':current_draft_record,'state':'dispatching'}
        write_bounded_effect_receipt(current_receipt_path,current_receipt_value)
        current_database_request=str(uuid.uuid5(uuid.NAMESPACE_URL,'slime-hermes-effect-replace:'+current_request_identifier))
        current_result_value=call_hermes_effect_editor('effect-replace',{'id':current_draft_record['id'],'expectedRevision':current_draft_record['revision'],'requestId':current_database_request,'effect':current_draft_record['effect']})
        if not isinstance(current_result_value,dict) or current_result_value.get('saved') is not True or current_result_value.get('id')!=current_draft_record['effect']['id'] or current_result_value.get('replaced')!=current_draft_record['id'] or type(current_result_value.get('generation')) is not int or current_result_value['generation']<1 or current_result_value.get('snapshot')!='pending':
            raise ValueError('교체 결과 확인 필요. 자동 재접수하지 않습니다.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_value:raise ValueError('저장 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_receipt_value.update(state='completed',result_id=current_result_value['id'],generation=current_result_value['generation'],ledger_status_at_save='pending')
        write_bounded_effect_receipt(current_receipt_path,current_receipt_value)
        return {'request_id':current_request_identifier,'state':'completed','id':current_result_value['id'],'generation':current_result_value['generation'],'ledger_status_at_save':'pending','duplicate':False}


def read_hermes_waypoint_replacement_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):
            return {'state':'not_found'}
        current_receipt_value=read_bounded_delegation_record(current_receipt_path)
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('version')!=9 or current_receipt_value.get('id')!=current_request_identifier:
            raise ValueError('이펙트 교체 접수 기록 오류')
        if current_receipt_value.get('state')=='dispatching':
            return {'request_id':current_request_identifier,'state':'unknown'}
        current_saved_draft=current_receipt_value.get('draft')
        current_saved_effect=current_saved_draft.get('effect') if isinstance(current_saved_draft,dict) else None
        if current_receipt_value.get('state')!='completed' or not isinstance(current_saved_effect,dict) or current_receipt_value.get('result_id')!=current_saved_effect.get('id') or not isinstance(current_receipt_value.get('result_id'),str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_receipt_value['result_id']):
            raise ValueError('이펙트 교체 접수 기록 오류')
        return {'request_id':current_request_identifier,'state':'completed','id':current_receipt_value['result_id'],'generation':current_receipt_value.get('generation'),'ledger_status_at_save':current_receipt_value.get('ledger_status_at_save','unknown')}


def check_hermes_effect_registration(current_effect_record):
    current_conflict_value=call_hermes_effect_editor('effect-register-check',current_effect_record)
    if not isinstance(current_conflict_value,dict) or current_conflict_value.get('available') is not True:
        raise ValueError('이펙트 등록 충돌을 확인할 수 없습니다.')


def preview_hermes_effect_registration(current_effect_record):
    """등록된 이미지 원본과 신규 이펙트의 기본 규격을 검토한다."""
    from tools.management.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
    current_required_fields={'id','name','image','renderer','columns','rows','frames'}
    if not isinstance(current_effect_record,dict) or not current_required_fields<=set(current_effect_record) or set(current_effect_record)-current_required_fields-{'animation','alignment'}:
        raise ValueError('이펙트 등록 필드 오류')
    if not isinstance(current_effect_record['id'],str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_effect_record['id']):
        raise ValueError('이펙트 ID 오류')
    if not isinstance(current_effect_record['name'],str) or not 1<=len(current_effect_record['name'])<=200:
        raise ValueError('이펙트 이름 오류')
    if current_effect_record['renderer'] not in ('swarm','billboard-glow','fog','safe-barrier-aura','waypoint-animation'):
        raise ValueError('지원하지 않는 이펙트 렌더러입니다.')
    if any(type(current_effect_record[key]) is not int or not 1<=current_effect_record[key]<=256 for key in ('columns','rows','frames')) or current_effect_record['frames']>current_effect_record['columns']*current_effect_record['rows']:
        raise ValueError('이펙트 프레임 규격 오류')
    if current_effect_record['renderer']=='safe-barrier-aura' and 'alignment' in current_effect_record:
        raise ValueError('안전지대 오라는 이펙트 좌표 alignment를 사용하지 않습니다.')
    if current_effect_record['renderer']!='waypoint-animation' and 'animation' in current_effect_record:
        raise ValueError('애니메이션 메타데이터는 웨이포인트 렌더러에서만 지원합니다.')
    if current_effect_record['renderer'] in ('swarm','billboard-glow','fog') and 'alignment' not in current_effect_record:
        raise ValueError('이 렌더러는 검수와 사용을 위한 alignment가 필요합니다.')
    if 'alignment' in current_effect_record:
        current_alignment=current_effect_record['alignment']
        if (current_effect_record['columns'],current_effect_record['rows'],current_effect_record['frames'])!=(4,2,8) or not isinstance(current_alignment,dict) or set(current_alignment)!={'key','texture','target','alpha','frames'}:
            raise ValueError('이펙트 정렬 규격 오류')
        if any(not isinstance(current_alignment[key],str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_alignment[key]) for key in ('key','texture')):
            raise ValueError('이펙트 연결 ID 오류')
        validate_hermes_effect_edit({'id':current_effect_record['id'],'revision':'0'*64,**{key:current_alignment[key] for key in ('target','alpha','frames')}})
        if len(current_alignment['frames'])!=current_effect_record['frames']:
            raise ValueError('이펙트 정렬 프레임 수 오류')
    current_linked_billboard=None
    if current_effect_record['renderer']=='billboard-glow':
        current_catalog_value=call_hermes_effect_editor('asset-list',{})
        if not isinstance(current_catalog_value,dict) or current_catalog_value.get('storage')!='database' or not isinstance(current_catalog_value.get('assets'),list):
            raise ValueError('콘텐츠 DB의 빌보드 목록을 확인할 수 없습니다.')
        current_texture_value=current_effect_record['alignment']['texture']
        current_matches=[item for item in current_catalog_value['assets'] if isinstance(item,dict) and item.get('texture')==current_texture_value]
        if len(current_matches)!=1:
            raise ValueError('연결할 빌보드를 찾을 수 없거나 중복되었습니다.')
        current_billboard_revision=current_matches[0].get('databaseRevision')
        if type(current_billboard_revision) is not int or current_billboard_revision < 1:
            raise ValueError('빌보드 DB 리비전을 확인할 수 없습니다.')
        current_linked_billboard={'texture':current_texture_value,'revision':current_billboard_revision,'note':'DB 목록 기준 존재 확인이며 이미지와 실제 배치는 별도 검수합니다.'}
    if current_effect_record['renderer']=='waypoint-animation' and ((current_effect_record['columns'],current_effect_record['rows'],current_effect_record['frames'])!=(4,2,8) or 'animation' not in current_effect_record or 'alignment' in current_effect_record):
        raise ValueError('웨이포인트는 애니메이션 원본이 있는 4×2 8프레임이어야 합니다.')
    check_hermes_effect_registration(current_effect_record)
    current_asset_root,current_asset_records=load_registered_tiles()
    current_sources_value={}
    current_source_paths={}
    for current_field_name in ('image','animation'):
        if current_field_name in current_effect_record:
            current_source_path,current_provenance_value=resolve_registered_asset(current_effect_record[current_field_name],current_asset_root,current_asset_records,'assets/sprites/effects')
            current_sources_value[current_field_name]=current_provenance_value
            current_source_paths[current_field_name]=current_source_path
    import io
    from PIL import Image
    current_image_bytes=current_source_paths['image'].read_bytes()
    if hashlib.sha256(current_image_bytes).hexdigest()!=current_sources_value['image']['sha256']:
        raise ValueError('이펙트 이미지 원본이 검토 중 변경됐습니다.')
    with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
        if current_image_value.format!='PNG':
            raise ValueError('이펙트 이미지는 PNG여야 합니다.')
        current_sheet_size=current_image_value.size
        current_image_value.verify()
    if current_sheet_size[0]<current_effect_record['columns'] or current_sheet_size[1]<current_effect_record['rows']:
        raise ValueError('시트 크기가 행·열보다 작습니다.')
    if current_effect_record['renderer']=='waypoint-animation':
        current_sheet_size=validate_hermes_waypoint_asset_files(current_source_paths,current_sources_value,current_effect_record['frames'])
    current_review_value={'effect':current_effect_record,'sources':current_sources_value,'sheet_pixels':{'width':current_sheet_size[0],'height':current_sheet_size[1]},'effect_editor_available':current_effect_record['renderer']!='safe-barrier-aura','linked_billboard':current_linked_billboard}
    current_review_hash=hashlib.sha256(json.dumps(current_review_value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {**current_review_value,'review_sha256':current_review_hash,'note':'신규 ID 중복 여부는 저장 시 콘텐츠 DB에서 확인합니다. 안전지대 오라는 이펙트 좌표 검수기에 표시되지 않습니다. 등록만으로 게임 원본 참조가 갱신되지는 않습니다.'}


def register_hermes_effect_once(current_request_identifier,current_effect_record,current_review_hash):
    """응답이 유실된 신규 등록을 자동 재전송하지 않는다."""
    if not isinstance(current_review_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_hash):
        raise ValueError('검토 해시 오류')
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_value=read_bounded_delegation_record(current_receipt_path)
            if not isinstance(current_receipt_value,dict) or current_receipt_value.get('version')!=10 or current_receipt_value.get('id')!=current_request_identifier or current_receipt_value.get('review_sha256')!=current_review_hash or current_receipt_value.get('effect')!=current_effect_record:
                raise ValueError('기존 접수 기록과 등록 입력이 일치하지 않습니다.')
            if current_receipt_value.get('state')=='dispatching':
                return {'request_id':current_request_identifier,'state':'unknown','duplicate':True}
            if current_receipt_value.get('state')!='completed' or current_receipt_value.get('result_id')!=current_effect_record.get('id'):
                raise ValueError('이펙트 등록 접수 기록 오류')
            return {'request_id':current_request_identifier,'state':'completed','id':current_receipt_value['result_id'],'generation':current_receipt_value['generation'],'duplicate':True}
        current_review_value=preview_hermes_effect_registration(current_effect_record)
        if current_review_value['review_sha256']!=current_review_hash:
            raise ValueError('등록 원본 또는 검토 내용이 변경됐습니다.')
        current_receipt_value={'version':10,'id':current_request_identifier,'review_sha256':current_review_hash,'effect':current_effect_record,'state':'dispatching'}
        write_bounded_effect_receipt(current_receipt_path,current_receipt_value)
        if 'alignment' in current_effect_record:
            current_target_revision=current_review_value['linked_billboard']['revision'] if current_review_value['linked_billboard'] else None
            current_result_value=call_hermes_effect_editor('effect-register-reviewed',{'effect':current_effect_record,'target_revision':current_target_revision})
        else:
            current_result_value=call_hermes_effect_editor('effect-register',current_effect_record)
        if not isinstance(current_result_value,dict) or current_result_value.get('created') is not True or current_result_value.get('id')!=current_effect_record['id'] or type(current_result_value.get('generation')) is not int or current_result_value['generation']<1 or current_result_value.get('snapshot')!='pending':
            raise ValueError('등록 결과 확인 필요. 자동 재접수하지 않습니다.')
        if read_bounded_delegation_record(current_receipt_path)!=current_receipt_value:raise ValueError('저장 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재저장하지 마세요.')
        current_receipt_value.update(state='completed',result_id=current_result_value['id'],generation=current_result_value['generation'])
        write_bounded_effect_receipt(current_receipt_path,current_receipt_value)
        return {'request_id':current_request_identifier,'state':'completed','id':current_result_value['id'],'generation':current_result_value['generation'],'duplicate':False}


def read_hermes_effect_registration_receipt(current_request_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_receipt_path=current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):
            return {'state':'not_found'}
        current_receipt_value=read_bounded_delegation_record(current_receipt_path)
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('version')!=10 or current_receipt_value.get('id')!=current_request_identifier:
            raise ValueError('이펙트 등록 접수 기록 오류')
        if current_receipt_value.get('state')=='dispatching':
            return {'request_id':current_request_identifier,'state':'unknown'}
        current_effect_value=current_receipt_value.get('effect')
        if current_receipt_value.get('state')!='completed' or not isinstance(current_effect_value,dict) or current_receipt_value.get('result_id')!=current_effect_value.get('id') or not isinstance(current_receipt_value.get('result_id'),str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_receipt_value['result_id']) or type(current_receipt_value.get('generation')) is not int or current_receipt_value['generation']<1:
            raise ValueError('이펙트 등록 접수 기록 오류')
        return {'request_id':current_request_identifier,'state':'completed','id':current_receipt_value['result_id'],'generation':current_receipt_value['generation'],'ledger_status_at_save':'pending'}
