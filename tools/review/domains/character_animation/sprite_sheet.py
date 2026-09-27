"""편집 좌표를 실제 투명 스프라이트 시트로 렌더링한다."""
import hashlib
import math
import re
from pathlib import Path
from PIL import Image

SPRITE_REVIEW_ROOT=Path(__file__).resolve().parents[4]/'.tmp/manager-current'
SPRITE_DIRECTION_ORDER=('down_left','down_right','up_left','up_right')
SPRITE_MAXIMUM_PIXELS=33554432


def resolve_sprite_image_path(source_asset_record,current_frame_record):
    current_image_url=current_frame_record['url']
    if source_asset_record['id'].startswith('asset:'):
        if not re.fullmatch(r'/animation-\d+/[^/]+\.png',current_image_url):raise ValueError('등록 시트 이미지 경로 오류')
        current_image_path=SPRITE_REVIEW_ROOT/current_image_url.lstrip('/')
        # 검수 빌드는 승인된 프론트 이미지를 심볼릭 링크로 전달할 수 있다.
    else:
        from .character_animation_jobs import read_generation_status
        current_job_status=read_generation_status(source_asset_record['id'])
        expected_url_prefix='/character-animation/files/'+source_asset_record['id']+'/'
        if not current_image_url.startswith(expected_url_prefix):raise ValueError('생성 프레임 경로 오류')
        current_job_directory=Path(current_job_status['path']).resolve()
        current_image_path=(current_job_directory/current_image_url[len(expected_url_prefix):]).resolve()
        if not current_image_path.is_relative_to(current_job_directory):raise ValueError('생성 프레임 경로 이탈')
    if not current_image_path.is_file():raise ValueError('원본 이미지가 없습니다: '+str(current_image_path))
    return current_image_path


def render_sprite_saved_sheet(source_asset_record,current_project_document,output_image_path):
    previous_cell_pixels=current_project_document.get('output',{}).get('cellSize',512)
    output_cell_pixels=source_asset_record['frames'][0]['rect']['width']
    if type(output_cell_pixels) is not int or not 1<=output_cell_pixels<=4096:raise ValueError('원본 셀 크기 오류')
    if any(current_frame_record['rect']['width']!=output_cell_pixels or current_frame_record['rect']['height']!=output_cell_pixels for current_frame_record in source_asset_record['frames']):raise ValueError('동일 크기의 정사각형 원본 셀만 지원합니다.')
    output_size_ratio=output_cell_pixels/previous_cell_pixels
    current_frame_records=source_asset_record['frames']
    if not 1<=len(current_frame_records)<=128:raise ValueError('저장 시트는 1~128프레임을 지원합니다.')
    if any(current_frame_record['direction'] not in SPRITE_DIRECTION_ORDER for current_frame_record in current_frame_records):raise ValueError('지원하지 않는 시트 방향')
    direction_frame_groups=[[current_frame_record for current_frame_record in current_frame_records if current_frame_record['direction']==current_direction_name] for current_direction_name in SPRITE_DIRECTION_ORDER]
    direction_frame_groups=[current_frame_group for current_frame_group in direction_frame_groups if current_frame_group]
    output_column_count=max(map(len,direction_frame_groups))
    output_sheet_width=output_column_count*output_cell_pixels
    output_sheet_height=len(direction_frame_groups)*output_cell_pixels
    if output_sheet_width>16384 or output_sheet_width*output_sheet_height>SPRITE_MAXIMUM_PIXELS:raise ValueError('출력 시트가 너무 큽니다.')
    output_sheet_image=Image.new('RGBA',(output_sheet_width,output_sheet_height))
    previous_anchor_height=448 if current_project_document['version']==1 else math.floor(previous_cell_pixels*.96+.5)
    output_anchor_height=math.floor(output_cell_pixels*.96+.5)
    for direction_row_index,current_frame_group in enumerate(direction_frame_groups):
        for frame_column_index,current_frame_record in enumerate(current_frame_group):
            current_frame_rect=current_frame_record['rect']
            with Image.open(resolve_sprite_image_path(source_asset_record,current_frame_record)) as source_image_value:
                source_frame_image=source_image_value.convert('RGBA').crop((current_frame_rect['x'],current_frame_rect['y'],current_frame_rect['x']+current_frame_rect['width'],current_frame_rect['y']+current_frame_rect['height']))
            current_frame_settings=current_project_document['frames'][current_frame_record['frameId']]
            current_frame_scale=current_frame_settings['scale']*output_size_ratio
            output_offset_left=output_cell_pixels/2-current_frame_settings['anchorX']*current_frame_scale+current_frame_settings['x']*output_size_ratio
            output_offset_top=(previous_anchor_height+current_frame_settings['y'])*output_size_ratio-current_frame_settings['anchorY']*current_frame_scale
            # 출력 좌표를 원본 좌표로 역변환하며 알파를 미리 곱한 색상으로 보간한다.
            output_frame_image=source_frame_image.convert('RGBa').transform((output_cell_pixels,output_cell_pixels),Image.Transform.AFFINE,(1/current_frame_scale,0,-output_offset_left/current_frame_scale,0,1/current_frame_scale,-output_offset_top/current_frame_scale),resample=Image.Resampling.BICUBIC).convert('RGBA')
            output_sheet_image.paste(output_frame_image,(frame_column_index*output_cell_pixels,direction_row_index*output_cell_pixels))
    output_temporary_path=output_image_path.with_suffix('.partial')
    try:
        output_sheet_image.save(output_temporary_path,format='PNG')
        output_temporary_path.replace(output_image_path)
    finally:output_temporary_path.unlink(missing_ok=True)
    return {'file':output_image_path.name,'width':output_sheet_width,'height':output_sheet_height,'cellSize':output_cell_pixels,'columns':output_column_count,'rows':len(direction_frame_groups),'sha256':hashlib.sha256(output_image_path.read_bytes()).hexdigest(),'anchor':{'x':output_cell_pixels/2,'y':output_anchor_height}}
