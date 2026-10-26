"""이펙트 좌표 검수의 공용 DB 명령. 이미지는 기존 등록 원본을 조회한다."""
import base64
import hashlib
import json
from urllib.parse import quote
from tools.review.domains.map_assets.database_client import execute_content_api_request
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset


def execute_effect_editor_command(current_command_name,current_request_payload):
    if current_command_name=='effect-save':
        if set(current_request_payload)!={'id','expectedRevision','requestId','alignment'}:
            raise ValueError('이펙트 저장 필드 오류')
        return execute_content_api_request('PATCH','/internal/v1/content/effects/'+quote(current_request_payload['id'],safe=''),{current_field_name:current_field_value for current_field_name,current_field_value in current_request_payload.items() if current_field_name!='id'})
    current_effect_records=execute_content_api_request('GET','/internal/v1/content/effects')['effects']
    if current_command_name=='effect-list':
        if current_request_payload!={}:raise ValueError('목록 조회는 빈 입력을 사용합니다.')
        return {'effects':[{'id':current_effect_record['id'],'name':current_effect_record['name']} for current_effect_record in current_effect_records if 'alignment' in current_effect_record]}
    if current_command_name!='effect-load' or set(current_request_payload)!={'id'}:raise ValueError('지원하지 않는 이펙트 명령·입력')
    current_effect_record=next((current_record for current_record in current_effect_records if current_record['id']==current_request_payload['id']),None)
    if not current_effect_record or 'alignment' not in current_effect_record:raise ValueError('좌표 검수용 이펙트를 선택하세요.')
    current_asset_root,current_asset_records=load_registered_tiles()
    current_image_path,_=resolve_registered_asset(current_effect_record['image'],current_asset_root,current_asset_records,'assets/sprites/effects')
    current_billboard_bytes=None
    if current_effect_record['renderer']!='swarm':
        current_billboard_record=execute_content_api_request('GET','/internal/v1/content/billboards/'+quote(current_effect_record['alignment']['texture'],safe=''))
        current_billboard_path=(current_asset_root/current_billboard_record['image']['path']).resolve()
        if not current_billboard_path.is_relative_to(current_asset_root/'assets/billboards'):raise ValueError('빌보드 경로 이탈')
        current_billboard_bytes=current_billboard_path.read_bytes()
        if hashlib.sha256(current_billboard_bytes).hexdigest()!=current_billboard_record['image']['sha256']:raise ValueError('빌보드 이미지 해시 불일치')
    return {'document':current_effect_record,'revision':hashlib.sha256(json.dumps(current_effect_record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        'sheetImage':'data:image/png;base64,'+base64.b64encode(current_image_path.read_bytes()).decode(),
        'hostImage':('data:image/png;base64,'+base64.b64encode(current_billboard_bytes).decode()) if current_billboard_bytes is not None else None}
