"""건물 원본 목록과 공용 앵커를 콘텐츠 API에 연결한다."""
import math
import re
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
from tools.review.domains.map_assets.database_client import execute_content_api_request


def load_building_editor_catalog(current_request_payload):
    if current_request_payload!={}:raise ValueError('건물 목록은 입력을 받지 않습니다.')
    current_initial_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle')
    current_generation_number=current_initial_bundle['generation']
    current_properties=current_initial_bundle['documents']['sprite-display-properties.yaml']['data']
    current_city_identifiers=current_initial_bundle['documents']['city_layouts/index.yaml']['data']['includes']['layouts']
    current_usage_records={}
    for current_city_identifier in current_city_identifiers:
        current_city_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle?map='+quote(current_city_identifier,safe=''))
        if current_city_bundle['generation']!=current_generation_number:raise ValueError('조회 중 콘텐츠가 변경되었습니다. 다시 불러오세요.')
        current_map_document=current_city_bundle['documents']['city_layouts/'+current_city_identifier+'.yaml']['data']
        for current_building_record in current_map_document['buildings']:
            current_identifier=current_building_record['sprite']['textureKey']
            current_usage_records.setdefault(current_identifier,[]).append({'map':current_city_identifier,'name':current_building_record['name'],'width':current_building_record['width'],'height':current_building_record['height'],'facing':current_building_record['facing'],'contentWidth':current_building_record['sprite']['contentWidth']})
    current_asset_root,current_registry_records=load_registered_tiles()
    current_catalog_rows=[]
    for current_path,current_registry_record in sorted(current_registry_records.items()):
        if not re.fullmatch(r'assets/buildings/town-[a-z0-9-]+-v[1-9][0-9]*\.png',current_path):continue
        current_identifier=Path(current_path).stem
        if current_identifier not in current_properties:continue
        current_property_values=current_properties[current_identifier]
        if set(current_property_values) not in ({'anchorX','anchorY'}, {'anchorX','anchorY','displayWidthAdjustment','displayHeightAdjustment'}):continue
        current_image_path,_=resolve_registered_asset(current_path,current_asset_root,current_registry_records,'assets/buildings')
        current_catalog_rows.append({'texture':current_identifier,'image':str(current_image_path),'properties':current_property_values,'maps':current_usage_records.get(current_identifier,[]),'width':current_registry_record['width'],'height':current_registry_record['height']})
    return {'generation':current_generation_number,'assets':current_catalog_rows}


def save_building_editor_anchor(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'texture','generation','expected','properties'}:raise ValueError('건물 ID·세대·기존 앵커·새 앵커가 필요합니다.')
    current_identifier=current_request_payload['texture']
    if not isinstance(current_identifier,str) or not re.fullmatch(r'town-[a-z0-9-]+-v[1-9][0-9]*',current_identifier):raise ValueError('건물 ID 오류')
    for current_name in ('expected','properties'):
        current_value=current_request_payload[current_name]
        if not isinstance(current_value,dict) or set(current_value) not in ({'anchorX','anchorY'}, {'anchorX','anchorY','displayWidthAdjustment','displayHeightAdjustment'}):raise ValueError('건물 공용 속성 형식 오류')
        if any(type(current_value[k]) not in (int,float) or not math.isfinite(current_value[k]) or not 0<=current_value[k]<=16 for k in ('anchorX','anchorY')):raise ValueError('앵커는 0~16 범위여야 합니다.')
        if any(type(current_value[k]) is not int or not -2048<=current_value[k]<=2048 for k in ('displayWidthAdjustment','displayHeightAdjustment') if k in current_value):raise ValueError('크기 보정은 -2048~2048 정수여야 합니다.')
    if type(current_request_payload['generation']) is not int:raise ValueError('세대 오류')
    return execute_content_api_request('POST','/internal/v1/content/buildings/'+quote(current_identifier,safe='')+'/anchor',{'requestId':'building-anchor-'+uuid4().hex,'expectedGeneration':current_request_payload['generation'],'expected':current_request_payload['expected'],'properties':current_request_payload['properties']})


def execute_building_lifecycle(current_request_payload, current_action_name):
    """원장 잠금 아래 이미지 원본과 세대 조건부 건물 속성을 반영한다."""
    import base64
    import binascii
    import fcntl
    import hashlib
    import io
    import os
    import yaml
    from PIL import Image
    from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document

    current_required_fields={'texture','generation','requestId'} | ({'imageBase64','properties'} if current_action_name=='register' else set())
    if current_action_name not in ('register','retire') or not isinstance(current_request_payload,dict) or set(current_request_payload)!=current_required_fields:
        raise ValueError('건물 명령 입력 오류')
    current_identifier=current_request_payload['texture']
    if not isinstance(current_identifier,str) or not re.fullmatch(r'town-[a-z0-9-]+-v[1-9][0-9]*',current_identifier):raise ValueError('건물 ID 오류')
    if type(current_request_payload['generation']) is not int or current_request_payload['generation']<0:raise ValueError('건물 세대 오류')
    current_request_identifier=current_request_payload['requestId']
    if not isinstance(current_request_identifier,str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,128}',current_request_identifier):raise ValueError('요청 ID 오류')
    current_asset_root,current_registry_entries=load_registered_tiles()
    current_asset_root=Path(current_asset_root).resolve(strict=True)
    current_registry_path=current_asset_root/'asset-registry.yaml'
    current_image_relative='assets/buildings/'+current_identifier+'.png'
    current_image_path=current_asset_root/current_image_relative
    if current_registry_path.is_symlink() or current_image_path.is_symlink() or not current_image_path.resolve().is_relative_to(current_asset_root/'assets/buildings'):raise ValueError('건물 원장 경로 이탈')
    current_state_directory=current_asset_root/'.local/content-ledger'
    current_state_directory.mkdir(parents=True,exist_ok=True)
    with (current_state_directory/'sync.lock').open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream,fcntl.LOCK_EX)
        current_registry_document=load_unique_yaml_document(current_registry_path)
        current_registry_matches=[current_entry for current_entry in current_registry_document['assets'] if current_entry['path']==current_image_relative]
        current_backend_payload={'requestId':current_request_identifier,'expectedGeneration':current_request_payload['generation']}
        if current_action_name=='register':
            current_property_values=current_request_payload['properties']
            if not isinstance(current_property_values,dict) or set(current_property_values)!={'anchorX','anchorY'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=16 for v in current_property_values.values()):raise ValueError('앵커는 0~16 범위여야 합니다.')
            try:current_image_bytes=base64.b64decode(current_request_payload['imageBase64'],validate=True)
            except (binascii.Error,TypeError,ValueError) as current_error:raise ValueError('PNG 입력 형식 오류') from current_error
            if not 0<len(current_image_bytes)<=16*1024*1024:raise ValueError('PNG 크기 제한 초과')
            with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
                if current_image_value.format!='PNG' or max(current_image_value.size)>512 or min(current_image_value.size)<1 or 'A' not in current_image_value.getbands():raise ValueError('512px 이하의 투명 PNG가 필요합니다.')
                current_image_value.load()
                if current_image_value.getchannel('A').getextrema()!=(0,255):raise ValueError('투명 배경과 불투명 건물이 필요합니다.')
                current_image_size=current_image_value.size
            current_image_hash=hashlib.sha256(current_image_bytes).hexdigest()
            current_new_entry={'managementId':'image.scenery.'+current_identifier,'version':current_identifier.rsplit('-',1)[-1],'path':current_image_relative,'width':current_image_size[0],'height':current_image_size[1],'sha256':current_image_hash,'source':{'repository':'user-provided','operation':'건물 관리 등록'}}
            if current_registry_matches:
                if len(current_registry_matches)!=1 or current_registry_matches[0]!=current_new_entry or not current_image_path.is_file() or hashlib.sha256(current_image_path.read_bytes()).hexdigest()!=current_image_hash:raise ValueError('이미 존재하는 건물 ID입니다.')
            else:
                if current_image_path.exists() or any(entry['managementId']==current_new_entry['managementId'] for entry in current_registry_document['assets']):raise ValueError('이미 존재하는 건물 ID입니다.')
                current_image_path.write_bytes(current_image_bytes)
                current_registry_document['assets'].append(current_new_entry)
                current_temporary_path=current_registry_path.with_suffix('.building-tmp')
                current_temporary_path.write_text(yaml.safe_dump(current_registry_document,allow_unicode=True,sort_keys=False))
                os.replace(current_temporary_path,current_registry_path)
            current_backend_payload['properties']=current_property_values
        else:
            if len(current_registry_matches)!=1:raise ValueError('건물 원장 항목을 찾을 수 없습니다.')
        try:
            current_result=execute_content_api_request('POST','/internal/v1/content/buildings/'+quote(current_identifier,safe='')+'/lifecycle/'+current_action_name,current_backend_payload)
        except Exception as current_lifecycle_error:
            if current_action_name=='register':
                raise RuntimeError('건물 이미지와 등록부가 준비되었으나 DB 등록을 확인하지 못했습니다. 같은 이미지와 ID로 다시 시도하세요: '+str(current_lifecycle_error)) from current_lifecycle_error
            raise
        if current_action_name=='retire':
            current_registry_matches[0].setdefault('source',{})['lifecycle_status']='retired'
            current_temporary_path=current_registry_path.with_suffix('.building-tmp')
            current_temporary_path.write_text(yaml.safe_dump(current_registry_document,allow_unicode=True,sort_keys=False))
            os.replace(current_temporary_path,current_registry_path)
        return current_result
