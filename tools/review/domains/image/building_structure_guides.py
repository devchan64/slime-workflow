"""고정 직교투영 건물 구조 가이드의 재현 가능한 제작."""
from pathlib import Path
import json
from datetime import datetime
from PIL import Image, ImageDraw

BUILDING_STRUCTURE_ROOT = Path(__file__).resolve().parents[4] / 'generators/image/config/building-structures'
BUILDING_STRUCTURE_CATALOG = BUILDING_STRUCTURE_ROOT / 'catalog.yaml'


def render_building_structure(current_structure_record, current_review_enabled=False):
    current_width_count = current_structure_record['width']
    current_depth_count = current_structure_record['depth']
    current_wall_height = current_structure_record['floors'] * 80
    current_roof_height = current_structure_record['roofRise']
    current_roof_type = current_structure_record['roof']
    current_face_records = []
    current_roof_faces = []
    current_roof_ridge = []
    def append_structure_face(current_world_points, current_face_color):
        current_face_records.append(([(512+40*(current_column_value-current_row_value),650+20*(current_column_value+current_row_value)-current_height_value) for current_column_value,current_row_value,current_height_value in current_world_points],current_face_color))
    # 동일한 평행이동으로 모든 규격의 바닥 원점을 유지한다.
    append_structure_face([(0,current_depth_count,0),(current_width_count,current_depth_count,0),(current_width_count,current_depth_count,current_wall_height),(0,current_depth_count,current_wall_height)],'#d9d2c3')
    append_structure_face([(current_width_count,current_depth_count,0),(current_width_count,0,0),(current_width_count,0,current_wall_height),(current_width_count,current_depth_count,current_wall_height)],'#bab5aa')
    current_door_span = current_width_count if current_structure_record['entrance']=='south' else current_depth_count
    current_door_width = current_structure_record['doorWidth']
    current_door_start = (current_door_span-current_door_width)/2
    current_door_points = [(current_door_start,0),(current_door_start+current_door_width,0),(current_door_start+current_door_width,64),(current_door_start,64)]
    append_structure_face([(current_horizontal_value,current_depth_count,current_vertical_value) if current_structure_record['entrance']=='south' else (current_width_count,current_horizontal_value,current_vertical_value) for current_horizontal_value,current_vertical_value in current_door_points],'#a66232')
    current_left_value,current_right_value=-0.1,current_width_count+0.1
    current_back_value,current_front_value=-0.1,current_depth_count+0.1
    current_top_height=current_wall_height+current_roof_height
    if current_roof_type=='gable':
        current_middle_value=current_width_count/2
        append_structure_face([(0,current_depth_count,current_wall_height),(current_width_count,current_depth_count,current_wall_height),(current_middle_value,current_depth_count,current_top_height)],'#d9d2c3')
        append_structure_face([(current_left_value,current_back_value,current_wall_height),(current_left_value,current_front_value,current_wall_height),(current_middle_value,current_front_value,current_top_height),(current_middle_value,current_back_value,current_top_height)],'#dfcba3')
        append_structure_face([(current_middle_value,current_back_value,current_top_height),(current_middle_value,current_front_value,current_top_height),(current_right_value,current_front_value,current_wall_height),(current_right_value,current_back_value,current_wall_height)],'#c5ac80')
    elif current_roof_type=='hip':
        current_middle_value=current_width_count/2
        current_ridge_back=current_width_count/2
        current_ridge_front=current_depth_count-current_width_count/2
        current_corner_points=[(current_left_value,current_back_value,current_wall_height),(current_left_value,current_front_value,current_wall_height),(current_right_value,current_front_value,current_wall_height),(current_right_value,current_back_value,current_wall_height)]
        current_ridge_points=[(current_middle_value,current_ridge_back,current_top_height),(current_middle_value,current_ridge_front,current_top_height)]
        current_roof_ridge = list(dict.fromkeys(current_ridge_points))
        for current_face_points,current_face_color in [([current_corner_points[3],current_corner_points[0],current_ridge_points[0]],'#e5d5b5'),([current_corner_points[0],current_corner_points[1],current_ridge_points[1],current_ridge_points[0]],'#dfcba3'),([current_corner_points[1],current_corner_points[2],current_ridge_points[1]],'#d1b88d'),([current_corner_points[2],current_corner_points[3],current_ridge_points[0],current_ridge_points[1]],'#bba078')]:
            # 정방형의 중복 꼭짓점을 제거하고 실제 네 면을 보존한다.
            current_face_points = list(dict.fromkeys(current_face_points))
            current_first_vector = [current_face_points[1][current_axis_index]-current_face_points[0][current_axis_index] for current_axis_index in range(3)]
            current_second_vector = [current_face_points[2][current_axis_index]-current_face_points[0][current_axis_index] for current_axis_index in range(3)]
            current_normal_vector = [current_first_vector[1]*current_second_vector[2]-current_first_vector[2]*current_second_vector[1],current_first_vector[2]*current_second_vector[0]-current_first_vector[0]*current_second_vector[2],current_first_vector[0]*current_second_vector[1]-current_first_vector[1]*current_second_vector[0]]
            # 면의 안쪽 법선과 직교 카메라 방향 (1,1,40)의 내적이다.
            current_face_visible = current_normal_vector[0]+current_normal_vector[1]+40*current_normal_vector[2] < 0
            current_roof_faces.append({'worldPoints':current_face_points,'visible':current_face_visible})
            if current_face_visible:
                append_structure_face(current_face_points,current_face_color)
    else:
        append_structure_face([(current_width_count,0,current_wall_height),(current_width_count,0,current_top_height),(current_width_count,current_depth_count,current_wall_height)],'#bab5aa')
        append_structure_face([(current_left_value,current_back_value,current_top_height),(current_left_value,current_front_value,current_wall_height),(current_right_value,current_front_value,current_wall_height),(current_right_value,current_back_value,current_top_height)],'#d1b88d')
    current_all_points=[point for points,color in current_face_records for point in points]
    current_center_x=(min(point[0] for point in current_all_points)+max(point[0] for point in current_all_points))/2
    current_center_y=(min(point[1] for point in current_all_points)+max(point[1] for point in current_all_points))/2
    def transform_canvas_point(current_point_value):
        return (512+2*(current_point_value[0]-current_center_x),512+2*(current_point_value[1]-current_center_y))
    current_face_records=[([transform_canvas_point(point) for point in points],color) for points,color in current_face_records]
    current_image_value=Image.new('RGB',(1024,1024),'#f5f4f0')
    current_draw_context=ImageDraw.Draw(current_image_value)
    current_svg_parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><rect width="1024" height="1024" fill="#f5f4f0"/>']
    for current_face_points,current_face_color in current_face_records:
        current_draw_context.polygon(current_face_points,fill=current_face_color,outline='#414950',width=2)
        current_svg_points=' '.join(f'{current_x_value},{current_y_value}' for current_x_value,current_y_value in current_face_points)
        current_svg_parts.append(f'<polygon points="{current_svg_points}" fill="{current_face_color}" stroke="#414950" stroke-width="2"/>')
    if current_review_enabled:
        current_ground_points=[(512-40*current_depth_count,650+20*current_depth_count),(512+40*(current_width_count-current_depth_count),650+20*(current_width_count+current_depth_count)),(512+40*current_width_count,650+20*current_width_count)]
        current_ground_points=[transform_canvas_point(point) for point in current_ground_points]
        current_draw_context.line(current_ground_points,fill='#16834a',width=3)
        for current_column_index in range(current_width_count+1):
            current_grid_points=[transform_canvas_point((512+40*(current_column_index-current_row_value),650+20*(current_column_index+current_row_value))) for current_row_value in (0,current_depth_count)]
            current_draw_context.line(current_grid_points,fill='#16834a',width=1)
        for current_row_index in range(current_depth_count+1):
            current_grid_points=[transform_canvas_point((512+40*(current_column_value-current_row_index),650+20*(current_column_value+current_row_index))) for current_column_value in (0,current_width_count)]
            current_draw_context.line(current_grid_points,fill='#16834a',width=1)
        current_draw_context.text((32,56),'World tile 80x40 / floor 80px | guide scale 2x / tile 160x80 / floor 160px',fill='#253342')
        current_draw_context.text((32,32),f"{current_structure_record['id']} | {current_width_count}x{current_depth_count} | {current_structure_record['floors']}F | {current_structure_record['entrance']} | door {current_door_width} tiles x 64px",fill='#253342')
    current_geometry_record = {
        'tileSize':[80,40], 'displayScale':2, 'floorHeight':80,
        'wallHeight':current_wall_height, 'doorHeight':64,
        'translation':[512-2*current_center_x,512-2*current_center_y],
        'groundPoints':[transform_canvas_point((512+40*(current_column_value-current_row_value),650+20*(current_column_value+current_row_value))) for current_column_value,current_row_value in ((0,0),(0,current_depth_count),(current_width_count,current_depth_count),(current_width_count,0))],
        'doorPoints':current_face_records[2][0],
        'roofFaces':current_roof_faces, 'roofRidge':current_roof_ridge,
    }
    current_image_value.info['geometry']=current_geometry_record
    current_svg_parts.append('</svg>')
    return current_image_value,''.join(current_svg_parts)


def generate_building_structure_files():
    from tools.review.domains.image.building_prompt import read_building_structure_catalog
    current_catalog_records=read_building_structure_catalog().values()
    for current_structure_record in current_catalog_records:
        current_image_value,current_svg_text=render_building_structure(current_structure_record)
        current_file_stem=BUILDING_STRUCTURE_ROOT/current_structure_record['id']
        current_file_stem.with_suffix('.geometry.json').write_text(json.dumps(current_image_value.info['geometry'],indent=2))
        current_image_value.save(current_file_stem.with_suffix('.png'))
        current_file_stem.with_suffix('.svg').write_text(current_svg_text)
        render_building_structure(current_structure_record,True)[0].save(BUILDING_STRUCTURE_ROOT/(current_structure_record['id']+'-review.png'))
        print(f"{datetime.now().isoformat()}/building-guide/generated {current_structure_record['id']}")


if __name__=='__main__':
    generate_building_structure_files()
