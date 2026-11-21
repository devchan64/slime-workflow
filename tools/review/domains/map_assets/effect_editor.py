"""이펙트 좌표 검수의 공용 DB 명령. 이미지는 기존 등록 원본을 조회한다."""
import base64
import hashlib
import json
from pathlib import Path

import yaml
from urllib.parse import quote
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset


def validate_effect_registration_conflicts(current_effect_value):
    """현재 콘텐츠 DB에서 신규 ID와 정렬 연결의 충돌을 확인한다."""
    if not isinstance(current_effect_value,dict) or not isinstance(current_effect_value.get('id'),str):
        raise ValueError('신규 이펙트 ID 오류')
    current_required_capability={'billboard-glow':'reviewedBillboardEffectRegistration','swarm':'effectAlignmentUniqueness','fog':'effectAlignmentUniqueness'}.get(current_effect_value.get('renderer'))
    if current_required_capability:
        current_status_record=execute_content_api_request('GET','/internal/v1/content/status')
        if not isinstance(current_status_record,dict) or not isinstance(current_status_record.get('capabilities'),dict) or current_status_record['capabilities'].get(current_required_capability) is not True:
            raise ValueError('콘텐츠 서비스가 요청한 이펙트 등록 또는 교체를 지원하지 않습니다. 에셋 서비스를 업데이트한 뒤 다시 검토하세요.')
    current_alignment_value=current_effect_value.get('alignment')
    current_texture_value=current_alignment_value.get('texture') if isinstance(current_alignment_value,dict) else None
    current_key_value=current_alignment_value.get('key') if isinstance(current_alignment_value,dict) else None
    current_effect_list=execute_content_api_request('GET','/internal/v1/content/effects')
    if not isinstance(current_effect_list,dict) or not isinstance(current_effect_list.get('effects'),list):
        raise ValueError('콘텐츠 DB 이펙트 목록 오류')
    for current_existing_effect in current_effect_list['effects']:
        if not isinstance(current_existing_effect,dict):
            raise ValueError('콘텐츠 DB 이펙트 항목 오류')
        current_existing_alignment=current_existing_effect.get('alignment')
        if current_existing_effect.get('id')==current_effect_value.get('id') or isinstance(current_alignment_value,dict) and isinstance(current_existing_alignment,dict) and (current_existing_alignment.get('texture')==current_texture_value or current_existing_alignment.get('key')==current_key_value):
            raise ValueError('동일 ID 또는 정렬 텍스처·키를 사용하는 이펙트가 이미 있습니다.')
    return {'available':True}


def register_reviewed_effect_with_target(current_request_payload):
    """공용 편집 잠금 안에서 이펙트 충돌과 대상 리비전을 확인한다."""
    import re
    from tools.review.domains.map_assets.database_editor import load_database_editor_catalog
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'effect','target_revision'}:
        raise ValueError('이펙트와 검토한 대상 리비전이 필요합니다.')
    current_effect_value=current_request_payload['effect']
    if not isinstance(current_effect_value,dict) or not isinstance(current_effect_value.get('alignment'),dict):
        raise ValueError('정렬 정보가 있는 이펙트만 지원합니다.')
    current_alignment_value=current_effect_value['alignment']
    current_texture_value=current_alignment_value.get('texture')
    current_key_value=current_alignment_value.get('key')
    if any(not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,95}',value) for value in (current_texture_value,current_key_value)):
        raise ValueError('이펙트 연결 식별자 오류')
    validate_effect_registration_conflicts(current_effect_value)
    if current_effect_value.get('renderer')=='billboard-glow':
        if type(current_request_payload['target_revision']) is not int or current_request_payload['target_revision'] < 1:
            raise ValueError('빌보드 대상 리비전 오류')
        current_catalog_value=load_database_editor_catalog({})
        if not isinstance(current_catalog_value,dict) or not isinstance(current_catalog_value.get('assets'),list):
            raise ValueError('빌보드 DB 목록 오류')
        current_matches=[item for item in current_catalog_value['assets'] if isinstance(item,dict) and item.get('texture')==current_texture_value]
        if current_catalog_value.get('storage')!='database' or len(current_matches)!=1 or current_matches[0].get('databaseRevision')!=current_request_payload['target_revision']:
            raise ValueError('빌보드 대상이 변경되었습니다. 다시 검토하세요.')
        current_asset_root,current_asset_records=load_registered_tiles()
        for current_path_field in ('image','animation'):
            if current_path_field=='image' or current_path_field in current_effect_value:
                resolve_registered_asset(current_effect_value.get(current_path_field),current_asset_root,current_asset_records,'assets/sprites/effects')
        return execute_content_api_request('POST','/internal/v1/content/effects/reviewed',{'effect':current_effect_value,'expectedBillboardRevision':current_request_payload['target_revision']})
    elif current_request_payload['target_revision'] is not None:
        raise ValueError('빌보드 발광이 아닌 이펙트에 대상 리비전을 사용할 수 없습니다.')
    return execute_effect_editor_command('effect-register',current_effect_value)


def execute_effect_editor_command(current_command_name,current_request_payload):
    if current_command_name=='effect-replace':
        if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'id','expectedRevision','requestId','effect'}:raise ValueError('기존 ID·리비전·요청 ID·새 이펙트가 필요합니다.')
        current_asset_root,current_asset_records=load_registered_tiles()
        current_new_effect=current_request_payload['effect']
        if not isinstance(current_new_effect,dict):raise ValueError('새 이펙트 형식 오류')
        for current_path_field in ('image','animation'):
            resolve_registered_asset(current_new_effect.get(current_path_field),current_asset_root,current_asset_records,'assets/sprites/effects')
        return execute_content_api_request('POST','/internal/v1/content/effects/'+quote(current_request_payload['id'],safe='')+'/replace',{k:v for k,v in current_request_payload.items() if k!='id'})
    if current_command_name=='effect-register':
        if not isinstance(current_request_payload,dict):
            raise ValueError('이펙트 등록 입력은 객체여야 합니다.')
        validate_effect_registration_conflicts(current_request_payload)
        current_asset_root,current_asset_records=load_registered_tiles()
        for current_path_field in ('image','animation'):
            if current_path_field=='image' or current_path_field in current_request_payload:
                resolve_registered_asset(current_request_payload.get(current_path_field),current_asset_root,current_asset_records,'assets/sprites/effects')
        return execute_content_api_request('POST','/internal/v1/content/effects',current_request_payload)
    if current_command_name=='effect-save':
        if set(current_request_payload) not in ({'id','expectedRevision','requestId','alignment'},{'id','expectedRevision','requestId','alignment','image'}):
            raise ValueError('이펙트 저장 필드 오류')
        if 'image' in current_request_payload:
            current_asset_root,current_asset_records=load_registered_tiles()
            resolve_registered_asset(current_request_payload['image'],current_asset_root,current_asset_records,'assets/sprites/effects')
        return execute_content_api_request('PATCH','/internal/v1/content/effects/'+quote(current_request_payload['id'],safe=''),{current_field_name:current_field_value for current_field_name,current_field_value in current_request_payload.items() if current_field_name!='id'})
    current_effect_records=execute_content_api_request('GET','/internal/v1/content/effects')['effects']
    if current_command_name=='effect-list':
        if current_request_payload!={}:raise ValueError('목록 조회는 빈 입력을 사용합니다.')
        return {'effects':[{'id':current_effect_record['id'],'name':current_effect_record['name']} for current_effect_record in current_effect_records if 'alignment' in current_effect_record or current_effect_record.get('renderer')=='waypoint-animation']}
    if current_command_name!='effect-load' or set(current_request_payload)!={'id'}:raise ValueError('지원하지 않는 이펙트 명령·입력')
    current_effect_record=next((current_record for current_record in current_effect_records if current_record['id']==current_request_payload['id']),None)
    if not current_effect_record or ('alignment' not in current_effect_record and current_effect_record.get('renderer')!='waypoint-animation'):raise ValueError('검수용 이펙트를 선택하세요.')
    current_asset_root,current_asset_records=load_registered_tiles()
    current_image_path,_=resolve_registered_asset(current_effect_record['image'],current_asset_root,current_asset_records,'assets/sprites/effects')
    current_billboard_bytes=None
    if current_effect_record['renderer'] not in ('swarm','fog','waypoint-animation'):
        current_billboard_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_effect_record['alignment']['texture'],safe=''))
        current_billboard_path=(current_asset_root/current_billboard_record['image']['path']).resolve()
        if not current_billboard_path.is_relative_to(current_asset_root/'assets/billboards'):raise ValueError('빌보드 경로 이탈')
        current_billboard_bytes=current_billboard_path.read_bytes()
        if hashlib.sha256(current_billboard_bytes).hexdigest()!=current_billboard_record['image']['sha256']:raise ValueError('빌보드 이미지 해시 불일치')
    current_animation_metadata=None
    if current_effect_record['renderer']=='waypoint-animation':
        current_metadata_path,_=resolve_registered_asset(current_effect_record['animation'],current_asset_root,current_asset_records,'assets/sprites/effects')
        current_animation_metadata=json.loads(current_metadata_path.read_text())
        if len(current_animation_metadata.get('frames',[])) != current_effect_record['frames']:
            raise ValueError('웨이포인트 애니메이션 프레임 수 오류')
    manifest_path=Path(__file__).resolve().parents[2]/'ui/map/vendor/field-renderer/manifest.yaml'
    version=yaml.safe_load(manifest_path.read_text())['version']
    return {'rendererModule':f'/isloon-map-review/vendor/field-renderer/{version}/field-renderer.mjs','animationMetadata':current_animation_metadata,'document':current_effect_record,'revision':hashlib.sha256(json.dumps(current_effect_record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        'sheetImage':'data:image/png;base64,'+base64.b64encode(current_image_path.read_bytes()).decode(),
        'hostImage':('data:image/png;base64,'+base64.b64encode(current_billboard_bytes).decode()) if current_billboard_bytes is not None else None}
