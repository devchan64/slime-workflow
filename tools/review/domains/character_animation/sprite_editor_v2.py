"""사용자 등록 프레임의 비파괴 편집·불변 수정 이력·출력을 관리한다."""
import base64
import hashlib
import io
import json
import math
import re
import shutil
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from PIL import Image
from tools.review.common.generation_records import write_record_atomically

SPRITE_V2_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]/'.tmp/test/sprite-editor-v2'
SPRITE_V2_COMMAND_LOCK = threading.RLock()
SPRITE_V2_FRAME_LIMIT = 128
SPRITE_V2_IMAGE_LIMIT = 8_000_000
SPRITE_V2_PIXEL_LIMIT = 16_777_216
SPRITE_V2_TIME_ZONE = ZoneInfo('Asia/Seoul')


def require_exact_fields(current_record_value, expected_field_names):
    if not isinstance(current_record_value, dict) or set(current_record_value) != set(expected_field_names):
        raise ValueError('편집 문서 필드가 올바르지 않습니다: '+', '.join(expected_field_names))


def require_finite_number(current_number_value, minimum_number_value, maximum_number_value):
    if type(current_number_value) not in (int, float) or not math.isfinite(current_number_value) or not minimum_number_value <= current_number_value <= maximum_number_value:
        raise ValueError(f'숫자는 {minimum_number_value}~{maximum_number_value} 범위여야 합니다.')


def resolve_v2_project(project_identifier_value):
    if not isinstance(project_identifier_value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', project_identifier_value):
        raise ValueError('작업 ID 형식 오류')
    project_directory_path = SPRITE_V2_WORKSPACE_ROOT/project_identifier_value[:19]/project_identifier_value
    if not (project_directory_path/'project.json').is_file():
        raise ValueError('등록되지 않은 편집 작업입니다.')
    return project_directory_path


def validate_v2_document(current_document_record, project_directory_path):
    require_exact_fields(current_document_record, ('version','name','cellSize','fps','reference','frames'))
    if type(current_document_record['version']) is not int or current_document_record['version'] != 2:
        raise ValueError('v2 편집 문서만 지원합니다.')
    if not isinstance(current_document_record['name'], str) or not 1 <= len(current_document_record['name'].strip()) <= 120:
        raise ValueError('작업 이름은 1~120자입니다.')
    if type(current_document_record['cellSize']) is not int or current_document_record['cellSize'] not in (256,384):
        raise ValueError('출력 크기는 256 또는 384입니다.')
    require_finite_number(current_document_record['fps'],1,60)
    current_frame_records = current_document_record['frames']
    if not isinstance(current_frame_records,list) or len(current_frame_records) > SPRITE_V2_FRAME_LIMIT:
        raise ValueError('프레임은 최대 128장입니다.')
    current_image_records = list(current_frame_records)
    if current_document_record['reference'] is not None:
        current_image_records.append(current_document_record['reference'])
    seen_frame_identifiers = set()
    for current_image_record in current_image_records:
        current_axis_fields=('scaleX','scaleY') if 'scaleX' in current_image_record or 'scaleY' in current_image_record else ()
        require_exact_fields(current_image_record, ('id','asset','name','x','y','scale','duration','face','guides',*current_axis_fields))
        for current_axis_field in current_axis_fields:
            require_finite_number(current_image_record[current_axis_field],.01,8)
        if not isinstance(current_image_record['id'],str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}',current_image_record['id']) or current_image_record['id'] in seen_frame_identifiers:
            raise ValueError('프레임 ID는 고유해야 합니다.')
        seen_frame_identifiers.add(current_image_record['id'])
        if not isinstance(current_image_record['name'],str) or len(current_image_record['name'])>200:
            raise ValueError('이미지 이름 오류')
        current_asset_name = current_image_record['asset']
        if not isinstance(current_asset_name,str) or not re.fullmatch(r'[a-f0-9]{64}',current_asset_name) or not (project_directory_path/'images'/f'{current_asset_name}.png').is_file():
            raise ValueError('등록되지 않은 이미지입니다.')
        for current_field_name in ('x','y'):
            require_finite_number(current_image_record[current_field_name],-8192,8192)
        require_finite_number(current_image_record['scale'],.01,8)
        require_finite_number(current_image_record['duration'],0,10000)
        require_exact_fields(current_image_record['face'],('x','y','radius'))
        for current_field_name in ('x','y'):
            require_finite_number(current_image_record['face'][current_field_name],-8192,8192)
        require_finite_number(current_image_record['face']['radius'],1,2048)
        if not isinstance(current_image_record['guides'],list) or len(current_image_record['guides'])>32:
            raise ValueError('가이드는 최대 32개입니다.')
        for current_guide_record in current_image_record['guides']:
            require_exact_fields(current_guide_record,('label','axis','position'))
            if current_guide_record['axis'] not in ('x','y') or not isinstance(current_guide_record['label'],str) or len(current_guide_record['label'])>40:
                raise ValueError('가이드 형식 오류')
            require_finite_number(current_guide_record['position'],-8192,8192)


def save_v2_revision(project_directory_path, current_document_record, parent_revision_value):
    validate_v2_document(current_document_record,project_directory_path)
    latest_record_path = project_directory_path/'latest.json'
    if latest_record_path.exists() and json.loads(latest_record_path.read_text())['revision'] != parent_revision_value:
        raise ValueError('다른 화면에서 수정되었습니다. 최신 작업을 불러온 뒤 다시 저장하세요.')
    current_revision_value = datetime.now(SPRITE_V2_TIME_ZONE).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8]
    saved_revision_record = {'revision':current_revision_value,'parent':parent_revision_value,'saved_at':datetime.now(SPRITE_V2_TIME_ZONE).isoformat(),'document':current_document_record}
    write_record_atomically(project_directory_path/'revisions'/f'{current_revision_value}.json',saved_revision_record)
    write_record_atomically(latest_record_path,saved_revision_record)
    return saved_revision_record


def export_v2_revision(project_directory_path, saved_revision_record):
    current_document_record = saved_revision_record['document']
    validate_v2_document(current_document_record,project_directory_path)
    if not current_document_record['frames']:
        raise ValueError('내보낼 프레임을 먼저 등록하세요.')
    output_cell_pixels = current_document_record['cellSize']
    output_frame_images = []
    output_frame_durations = []
    output_archive_buffer = io.BytesIO()
    with zipfile.ZipFile(output_archive_buffer,'w',zipfile.ZIP_DEFLATED) as output_zip_archive:
        for current_frame_index,current_frame_record in enumerate(current_document_record['frames']):
            with Image.open(project_directory_path/'images'/f"{current_frame_record['asset']}.png") as source_image_value:
                current_base_scale = output_cell_pixels/max(source_image_value.size)
                current_horizontal_scale = current_frame_record.get('scaleX',current_frame_record['scale'])*current_base_scale
                current_vertical_scale = current_frame_record.get('scaleY',current_frame_record['scale'])*current_base_scale
                current_offset_left = (output_cell_pixels-source_image_value.width*current_horizontal_scale)/2+current_frame_record['x']
                current_offset_top = (output_cell_pixels-source_image_value.height*current_vertical_scale)/2+current_frame_record['y']
                output_frame_image = source_image_value.convert('RGBa').transform((output_cell_pixels,output_cell_pixels),Image.Transform.AFFINE,(1/current_horizontal_scale,0,-current_offset_left/current_horizontal_scale,0,1/current_vertical_scale,-current_offset_top/current_vertical_scale),resample=Image.Resampling.BICUBIC).convert('RGBA')
            output_frame_images.append(output_frame_image)
            output_frame_durations.append(max(10,round((current_frame_record['duration'] or 1000/current_document_record['fps'])/10)*10))
            current_png_buffer = io.BytesIO()
            output_frame_image.save(current_png_buffer,format='PNG')
            output_zip_archive.writestr(f'frame-{current_frame_index+1:03}.png',current_png_buffer.getvalue())
        output_frame_count = len(output_frame_images)
        output_row_count = math.isqrt(output_frame_count)
        while output_frame_count % output_row_count:
            output_row_count -= 1
        output_column_count = output_frame_count // output_row_count
        output_sheet_image = Image.new('RGBA',(output_column_count*output_cell_pixels,math.ceil(len(output_frame_images)/output_column_count)*output_cell_pixels))
        for current_frame_index,current_frame_image in enumerate(output_frame_images):
            output_sheet_image.paste(current_frame_image,((current_frame_index%output_column_count)*output_cell_pixels,(current_frame_index//output_column_count)*output_cell_pixels))
        current_png_buffer = io.BytesIO()
        output_sheet_image.save(current_png_buffer,format='PNG')
        output_zip_archive.writestr('sheet.png',current_png_buffer.getvalue())
        gif_frame_images = []
        for current_frame_image in output_frame_images:
            current_gif_background = Image.new('RGBA',current_frame_image.size,'white')
            current_gif_background.alpha_composite(current_frame_image)
            gif_frame_images.append(current_gif_background.convert('RGB'))
        current_gif_buffer = io.BytesIO()
        gif_frame_images[0].save(current_gif_buffer,format='GIF',save_all=True,append_images=gif_frame_images[1:],duration=output_frame_durations,loop=0,disposal=2)
        output_zip_archive.writestr('review.gif',current_gif_buffer.getvalue())
        output_zip_archive.writestr('metadata.json',json.dumps({'revision':saved_revision_record['revision'],'document':current_document_record,'columns':output_column_count,'durations_ms':output_frame_durations,'gif_background':'white','note':'PNG는 입력 알파를 유지하며 배경을 자동 제거하지 않습니다.'},ensure_ascii=False,indent=2))
    export_archive_bytes = output_archive_buffer.getvalue()
    export_directory_path = project_directory_path/'exports'
    export_directory_path.mkdir(exist_ok=True)
    (export_directory_path/f"{saved_revision_record['revision']}.zip").write_bytes(export_archive_bytes)
    return {'filename':f"sprite-v2-{saved_revision_record['revision']}.zip",'data':base64.b64encode(export_archive_bytes).decode()}


def execute_v2_command(operation_command_name, command_payload_value):
    with SPRITE_V2_COMMAND_LOCK:
        if operation_command_name == 'sprite-v2-list':
            require_exact_fields(command_payload_value,())
            current_project_records = []
            for latest_record_path in sorted(SPRITE_V2_WORKSPACE_ROOT.glob('*/*/latest.json'),reverse=True):
                current_latest_record = json.loads(latest_record_path.read_text())
                current_project_records.append({'id':latest_record_path.parent.name,'name':current_latest_record['document']['name'],'frames':len(current_latest_record['document']['frames']),'saved_at':current_latest_record['saved_at']})
            return {'items':current_project_records}
        if operation_command_name == 'sprite-v2-create':
            require_exact_fields(command_payload_value,('name','cellSize'))
            current_time_string = datetime.now(SPRITE_V2_TIME_ZONE).strftime('%Y-%m-%d_%H-%M-%S')
            project_identifier_value = current_time_string+'-'+uuid4().hex[:8]
            project_directory_path = SPRITE_V2_WORKSPACE_ROOT/current_time_string/project_identifier_value
            current_document_record = {'version':2,'name':command_payload_value['name'],'cellSize':command_payload_value['cellSize'],'fps':8,'reference':None,'frames':[]}
            validate_v2_document(current_document_record,project_directory_path)
            (project_directory_path/'images').mkdir(parents=True)
            (project_directory_path/'revisions').mkdir()
            write_record_atomically(project_directory_path/'project.json',{'id':project_identifier_value,'created_at':datetime.now(SPRITE_V2_TIME_ZONE).isoformat()})
            return {'id':project_identifier_value,**save_v2_revision(project_directory_path,current_document_record,None)}
        expected_command_fields = {'sprite-v2-revision-delete':('id','revision','confirm'),'sprite-v2-delete':('id','confirm'),'sprite-v2-upload':('id','data'),'sprite-v2-save':('id','parent','document'),'sprite-v2-load':('id','revision'),'sprite-v2-history':('id',),'sprite-v2-export':('id','revision')}
        if operation_command_name not in expected_command_fields:
            raise ValueError('지원하지 않는 v2 명령입니다.')
        require_exact_fields(command_payload_value,expected_command_fields[operation_command_name])
        project_directory_path = resolve_v2_project(command_payload_value['id'])
        if operation_command_name == 'sprite-v2-delete':
            if command_payload_value['confirm'] is not True:
                raise ValueError('작업 삭제 확인이 필요합니다.')
            if project_directory_path.is_symlink() or project_directory_path.parent.is_symlink() or not project_directory_path.resolve().is_relative_to(SPRITE_V2_WORKSPACE_ROOT.resolve()):
                raise ValueError('작업 삭제 경로가 올바르지 않습니다.')
            shutil.rmtree(project_directory_path)
            return {'id':command_payload_value['id'],'deleted':True}
        if operation_command_name == 'sprite-v2-revision-delete':
            if command_payload_value['confirm'] is not True:
                raise ValueError('수정본 삭제 확인이 필요합니다.')
            current_revision_identifier=command_payload_value['revision']
            if not isinstance(current_revision_identifier,str) or not re.fullmatch(r'\d{8}T\d{6}-[a-f0-9]{8}',current_revision_identifier):
                raise ValueError('수정 버전 형식 오류')
            current_revision_path=project_directory_path/'revisions'/f'{current_revision_identifier}.json'
            if not current_revision_path.is_file():
                raise ValueError('삭제할 수정본이 없습니다.')
            current_remaining_records=[json.loads(value.read_text()) for value in (project_directory_path/'revisions').glob('*.json') if value!=current_revision_path]
            if not current_remaining_records:
                raise ValueError('마지막 수정본은 삭제할 수 없습니다. 작업 전체 삭제를 사용하세요.')
            current_latest_record=json.loads((project_directory_path/'latest.json').read_text())
            if current_latest_record['revision']==current_revision_identifier:
                current_latest_record=max(current_remaining_records,key=lambda value:(value['saved_at'],value['revision']))
                write_record_atomically(project_directory_path/'latest.json',current_latest_record)
            current_revision_path.unlink()
            return {'deleted':True,'revision':current_revision_identifier,'latest':current_latest_record['revision']}
        if operation_command_name == 'sprite-v2-upload':
            current_encoded_data = command_payload_value['data']
            if not isinstance(current_encoded_data,str) or len(current_encoded_data)>SPRITE_V2_IMAGE_LIMIT*4/3+4:
                raise ValueError('이미지는 최대 8MB입니다.')
            try:
                current_image_bytes = base64.b64decode(current_encoded_data,validate=True)
                with Image.open(io.BytesIO(current_image_bytes)) as source_image_value:
                    if source_image_value.format not in ('PNG','JPEG','WEBP') or source_image_value.width*source_image_value.height>SPRITE_V2_PIXEL_LIMIT or getattr(source_image_value,'n_frames',1)!=1:
                        raise ValueError('정지 PNG/JPEG/WebP, 최대 1600만 픽셀만 지원합니다.')
                    current_png_buffer = io.BytesIO()
                    source_image_value.convert('RGBA').save(current_png_buffer,format='PNG')
                    current_image_size = list(source_image_value.size)
            except (OSError,ValueError,Image.DecompressionBombError) as image_decode_error:
                raise ValueError('이미지 입력 오류: '+str(image_decode_error)) from image_decode_error
            current_png_bytes = current_png_buffer.getvalue()
            current_asset_hash = hashlib.sha256(current_png_bytes).hexdigest()
            (project_directory_path/'images'/f'{current_asset_hash}.png').write_bytes(current_png_bytes)
            return {'asset':current_asset_hash,'size':current_image_size,'data':base64.b64encode(current_png_bytes).decode()}
        if operation_command_name == 'sprite-v2-save':
            return save_v2_revision(project_directory_path,command_payload_value['document'],command_payload_value['parent'])
        if operation_command_name == 'sprite-v2-history':
            return {'items':[{'revision':current_revision_record['revision'],'parent':current_revision_record['parent'],'saved_at':current_revision_record['saved_at'],'name':current_revision_record['document']['name'],'frames':len(current_revision_record['document']['frames'])} for current_revision_record in (json.loads(current_revision_path.read_text()) for current_revision_path in sorted((project_directory_path/'revisions').glob('*.json'),reverse=True))]}
        selected_revision_value = command_payload_value['revision']
        if selected_revision_value is not None and (not isinstance(selected_revision_value,str) or not re.fullmatch(r'\d{8}T\d{6}-[a-f0-9]{8}',selected_revision_value)):
            raise ValueError('수정 버전 형식 오류')
        selected_revision_path = project_directory_path/'revisions'/f'{selected_revision_value}.json' if selected_revision_value else project_directory_path/'latest.json'
        saved_revision_record = json.loads(selected_revision_path.read_text())
        if operation_command_name == 'sprite-v2-export':
            return export_v2_revision(project_directory_path,saved_revision_record)
        current_image_records = list(saved_revision_record['document']['frames'])
        if saved_revision_record['document']['reference'] is not None:
            current_image_records.append(saved_revision_record['document']['reference'])
        return {'id':command_payload_value['id'],**saved_revision_record,'latest':json.loads((project_directory_path/'latest.json').read_text())['revision'],'images':{current_asset_hash:base64.b64encode((project_directory_path/'images'/f'{current_asset_hash}.png').read_bytes()).decode() for current_asset_hash in {current_image_record['asset'] for current_image_record in current_image_records}}}
