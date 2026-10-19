"""등록 원본에서 월드맵 읽기 전용 검수 계약을 구성한다."""
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset, UniqueAssetYamlLoader
from tools.review.common.map_asset_sources import read_registered_map_data, load_review_map_identifiers

WORLD_MAP_DIRECTION_OFFSETS = {'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}
WORLD_MAP_REVERSE_DIRECTIONS = {'north':'south','south':'north','west':'east','east':'west'}
WORLD_THUMBNAIL_CATALOG_PATH = 'assets/ui/world-map/thumbnails.yaml'


def load_world_review_catalog():
    current_source_catalog = load_registered_tiles()
    current_assets_root,current_asset_records = current_source_catalog
    current_provenance_records = []
    current_city_identifiers,current_map_identifiers = load_review_map_identifiers(current_source_catalog)
    current_display_document = read_registered_map_data('world-map.yaml',current_provenance_records,current_source_catalog)
    if set(current_display_document)!={'version','maps'} or type(current_display_document['version']) is not int or current_display_document['version']!=1 or not isinstance(current_display_document['maps'],dict) or set(current_display_document['maps'])!=set(current_map_identifiers):
        raise ValueError('월드맵 표시 원본과 실제 맵 목록이 다릅니다.')
    current_thumbnail_path,current_thumbnail_provenance = resolve_registered_asset(WORLD_THUMBNAIL_CATALOG_PATH,current_assets_root,current_asset_records,'assets/ui/world-map')
    current_thumbnail_document = yaml.load(current_thumbnail_path.read_text(),Loader=UniqueAssetYamlLoader)
    if not isinstance(current_thumbnail_document,dict) or set(current_thumbnail_document)!={'schema_version','maps'} or type(current_thumbnail_document['schema_version']) is not int or current_thumbnail_document['schema_version']!=1 or not isinstance(current_thumbnail_document['maps'],dict) or set(current_thumbnail_document['maps'])!=set(current_map_identifiers):
        raise ValueError('썸네일 목록과 실제 맵 목록이 다릅니다.')
    current_provenance_records.append(current_thumbnail_provenance)
    current_world_nodes = []
    current_occupied_positions = set()
    for current_map_identifier in current_map_identifiers:
        current_display_node = current_display_document['maps'][current_map_identifier]
        if not isinstance(current_display_node,dict) or set(current_display_node)!={'column','row','thumbnailId'} or any(type(current_display_node[current_axis_name]) is not int for current_axis_name in ('column','row')) or current_display_node['thumbnailId']!='image.ui.world-map.'+current_map_identifier:
            raise ValueError('월드맵 표시 항목 형식 오류: '+current_map_identifier)
        current_map_position = (current_display_node['column'],current_display_node['row'])
        if current_map_position in current_occupied_positions: raise ValueError('월드맵 표시 좌표가 중복됩니다.')
        current_occupied_positions.add(current_map_position)
        current_thumbnail_record = current_thumbnail_document['maps'][current_map_identifier]
        if not isinstance(current_thumbnail_record,dict) or set(current_thumbnail_record)!={'managementId','version','path','sha256','width','height'} or current_thumbnail_record['managementId']!=current_display_node['thumbnailId'] or type(current_thumbnail_record['width']) is not int or type(current_thumbnail_record['height']) is not int or current_thumbnail_record['width']!=256 or current_thumbnail_record['height']!=256:
            raise ValueError('월드맵 썸네일 항목 오류: '+current_map_identifier)
        current_image_path,current_image_provenance = resolve_registered_asset(current_thumbnail_record['path'],current_assets_root,current_asset_records,'assets/ui/world-map/thumbnails')
        if current_image_path.suffix!='.png' or any(current_thumbnail_record[current_field_name]!=current_image_provenance[current_field_name] for current_field_name in ('managementId','version','sha256')):
            raise ValueError('월드맵 썸네일 등록 계약 불일치: '+current_map_identifier)
        current_provenance_records.append(current_image_provenance)
        current_name_record = read_registered_map_data('map_names/'+current_map_identifier+'.yaml',current_provenance_records,current_source_catalog)
        if set(current_name_record)!={'ko','en'} or any(not isinstance(current_name_value,str) or not current_name_value.strip() for current_name_value in current_name_record.values()):
            raise ValueError('월드맵 이름 형식 오류')
        current_safe_town = current_map_identifier in current_city_identifiers
        current_connection_source = read_registered_map_data(('city_layouts/' if current_safe_town else 'field_waypoints/')+current_map_identifier+'.yaml',current_provenance_records,current_source_catalog)
        current_world_nodes.append(dict(id=current_map_identifier,name=current_name_record['ko'],nameTranslations=current_name_record,safeTown=current_safe_town,
            **current_display_node,connections=[{current_field_name:current_link_record[current_field_name] for current_field_name in ('id','target','direction')} | ({'targetWaypointId':current_link_record['targetWaypointId']} if 'targetWaypointId' in current_link_record else {}) for current_link_record in current_connection_source['connections']],
            thumbnail=dict(current_thumbnail_record,url='/management/map-assets/thumbnails/'+current_image_path.name+'?v='+current_thumbnail_record['sha256'])))
    current_world_lookup = {current_world_node['id']:current_world_node for current_world_node in current_world_nodes}
    for current_world_node in current_world_nodes:
        current_seen_targets = set()
        current_seen_waypoints = set()
        for current_world_link in current_world_node['connections']:
            if current_world_link['target'] not in current_world_lookup or current_world_link['direction'] not in WORLD_MAP_DIRECTION_OFFSETS or current_world_link['target'] in current_seen_targets or current_world_link['id'] in current_seen_waypoints:
                raise ValueError('월드맵 연결 대상·방향·중복 오류')
            current_seen_targets.add(current_world_link['target']);current_seen_waypoints.add(current_world_link['id'])
            current_target_node = current_world_lookup[current_world_link['target']]
            current_reverse_links = [current_reverse_link for current_reverse_link in current_target_node['connections'] if current_reverse_link['target']==current_world_node['id'] and current_reverse_link['direction']==WORLD_MAP_REVERSE_DIRECTIONS[current_world_link['direction']]]
            if len(current_reverse_links)!=1: raise ValueError('월드맵 상대 웨이포인트 누락·중복')
            if 'targetWaypointId' in current_world_link and current_world_link['targetWaypointId']!=current_reverse_links[0]['id']: raise ValueError('월드맵 상대 웨이포인트 불일치')
            current_world_link['targetWaypointId'] = current_reverse_links[0]['id']
            current_coordinate_delta = (current_target_node['column']-current_world_node['column'],current_target_node['row']-current_world_node['row'])
            if tuple((current_axis_value>0)-(current_axis_value<0) for current_axis_value in current_coordinate_delta)!=WORLD_MAP_DIRECTION_OFFSETS[current_world_link['direction']]: raise ValueError('월드맵 표시 좌표와 이동 방향이 다릅니다.')
    current_reachable_maps = {current_world_nodes[0]['id']};current_pending_maps = list(current_reachable_maps)
    for current_map_identifier in current_pending_maps:
        for current_world_link in current_world_lookup[current_map_identifier]['connections']:
            if current_world_link['target'] not in current_reachable_maps:
                current_reachable_maps.add(current_world_link['target']);current_pending_maps.append(current_world_link['target'])
    if current_reachable_maps!=set(current_world_lookup): raise ValueError('월드맵에 고립된 맵이 있습니다.')
    return dict(version=3,maps=current_world_nodes,provenance=current_provenance_records)
