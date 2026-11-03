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
        if set(current_property_values)!={'anchorX','anchorY'}:continue
        current_image_path,_=resolve_registered_asset(current_path,current_asset_root,current_registry_records,'assets/buildings')
        current_catalog_rows.append({'texture':current_identifier,'image':str(current_image_path),'properties':current_property_values,'maps':current_usage_records.get(current_identifier,[]),'width':current_registry_record['width'],'height':current_registry_record['height']})
    return {'generation':current_generation_number,'assets':current_catalog_rows}


def save_building_editor_anchor(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'texture','generation','expected','properties'}:raise ValueError('건물 ID·세대·기존 앵커·새 앵커가 필요합니다.')
    current_identifier=current_request_payload['texture']
    if not isinstance(current_identifier,str) or not re.fullmatch(r'town-[a-z0-9-]+-v[1-9][0-9]*',current_identifier):raise ValueError('건물 ID 오류')
    for current_name in ('expected','properties'):
        current_value=current_request_payload[current_name]
        if not isinstance(current_value,dict) or set(current_value)!={'anchorX','anchorY'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=16 for v in current_value.values()):raise ValueError('앵커는 0~16 범위여야 합니다.')
    if type(current_request_payload['generation']) is not int:raise ValueError('세대 오류')
    return execute_content_api_request('POST','/internal/v1/content/buildings/'+quote(current_identifier,safe='')+'/anchor',{'requestId':'building-anchor-'+uuid4().hex,'expectedGeneration':current_request_payload['generation'],'expected':current_request_payload['expected'],'properties':current_request_payload['properties']})
