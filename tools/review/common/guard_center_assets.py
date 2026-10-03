"""게임과 같은 경비센터 표시 설정·등록 이미지를 검수 화면에 연결한다."""
import math
import yaml
from tools.review.common.map_tile_assets import resolve_registered_asset, UniqueAssetYamlLoader


def load_guard_center_visuals(current_source_catalog):
    current_asset_root, current_asset_records = current_source_catalog
    current_catalog_path, current_catalog_provenance = resolve_registered_asset('assets/ui/guard-centers.yaml',current_asset_root,current_asset_records,'assets/ui')
    current_catalog_record = yaml.load(current_catalog_path.read_text(),Loader=UniqueAssetYamlLoader)
    if not isinstance(current_catalog_record,dict) or set(current_catalog_record)!={'schema_version','cities','styles'} or type(current_catalog_record['schema_version']) is not int or current_catalog_record['schema_version']!=1:
        raise ValueError('경비센터 카탈로그 형식 오류')
    if not isinstance(current_catalog_record['cities'],dict) or not current_catalog_record['cities'] or not isinstance(current_catalog_record['styles'],dict) or set(current_catalog_record['styles'])!={'wood','red-tile','teal'}:
        raise ValueError('경비센터 외형 목록 오류')
    for current_style_name,current_style_record in current_catalog_record['styles'].items():
        if not isinstance(current_style_record,dict) or set(current_style_record)!={'path','anchorX','anchorY','displayWidth','offsetX','offsetY'} or current_style_record['path']!=f'assets/sprites/structures/guard-center-{current_style_name}-v1.png':
            raise ValueError('경비센터 외형 필드 오류')
        for current_numeric_field in ('anchorX','anchorY','displayWidth','offsetX','offsetY'):
            if type(current_style_record[current_numeric_field]) not in (int,float) or not math.isfinite(current_style_record[current_numeric_field]):
                raise ValueError('경비센터 표시 수치 오류')
        if current_style_record['displayWidth']<=0 or not 0<=current_style_record['anchorX']<=1 or not 0<=current_style_record['anchorY']<=1:
            raise ValueError('경비센터 표시 범위 오류')
        _,current_image_provenance=resolve_registered_asset(current_style_record['path'],current_asset_root,current_asset_records,'assets/sprites/structures')
        current_style_record['provenance']=current_image_provenance
        current_style_record['image']='/management/map-assets/structures/'+current_style_record['path'].rsplit('/',1)[-1]
    for current_city_name,current_style_name in current_catalog_record['cities'].items():
        if not isinstance(current_city_name,str) or not isinstance(current_style_name,str) or current_style_name not in current_catalog_record['styles']:
            raise ValueError('경비센터 도시 외형 오류')
    return current_catalog_record,current_catalog_provenance
