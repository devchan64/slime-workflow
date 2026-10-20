"""빌보드 제작 참고 카탈로그를 공용 속성·등록부·실제 맵 참조와 동기화한다."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
from pathlib import Path
import re
import yaml

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
DEFAULT_ASSET_DIRECTORY = WORKFLOW_ROOT_DIRECTORY.parent / 'slime-assets'
MODELING_ROLE_RULES = (
    (r'waypost|waystone|waymark|boundary-stone|waypoint', '길 안내 지표', '갈림길·출입구 옆에 단독 배치하고 이동 칸과 표지 가독성을 확보한다.'),
    (r'cargo|crate|barrel|bucket|bundle|rope-coil', '운반·보관 소품', '운반로 옆 작업 구역에 소량 묶어 배치하고 통로를 비운다.'),
    (r'winch|tools|workbench|millstone|rack|counter|workshop|dispatch|weighing', '작업 흔적', '해당 작업 장소의 중심 소품으로 사용하며 같은 기능을 과도하게 반복하지 않는다.'),
    (r'snag|dead-tree|deadwood|snapped|charred|split-stump', '고사목·산불 및 쇠퇴 흔적', '노출 지면·숲 경계에 불규칙하게 배치하고 어린 식생과 대비시킨다.'),
    (r'log|stump|root-knot|dry-branch', '숲 바닥 잔해', '수목 아래·군락 가장자리에 배치하고 방향·형태 변형을 섞는다.'),
    (r'tree', '수목 군락', '크기가 다른 수목을 섞어 군락과 빈터를 만들고 출입구·시작 지점을 비운다.'),
    (r'rock|stone|quartz|basalt|granite|slab|scree|rubble|boulder|pebble|chips|outcrop|spires|shelf', '암석·지질 지표', '지면 재질과 어울리는 암석 군락에 사용하며 큰 덩어리 주변에 작은 파편을 배치한다.'),
    (r'grass|sedge|reed|shoot|fern|clover|sapling|grain|wheat', '낮은 식생·회복 식생', '토양 경계·수목 사이에 크기와 밀도를 달리해 군락으로 배치한다.'),
    (r'flower|daisy|iris|lavender|dandelion', '꽃·색채 강조', '식생 군락의 일부에 제한적으로 섞어 색채가 균일하게 반복되지 않도록 한다.'),
    (r'mushroom|fungus', '분해·그늘 식생', '그늘·고목 주변에 작은 무리로 배치한다.'),
    (r'bush|shrub|hedge|bramble', '관목·경계 식생', '나무와 낮은 풀 사이를 연결하며 주요 이동 동선을 가리지 않는다.'),
)


def load_unique_yaml_document(current_source_path):
    class UniqueKeyLoader(yaml.SafeLoader):
        pass
    def construct_unique_mapping(current_yaml_loader, current_yaml_node, current_deep_flag=False):
        current_result_mapping = {}
        for current_key_node, current_value_node in current_yaml_node.value:
            current_key_value = current_yaml_loader.construct_object(current_key_node, deep=current_deep_flag)
            if current_key_value in current_result_mapping:
                raise ValueError(f'중복 YAML 키: {current_source_path}: {current_key_value}')
            current_result_mapping[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=current_deep_flag)
        return current_result_mapping
    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)
    return yaml.load(current_source_path.read_text(), Loader=UniqueKeyLoader)


def build_modeling_guidance(current_texture_key, current_family_record):
    current_role_name = current_family_record['category']
    current_placement_advice = '등록된 용도에 맞는 장소를 선택하고 주변 오브젝트와 간격을 조정한다.'
    for current_match_pattern, current_rule_role, current_rule_advice in MODELING_ROLE_RULES:
        if re.search(current_match_pattern, current_texture_key):
            current_role_name, current_placement_advice = current_rule_role, current_rule_advice
            break
    current_family_uses = [current_usage_text for current_usage_text in current_family_record['uses'] if current_usage_text != '야외 필드 배경 배치 후보']
    return {
        'purpose': current_family_record['name']+' · '+current_role_name,
        'recommended_uses': current_family_uses or [current_placement_advice],
        'composition': current_placement_advice,
        'avoid': ['접지 영역의 서로 다른 고도', '다른 오브젝트의 접지 점유와 중첩', '출입구·시작점·주요 이동로 점유'],
        'basis': '등록 명칭·계열에 근거한 배치 지침. 원본 외형과 지역 설정을 최종 확인한다.',
    }


def build_shadow_guidance(current_texture_key):
    """그림자 제작 지침이며 렌더러의 실행 속성과 구분한다."""
    current_contact_advice = '밑면 접촉부에 짧고 부드러운 타원 그림자를 둔다.'
    if re.search(r'grass|sedge|reed|shoot|fern|flower|grain|clover', current_texture_key):
        current_contact_advice = '줄기 군락 밑에 작고 옅은 접지 그림자를 둔다. 잎 전체를 검은 원으로 채우지 않는다.'
    elif re.search(r'log|driftwood|root-knot|branch', current_texture_key):
        current_contact_advice = '누운 몸통과 뿌리가 닿는 방향으로 낮고 긴 접지 그림자가 어울린다. 열·행 점유 수가 다르면 둥근 직사각형을 해당 지면 축으로 투영한다.'
    elif re.search(r'tree|snag|deadwood', current_texture_key):
        current_contact_advice = '줄기·밑동에 접지 그림자를 둔다. 수관 크기의 검은 원이나 긴 투사 그림자를 접지 그림자로 대신하지 않는다.'
    elif re.search(r'rock|stone|boulder|stump|crate|barrel', current_texture_key):
        current_contact_advice = '단단한 밑면 아래 중심은 조금 진하고 가장자리는 부드럽게 표현한다.'
    return {
        'runtime_profile': 'billboard-contact-v2',
        'current_rendering': '공용 렌더러 3겹 접지 그림자. 정사각 점유는 타원, 열·행 수가 다른 점유는 점유 축을 따르는 둥근 직사각형. 공용 속성 shadowOffsetColumn/Row와 shadowScaleX/Y로 위치·크기를 조절한다. 농도 수동 조절은 미지원.',
        'contact_guidance': current_contact_advice,
        'baked_shadow_review': '원본에 진한 그림자·지면 받침이 있으면 중복 음영을 확인한다. 원본별 그림자 포함 여부는 이미지 검수로 확정한다.',
        'placement_review': '타일 고도·상하 앵커·회전에 맞는 접지 위치를 확인하고 절벽 밖이나 다른 오브젝트 위로 그림자가 번지지 않게 검수한다.',
        'guidance_only': True,
    }


def build_catalog_reference(current_asset_root):
    from tools.review.common.sprite_display_properties import validate_sprite_display_properties
    current_catalog_path = current_asset_root/'assets/billboards/catalog.yaml'
    current_catalog_record = load_unique_yaml_document(current_catalog_path)
    current_registry_record = load_unique_yaml_document(current_asset_root/'asset-registry.yaml')
    current_property_path = current_asset_root/'assets/maps/sprite-display-properties.yaml'
    current_property_catalog = load_unique_yaml_document(current_property_path)['data']
    validate_sprite_display_properties(current_property_catalog)
    current_registry_lookup = {}
    for current_asset_record in current_registry_record['assets']:
        current_asset_identity = (current_asset_record['managementId'], current_asset_record['version'])
        if current_asset_identity in current_registry_lookup:
            raise ValueError('등록부 ID·버전 중복: '+str(current_asset_identity))
        current_registry_lookup[current_asset_identity] = current_asset_record
    current_metric_path = WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map/vendor/field-renderer/game-render-profile.mjs'
    # 설치된 공용 렌더러가 공개하는 상수를 그대로 사용한다.
    current_metric_text = current_metric_path.read_text()
    current_scale_matches = re.findall(r'(?:const|var) OUTDOOR_MAP_RENDER_SCALE = ([0-9.]+)',current_metric_text)
    if len(current_scale_matches)!=1:
        raise ValueError('공용 렌더러 야외필드 배율 상수 누락·중복')
    current_outdoor_scale = float(current_scale_matches[0])
    current_map_references = {}
    for current_map_path in sorted((current_asset_root/'assets/maps').rglob('*.yaml')):
        if current_map_path == current_property_path:
            continue
        current_reference_counts = Counter(re.findall(r'^\s*textureKey:\s*([a-z0-9-]+)\s*$',current_map_path.read_text(),re.M))
        for current_texture_key, current_reference_count in current_reference_counts.items():
            current_map_references.setdefault(current_texture_key, []).append({'path':str(current_map_path.relative_to(current_asset_root)), 'texture_key_occurrences':current_reference_count})
    current_seen_textures = set()
    for current_billboard_record in current_catalog_record['billboards']:
        current_allowed_fields={'texture_key','family','asset_ref','map_references','source_file','modeling','placement','variant_features','metadata_references','related_texture_keys'}
        current_required_fields={'texture_key','family','asset_ref','map_references'}
        if set(current_billboard_record)-current_allowed_fields or not current_required_fields<=set(current_billboard_record):
            raise ValueError('빌보드 카탈로그 필드 누락·알 수 없는 필드: '+str(current_billboard_record.get('texture_key')))
        if set(current_billboard_record['asset_ref'])!={'management_id','version'}:
            raise ValueError('빌보드 등록 참조 필드 오류')
        current_texture_key = current_billboard_record['texture_key']
        if current_texture_key in current_seen_textures:
            raise ValueError('카탈로그 텍스처 중복: '+current_texture_key)
        current_seen_textures.add(current_texture_key)
        current_asset_reference = current_billboard_record['asset_ref']
        current_asset_record = current_registry_lookup[(current_asset_reference['management_id'],current_asset_reference['version'])]
        current_image_path = current_asset_root/current_asset_record['path']
        if not current_image_path.is_file() or hashlib.sha256(current_image_path.read_bytes()).hexdigest()!=current_asset_record['sha256']:
            raise ValueError('빌보드 원본 누락·해시 불일치: '+str(current_image_path))
        current_billboard_record['source_file'] = {current_field_name:current_asset_record[current_field_name] for current_field_name in ('path','width','height','sha256')}
        current_family_record = current_catalog_record['families'][current_billboard_record['family']]
        current_billboard_record.setdefault('modeling',build_modeling_guidance(current_texture_key,current_family_record))
        current_billboard_record['modeling'].setdefault('shadow',build_shadow_guidance(current_texture_key))
        if current_billboard_record['modeling']['shadow'].get('runtime_profile')=='billboard-contact-v1':
            current_billboard_record['modeling']['shadow'].update(build_shadow_guidance(current_texture_key))
        current_shared_properties = current_property_catalog.get(current_texture_key)
        if current_shared_properties is None or 'displayHeight' not in current_shared_properties:
            current_billboard_record['placement'] = {'status':'설정 필요','reason':'공용 배치 속성 없음. 구버전·애니메이션 등 별도 계약을 확인하고 기본값 등록 후 사용한다.'}
        else:
            current_billboard_record['placement'] = {
                'status':'공용 속성 등록됨',
                'anchor_semantics':'이미지 사각형 아랫변 중앙의 타일 좌표. (.5,.5)는 중앙. 투명 여백 포함.',
                'vertical_classification':('top' if current_shared_properties['anchorY']<.5 else 'bottom' if current_shared_properties['anchorY']>.5 else 'center'),
                'source':'assets/maps/sprite-display-properties.yaml#data.'+current_texture_key,
                **current_shared_properties,
                'outdoorDisplayHeight': current_shared_properties['displayHeight']*current_outdoor_scale,
                'size_variant':'소형 변형' if '-size-small-' in current_texture_key else '대형 변형' if '-size-large-' in current_texture_key else '기본 변형',
                'occupied_tile_count': current_shared_properties['groundFootprintColumns']*current_shared_properties['groundFootprintRows'],
                'movement':'내부 타일 통행 불가' if current_shared_properties.get('billboardBlocksMovement',False) else '통행 가능',
            }
        current_billboard_record['map_references'] = current_map_references.get(current_texture_key,[])
    current_catalog_record['modeling_contract'] = {
        'purpose':'맵 제작용 에셋 선택·크기·접지·통행 참고 자료',
        'authoritative_properties':'assets/maps/sprite-display-properties.yaml',
        'derived_fields':['source_file','placement','map_references'],
        'editable_guidance':'modeling은 수동 보강한다. 동기화는 기존 설명을 덮어쓰지 않는다.',
        'display_height':'displayHeight는 공용 기준 높이(px). PNG 해상도와 다르다.',
        'outdoor_scale':current_outdoor_scale,
        'outdoor_height':'outdoorDisplayHeight는 야외필드 배율 적용 후 높이이며 화면 줌은 포함하지 않는다.',
        'footprint':'기준 타일부터 열·행 증가 방향으로만 확장한다. 실제 점유 칸 수는 선언 열 수×행 수이며 2×1은 정확히 2칸이다.',
        'blocking':'열·행이 모두 3 이상이면 외곽 한 줄을 제외한 내부 (열-2)×(행-2) 타일만 자동 차단한다. 기준 교차점 거리는 축별 1칸=0.5, 그 외 칸수-1이다. 앵커 X·Y는 이 교차점에서 이미지 아랫변 중심까지의 수동 이동값이다.',
        'missing':'설정 필요 항목은 크기를 추측하여 배치하지 않는다.',
        'shadow': {
            'profile':'billboard-contact-v2',
            'implementation':'@slime/field-renderer 1.0.142 · drawBillboardContactShadow',
            'enabled':'기본 활성화. 렌더러 옵션 billboardShadows=false로 전체 비활성화.',
            'geometry':'폭=min(displayHeight×billboardScale×0.76, tileWidth×1.10), 높이=폭×0.2. 정사각 점유는 이 타원 공식을 사용한다. 열·행 수가 다른 점유는 각 축 길이=선언 점유 수×1.10타일, 모서리 반경=짧은 반축×0.35인 둥근 직사각형을 지면에 투영한다.',
            'layers':[{'scale':1,'alpha':0.14},{'scale':0.78,'alpha':0.20},{'scale':0.5,'alpha':0.26}],
            'color':'#18201b',
            'position':'tile-intersection의 그림자 이동 0·0은 기준 교차점이다. 수동 이미지 앵커와 독립적이다. 빌보드 앵커의 화면 이동을 제거한다: X 보정=(column-row)×tileWidth×0.5, Y 보정=(column+row)×tileHeight×0.5를 뺀다. 열·행 오프셋은 카메라 회전을 반영한다.',
            'depth':'소속 타일의 지면 바로 위에 배치하며 빌보드·캐릭터 정렬과 분리한다.',
            'limits':'접지 그림자만 지원. 광원 방향의 투사·실루엣 그림자, 에셋별 농도 설정, 지면 경계 클리핑은 지원하지 않는다.',
            'catalog_role':'modeling.shadow는 제작·검수 지침이다. 이 지침만 편집해도 런타임은 바뀌지 않는다. 위치·크기는 공용 속성 편집기에서 shadowOffsetColumn/Row(-4~4타일), shadowScaleX(0.1~4), shadowScaleY(0.05~4, 기본 1·타원 세로만 2배 보정, 긴 그림자의 행 방향은 직접 적용)를 저장한다.',
        },
        'validation':'slime-workflow/tools/review/maintenance/sync_billboard_catalog.py --check',
    }
    current_catalog_record['scope']['image_count']=len(current_seen_textures)
    return current_catalog_record


def main_catalog_sync():
    current_argument_parser=argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--asset-root',type=Path,default=DEFAULT_ASSET_DIRECTORY)
    current_mode_group=current_argument_parser.add_mutually_exclusive_group(required=True)
    current_mode_group.add_argument('--check',action='store_true')
    current_mode_group.add_argument('--write',action='store_true')
    current_argument_values=current_argument_parser.parse_args()
    current_catalog_path=current_argument_values.asset_root/'assets/billboards/catalog.yaml'
    print(f'{datetime.now().isoformat()}/billboard-catalog/start 원본·공용 속성·맵 참조 검증',flush=True)
    current_original_record=load_unique_yaml_document(current_catalog_path)
    current_expected_record=build_catalog_reference(current_argument_values.asset_root)
    if current_argument_values.write:
        current_catalog_path.write_text(yaml.safe_dump(current_expected_record,allow_unicode=True,sort_keys=False))
    elif current_original_record!=current_expected_record:
        raise ValueError('카탈로그가 공용 속성·원본·맵 배치와 다릅니다. --write로 파생 정보를 갱신하세요.')
    current_missing_count=sum(x['placement']['status']=='설정 필요' for x in current_expected_record['billboards'])
    print(f'{datetime.now().isoformat()}/billboard-catalog/complete 전체 {len(current_expected_record["billboards"])}종 · 공용 속성 미등록 {current_missing_count}종 · 검증 완료')

if __name__=='__main__':
    main_catalog_sync()
