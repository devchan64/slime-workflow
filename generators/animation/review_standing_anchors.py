"""4방향 스탠딩의 양발 접지 중간점 추정과 브라우저 검수 자료를 만든다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import math
import shutil
import traceback
from PIL import Image, ImageDraw

STANDING_DIRECTION_NAMES = ('down_left', 'down_right', 'up_left', 'up_right')
STANDING_FRAME_COUNT = 4
STANDING_FRAME_DURATION = 400
SHOE_REGION_HEIGHT_RATIO = 0.77
SHOE_ALPHA_THRESHOLD = 160
SHOE_MINIMUM_BRIGHTNESS = 95
SHOE_MAXIMUM_COLOR_SPREAD = 48
SHOE_COMPONENT_MINIMUM = 150
SHOE_ENDPOINT_INSET_RATIO = 0.12

def calculate_contact_midpoint(screen_left_contact, screen_right_contact):
    return {coordinate_axis_name: math.floor((screen_left_contact[coordinate_axis_name] + screen_right_contact[coordinate_axis_name]) / 2 + 0.5) for coordinate_axis_name in ('x', 'y')}

def detect_shoe_endpoints(source_frame_image, direction_identifier_text):
    """하단의 밝은 무채색 신발 연결 영역 두 개를 찾는다. 화면 좌우 순서다."""
    source_frame_width, source_frame_height = source_frame_image.size
    pixel_access_data = source_frame_image.load()
    shoe_region_top = int(source_frame_height * SHOE_REGION_HEIGHT_RATIO)
    remaining_shoe_pixels = set()
    for pixel_position_y in range(shoe_region_top, source_frame_height):
        for pixel_position_x in range(source_frame_width):
            pixel_color_value = pixel_access_data[pixel_position_x, pixel_position_y]
            if pixel_color_value[3] >= SHOE_ALPHA_THRESHOLD and min(pixel_color_value[:3]) >= SHOE_MINIMUM_BRIGHTNESS and max(pixel_color_value[:3]) - min(pixel_color_value[:3]) <= SHOE_MAXIMUM_COLOR_SPREAD:
                remaining_shoe_pixels.add((pixel_position_x, pixel_position_y))
    shoe_component_list = []
    while remaining_shoe_pixels:
        pending_pixel_stack = [remaining_shoe_pixels.pop()]
        connected_pixel_list = []
        while pending_pixel_stack:
            current_pixel_x, current_pixel_y = pending_pixel_stack.pop()
            connected_pixel_list.append((current_pixel_x, current_pixel_y))
            for neighbor_offset_x, neighbor_offset_y in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)):
                neighbor_pixel_pair = (current_pixel_x + neighbor_offset_x, current_pixel_y + neighbor_offset_y)
                if neighbor_pixel_pair in remaining_shoe_pixels:
                    remaining_shoe_pixels.remove(neighbor_pixel_pair)
                    pending_pixel_stack.append(neighbor_pixel_pair)
        if len(connected_pixel_list) >= SHOE_COMPONENT_MINIMUM:
            shoe_component_list.append(connected_pixel_list)
    if len(shoe_component_list) != 2:
        raise ValueError(f'신발 영역이 정확히 2개여야 합니다: {len(shoe_component_list)}. --contacts-file로 검수한 좌표를 지정하세요.')
    shoe_component_list.sort(key=lambda shoe_pixel_group: sum(pixel_position_pair[0] for pixel_position_pair in shoe_pixel_group)/len(shoe_pixel_group))
    shoe_endpoint_list = []
    for connected_pixel_list in shoe_component_list:
        sole_column_bottoms = {}
        for pixel_position_x, pixel_position_y in connected_pixel_list:
            sole_column_bottoms[pixel_position_x] = max(sole_column_bottoms.get(pixel_position_x, 0), pixel_position_y)
        sole_minimum_column, sole_maximum_column = min(sole_column_bottoms), max(sole_column_bottoms)
        endpoint_inset_width = max(1, round((sole_maximum_column-sole_minimum_column)*SHOE_ENDPOINT_INSET_RATIO))
        endpoint_left_column = sole_minimum_column+endpoint_inset_width
        endpoint_right_column = sole_maximum_column-endpoint_inset_width
        sole_left_endpoint = {'x':endpoint_left_column,'y':sole_column_bottoms[endpoint_left_column]}
        sole_right_endpoint = {'x':endpoint_right_column,'y':sole_column_bottoms[endpoint_right_column]}
        shoe_endpoint_list.extend([sole_left_endpoint,sole_right_endpoint] if direction_identifier_text.endswith('left') else [sole_right_endpoint,sole_left_endpoint])
    return shoe_endpoint_list

def load_contact_overrides(contact_source_path, coordinate_input_mode="toe-heel", contact_input_format="review", source_sheet_directory=None):
    expected_point_count = 2 if coordinate_input_mode == "foot-centers" else 4
    def reject_duplicate_keys(object_item_pairs):
        parsed_object_value = {}
        for object_field_name, object_field_value in object_item_pairs:
            if object_field_name in parsed_object_value:
                raise ValueError(f'중복 키: {object_field_name}')
            parsed_object_value[object_field_name] = object_field_value
        return parsed_object_value
    parsed_contact_data = json.loads(contact_source_path.read_text(), object_pairs_hook=reject_duplicate_keys)
    if contact_input_format == 'review':
        def require_exact_fields(current_object_value, expected_field_names):
            if not isinstance(current_object_value, dict) or set(current_object_value) != set(expected_field_names):
                raise ValueError(f'좌표 산출물 필드 오류: {expected_field_names}')
        require_exact_fields(parsed_contact_data, ('schemaVersion','artifactType','description','coordinateMode','source','frames'))
        if type(parsed_contact_data['schemaVersion']) is not int or parsed_contact_data['schemaVersion'] != 1 or parsed_contact_data['artifactType'] != 'character-standing-anchor-review' or parsed_contact_data['coordinateMode'] != coordinate_input_mode or not isinstance(parsed_contact_data['description'],str) or not parsed_contact_data['description'].strip():
            raise ValueError('좌표 산출물 버전·종류·설명·입력 모드 오류')
        source_artifact_record = parsed_contact_data['source']
        require_exact_fields(source_artifact_record, ('animationId','animationVersion','sheets'))
        if source_artifact_record['animationId'] != 'character.default.white-shirt.idle' or source_artifact_record['animationVersion'] != '4':
            raise ValueError('다른 애니메이션용 좌표입니다.')
        if not isinstance(source_artifact_record['sheets'],list) or len(source_artifact_record['sheets']) != 4:
            raise ValueError('방향별 시트 출처 4개가 필요합니다.')
        verified_sheet_directions = set()
        for source_sheet_record in source_artifact_record['sheets']:
            require_exact_fields(source_sheet_record, ('direction','image','sha256'))
            direction_identifier_text = source_sheet_record['direction']
            if direction_identifier_text not in STANDING_DIRECTION_NAMES or direction_identifier_text in verified_sheet_directions:
                raise ValueError('중복 또는 미지원 시트 방향')
            verified_sheet_directions.add(direction_identifier_text)
            expected_sheet_filename = f"standing-{direction_identifier_text.replace('_','-')}.png"
            if source_sheet_record['image'] != expected_sheet_filename or not isinstance(source_sheet_record['sha256'],str) or len(source_sheet_record['sha256']) != 64 or any(hash_character_value not in '0123456789abcdef' for hash_character_value in source_sheet_record['sha256']):
                raise ValueError('시트 이름·해시 형식 오류')
            if source_sheet_directory is not None and hashlib.sha256((source_sheet_directory/expected_sheet_filename).read_bytes()).hexdigest() != source_sheet_record['sha256']:
                raise ValueError('좌표 산출물과 입력 시트 해시가 다릅니다.')
        if not isinstance(parsed_contact_data['frames'],list) or len(parsed_contact_data['frames']) != 16:
            raise ValueError('좌표 산출물은 16프레임이어야 합니다.')
        parsed_frame_contacts = {}
        for frame_record_value in parsed_contact_data['frames']:
            require_exact_fields(frame_record_value, ('frameId','direction','image','rect','points','anchor'))
            frame_identifier_text = frame_record_value['frameId']
            if not isinstance(frame_identifier_text,str) or frame_identifier_text in parsed_frame_contacts:
                raise ValueError('잘못되거나 중복된 frameId')
            direction_identifier_text, frame_sequence_text = frame_identifier_text.rsplit('.',1)
            if direction_identifier_text not in STANDING_DIRECTION_NAMES or frame_sequence_text not in ('0','1','2','3') or frame_record_value['direction'] != direction_identifier_text or frame_record_value['image'] != f"standing-{direction_identifier_text.replace('_','-')}.png":
                raise ValueError('프레임 방향·시트 대응 오류')
            require_exact_fields(frame_record_value['rect'], ('x','y','width','height'))
            if any(type(coordinate_value_number) is not int or coordinate_value_number < 0 for coordinate_value_number in frame_record_value['rect'].values()) or min(frame_record_value['rect']['width'],frame_record_value['rect']['height']) <= 0:
                raise ValueError('정수 셀 영역이 필요합니다.')
            if source_sheet_directory is not None:
                with Image.open(source_sheet_directory/frame_record_value['image']) as actual_source_sheet:
                    expected_frame_rect = {'x':int(frame_sequence_text)*(actual_source_sheet.width//4),'y':0,'width':actual_source_sheet.width//4,'height':actual_source_sheet.height}
                if frame_record_value['rect'] != expected_frame_rect: raise ValueError('원본 셀 영역과 다른 좌표입니다.')
            frame_contact_points = frame_record_value['points']
            if not isinstance(frame_contact_points,list) or len(frame_contact_points) != expected_point_count: raise ValueError('입력 모드와 점 개수가 다릅니다.')
            for contact_point_record in frame_contact_points+[frame_record_value['anchor']]:
                require_exact_fields(contact_point_record, ('x','y'))
                if any(type(coordinate_value_number) is not int for coordinate_value_number in contact_point_record.values()) or not 0 <= contact_point_record['x'] < frame_record_value['rect']['width'] or not 0 <= contact_point_record['y'] < frame_record_value['rect']['height']:
                    raise ValueError('좌표는 셀 내부 정수여야 합니다.')
            derived_foot_centers = frame_contact_points if coordinate_input_mode == 'foot-centers' else [calculate_contact_midpoint(*frame_contact_points[:2]),calculate_contact_midpoint(*frame_contact_points[2:])]
            if frame_record_value['anchor'] != calculate_contact_midpoint(*derived_foot_centers): raise ValueError('저장 앵커와 두 발 중심 계산이 다릅니다.')
            parsed_frame_contacts[frame_identifier_text] = frame_contact_points
        parsed_contact_data = parsed_frame_contacts
    expected_frame_identifiers = {f'{direction_identifier_text}.{frame_sequence_index}' for direction_identifier_text in STANDING_DIRECTION_NAMES for frame_sequence_index in range(STANDING_FRAME_COUNT)}
    if not isinstance(parsed_contact_data, dict) or set(parsed_contact_data) != expected_frame_identifiers:
        raise ValueError('접지 좌표 파일에는 정확히 16개 frameId가 필요합니다.')
    for frame_contact_points in parsed_contact_data.values():
        if not isinstance(frame_contact_points, list) or len(frame_contact_points) != expected_point_count:
            raise ValueError(f'프레임마다 {expected_point_count}개 좌표가 필요합니다: {coordinate_input_mode}')
        for contact_point_data in frame_contact_points:
            if not isinstance(contact_point_data, dict) or set(contact_point_data) != {'x','y'} or any(type(coordinate_number_value) not in (int,float) or not math.isfinite(coordinate_number_value) for coordinate_number_value in contact_point_data.values()):
                raise ValueError('접지점은 유한한 x/y 숫자만 허용합니다.')
    return parsed_contact_data

def build_anchor_review(parsed_argument_values):
    output_review_directory = parsed_argument_values.output_dir.resolve()
    workflow_temporary_root = Path(__file__).resolve().parents[2] / ".tmp"
    if not output_review_directory.is_relative_to(workflow_temporary_root):
        raise ValueError("검수 산출물은 워크플로우 .tmp 아래에만 생성합니다.")
    output_review_directory.mkdir(parents=True, exist_ok=False)
    def emit_trace_message(trace_stage_name, trace_message_text):
        trace_output_line = f'{datetime.now().isoformat()}/standing-anchor/{trace_stage_name} {trace_message_text}'
        print(trace_output_line, flush=True)
        with (output_review_directory/'execution.log').open('a') as trace_output_stream:
            trace_output_stream.write(trace_output_line+'\n')
    try:
        emit_trace_message('start', str(parsed_argument_values.sheets_dir))
        if parsed_argument_values.coordinate_mode == 'foot-centers' and parsed_argument_values.contacts_file is None:
            raise ValueError('foot-centers 모드는 명시적인 좌표 파일이 필요합니다.')
        manual_contact_data = load_contact_overrides(parsed_argument_values.contacts_file, parsed_argument_values.coordinate_mode, parsed_argument_values.contacts_format, parsed_argument_values.sheets_dir) if parsed_argument_values.contacts_file else None
        output_frame_records, output_clip_records, output_review_records, source_sheet_records, body_height_values = [], [], [], [], []
        common_sheet_dimensions = None
        for direction_identifier_text in STANDING_DIRECTION_NAMES:
            source_sheet_path = parsed_argument_values.sheets_dir / f"standing-{direction_identifier_text.replace('_','-')}.png"
            with Image.open(source_sheet_path) as source_sheet_image:
                if source_sheet_image.mode != 'RGBA' or source_sheet_image.width % STANDING_FRAME_COUNT:
                    raise ValueError('RGBA PNG와 4로 나누어지는 너비가 필요합니다.')
                if common_sheet_dimensions is not None and source_sheet_image.size != common_sheet_dimensions:
                    raise ValueError('네 시트의 크기가 같아야 합니다.')
                common_sheet_dimensions = source_sheet_image.size
                source_frame_width = source_sheet_image.width // STANDING_FRAME_COUNT
                source_frame_height = source_sheet_image.height
                shutil.copy2(source_sheet_path, output_review_directory/source_sheet_path.name)
                source_sheet_records.append({'direction':direction_identifier_text,'image':source_sheet_path.name,'sha256':hashlib.sha256(source_sheet_path.read_bytes()).hexdigest()})
                direction_clip_frames = []
                for frame_sequence_index in range(STANDING_FRAME_COUNT):
                    current_frame_identifier = f'{direction_identifier_text}.{frame_sequence_index}'
                    current_frame_rectangle = {'x':frame_sequence_index*source_frame_width,'y':0,'width':source_frame_width,'height':source_frame_height}
                    current_frame_image = source_sheet_image.crop((current_frame_rectangle['x'],0,current_frame_rectangle['x']+source_frame_width,source_frame_height))
                    if parsed_argument_values.coordinate_mode == 'foot-centers':
                        foot_endpoint_points = []
                        foot_contact_points = manual_contact_data[current_frame_identifier]
                    else:
                        foot_endpoint_points = manual_contact_data[current_frame_identifier] if manual_contact_data else detect_shoe_endpoints(current_frame_image, direction_identifier_text)
                        foot_contact_points = [calculate_contact_midpoint(*foot_endpoint_points[:2]),calculate_contact_midpoint(*foot_endpoint_points[2:])]
                    foot_endpoint_points = [{coordinate_axis_name:math.floor(contact_point_data[coordinate_axis_name]+0.5) for coordinate_axis_name in ('x','y')} for contact_point_data in foot_endpoint_points]
                    foot_contact_points = ([{coordinate_axis_name:math.floor(contact_point_data[coordinate_axis_name]+0.5) for coordinate_axis_name in ('x','y')} for contact_point_data in foot_contact_points] if parsed_argument_values.coordinate_mode == 'foot-centers' else [calculate_contact_midpoint(*foot_endpoint_points[:2]),calculate_contact_midpoint(*foot_endpoint_points[2:])])
                    if any(not 0 <= contact_point_data['x'] < source_frame_width or not 0 <= contact_point_data['y'] < source_frame_height for contact_point_data in foot_endpoint_points+foot_contact_points):
                        raise ValueError(f'셀 밖 접지점: {current_frame_identifier}')
                    current_frame_anchor = calculate_contact_midpoint(*foot_contact_points)
                    output_frame_records.append({'frameId':current_frame_identifier,'rect':current_frame_rectangle,'anchor':current_frame_anchor})
                    direction_clip_frames.append({'frameId':current_frame_identifier,'durationMs':STANDING_FRAME_DURATION})
                    output_review_records.append({'frameId':current_frame_identifier,'direction':direction_identifier_text,'image':source_sheet_path.name,'rect':current_frame_rectangle,'contacts':foot_contact_points,'endpoints':foot_endpoint_points,'anchor':current_frame_anchor})
                    body_alpha_bounds = current_frame_image.getchannel('A').point(lambda alpha_channel_value:255 if alpha_channel_value >= SHOE_ALPHA_THRESHOLD else 0).getbbox()
                    if body_alpha_bounds is None: raise ValueError('빈 프레임입니다.')
                    body_height_values.append(body_alpha_bounds[3]-body_alpha_bounds[1])
                    emit_trace_message('frame', f'{current_frame_identifier} contacts={foot_contact_points} anchor={current_frame_anchor}')
                output_clip_records.append({'clipId':f'idle.{direction_identifier_text}','action':'idle','direction':direction_identifier_text,'frames':direction_clip_frames,'loop':True,'nextClipId':None})
        reference_body_height = round(sum(body_height_values)/len(body_height_values),3)
        animation_metadata_data = {'animationId':'character.default.white-shirt.idle','version':'4','sheet':{'width':common_sheet_dimensions[0],'height':common_sheet_dimensions[1]},'frames':output_frame_records,'clips':output_clip_records}
        (output_review_directory/'idle-v4.animation.json').write_text(json.dumps(animation_metadata_data,ensure_ascii=False,indent=2)+'\n')
        source_manifest_data = {'version':4,'sheets':source_sheet_records,'referenceBodyHeight':reference_body_height,'anchorMethod':('mean-of-user-foot-centers' if parsed_argument_values.coordinate_mode == 'foot-centers' else 'mean-of-two-toe-heel-midpoints'),'contacts':{current_frame_record['frameId']:current_frame_record['contacts'] for current_frame_record in output_review_records},'footprintEndpoints':{current_frame_record['frameId']:current_frame_record['endpoints'] for current_frame_record in output_review_records},'coordinateMode':parsed_argument_values.coordinate_mode,'endpointMethod':('not-supplied' if parsed_argument_values.coordinate_mode == 'foot-centers' else 'lower-contour-12-percent-inset-estimate-requires-visual-review'),'source':str(parsed_argument_values.sheets_dir.resolve()),'bodyHeightRange':[min(body_height_values),max(body_height_values)]}
        (output_review_directory/'source.json').write_text(json.dumps(source_manifest_data,ensure_ascii=False,indent=2)+'\n')
        (output_review_directory/'contacts.json').write_text(json.dumps(source_manifest_data['contacts'] if parsed_argument_values.coordinate_mode == 'foot-centers' else source_manifest_data['footprintEndpoints'],ensure_ascii=False,indent=2)+'\n')
        coordinate_artifact_data = {'schemaVersion':1,'artifactType':'character-standing-anchor-review','description':'기본 캐릭터 standing-v4 방향별 4프레임 시트 4장의 정수 앵커 검수 좌표. 셀 왼쪽 위 원점, x는 오른쪽, y는 아래. points는 '+('화면 왼쪽·오른쪽 발 중심' if parsed_argument_values.coordinate_mode == 'foot-centers' else '화면 왼쪽 발 앞꿈치·뒤꿈치, 오른쪽 발 앞꿈치·뒤꿈치')+'이다. anchor는 두 발 중심 평균을 반올림하며 프레임별로 독립적이다.','coordinateMode':parsed_argument_values.coordinate_mode,'source':{'animationId':animation_metadata_data['animationId'],'animationVersion':animation_metadata_data['version'],'sheets':source_sheet_records},'frames':[{'frameId':frame_record_value['frameId'],'direction':frame_record_value['direction'],'image':frame_record_value['image'],'rect':frame_record_value['rect'],'points':frame_record_value['contacts'] if parsed_argument_values.coordinate_mode == 'foot-centers' else frame_record_value['endpoints'],'anchor':frame_record_value['anchor']} for frame_record_value in output_review_records]}
        (output_review_directory/'character-default-standing-v4-anchor-review.json').write_text(json.dumps(coordinate_artifact_data,ensure_ascii=False,indent=2)+'\n')
        html_template_path = Path(__file__).with_suffix('.html')
        review_page_text = html_template_path.read_text().replace('__FRAME_RECORDS__',json.dumps(output_review_records,ensure_ascii=False)).replace('__SOURCE_METADATA__',json.dumps(source_manifest_data,ensure_ascii=False))
        (output_review_directory/'preview.html').write_text(review_page_text)
        # 육안 검수용: 네 방향 첫 프레임을 같은 스케일과 공통 앵커에 표시한다.
        overview_image_canvas = Image.new('RGB',(1200,760),'#29313f')
        overview_draw_context = ImageDraw.Draw(overview_image_canvas)
        for direction_sequence_index in range(4):
            selected_frame_record = output_review_records[direction_sequence_index*4]
            with Image.open(output_review_directory/selected_frame_record['image']) as source_sheet_image:
                selected_frame_image = source_sheet_image.crop((0,0,source_frame_width,source_frame_height))
                selected_frame_image.thumbnail((280,650))
                frame_display_scale = selected_frame_image.height/source_frame_height
                target_anchor_position = (150+direction_sequence_index*300,690)
                sprite_canvas_position = (round(target_anchor_position[0]-selected_frame_record['anchor']['x']*frame_display_scale),round(target_anchor_position[1]-selected_frame_record['anchor']['y']*frame_display_scale))
                overview_image_canvas.paste(selected_frame_image,sprite_canvas_position,selected_frame_image)
                contact_canvas_points = [(sprite_canvas_position[0]+contact_point_data['x']*frame_display_scale,sprite_canvas_position[1]+contact_point_data['y']*frame_display_scale) for contact_point_data in selected_frame_record['contacts']]
                overview_draw_context.line(contact_canvas_points,fill='#00ffff',width=2)
                for endpoint_pair_offset in range(0,len(selected_frame_record['endpoints']),2):
                    endpoint_canvas_points = [(sprite_canvas_position[0]+endpoint_value['x']*frame_display_scale,sprite_canvas_position[1]+endpoint_value['y']*frame_display_scale) for endpoint_value in selected_frame_record['endpoints'][endpoint_pair_offset:endpoint_pair_offset+2]]
                    overview_draw_context.line(endpoint_canvas_points,fill='#ffdf66',width=2)
                for contact_canvas_x,contact_canvas_y in contact_canvas_points:
                    overview_draw_context.ellipse((contact_canvas_x-4,contact_canvas_y-4,contact_canvas_x+4,contact_canvas_y+4),fill='#00ffff')
                overview_draw_context.ellipse((target_anchor_position[0]-4,686,target_anchor_position[0]+4,694),fill='#ff4444')
                overview_draw_context.text((direction_sequence_index*300+25,15),selected_frame_record['direction'],fill='white')
        overview_image_canvas.save(output_review_directory/'anchor-overview.png')
        emit_trace_message('complete', f'{output_review_directory}/preview.html bodyHeight={reference_body_height}')
    except Exception:
        emit_trace_message('failure',traceback.format_exc())
        print('\n'.join((output_review_directory/'execution.log').read_text().splitlines()[-20:]),flush=True)
        raise

if __name__ == '__main__':
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--sheets-dir',type=Path,required=True)
    argument_value_parser.add_argument('--contacts-file',type=Path)
    argument_value_parser.add_argument('--contacts-format',choices=('review','legacy'),default='review')
    argument_value_parser.add_argument('--coordinate-mode',choices=('toe-heel','foot-centers'),default='toe-heel')
    argument_value_parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[2]/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S'))
    build_anchor_review(argument_value_parser.parse_args())
