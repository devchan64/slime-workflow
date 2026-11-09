"""프레임 크롭과 공통 앵커를 검수하는 스프라이트 시트 클라이언트."""
import base64
import hashlib
import json
import math
from io import BytesIO
from pathlib import Path
import tempfile
import gradio as gr
from PIL import Image
from tools.review.common.management_client import execute_remote_management_command

SPRITE_EDITOR_FRAME_FIELDS = ('x','y','width','height','anchorX','anchorY')
SPRITE_EDITOR_UPLOAD_LIMIT = 8_000_000
SPRITE_EDITOR_DEFAULT_COLUMNS = 4
SPRITE_EDITOR_SETTINGS_MIN_WIDTH = 280
SPRITE_EDITOR_PREVIEW_MIN_WIDTH = 320


def search_sprite_asset_choices(current_search_text,current_source_kind="assets"):
    current_result_record=execute_remote_management_command('character-animation','sheet-search',{'query':current_search_text or '', 'source':current_source_kind})
    return gr.update(choices=[(current_asset_record['label'],current_asset_record['path']) for current_asset_record in current_result_record['items']],value=None),f"{len(current_result_record['items'])}개 스프라이트를 찾았습니다. 선택 후 선택 시트 불러오기를 누르세요."


def build_sprite_clip_choices(current_source_record):
    """등록 클립을 재생 선택지로 제공하며 원본 프레임 순서는 보존한다."""
    current_animation_record=current_source_record.get('animation') or {}
    current_clip_records=current_animation_record.get('clips',[])
    current_clip_choices=[('현재 시트 전체','')]
    for current_clip_record in current_clip_records:
        current_clip_choices.append((f"{current_clip_record['action']} · {current_clip_record['direction']} · {len(current_clip_record['frames'])}프레임",current_clip_record['clipId']))
    return gr.update(choices=current_clip_choices,value='',interactive=bool(current_clip_records))


def calculate_registered_sheet_layout(current_animation_record):
    """높이가 다른 프레임도 세로 영역이 겹치면 같은 행으로 계산한다."""
    current_row_groups=[]
    for current_frame_record in sorted(current_animation_record['frames'],key=lambda current_frame_value:current_frame_value['rect']['y']):
        current_frame_rect=current_frame_record['rect']
        current_frame_top=current_frame_rect['y']
        current_frame_bottom=current_frame_top+current_frame_rect['height']
        if current_row_groups and current_frame_top<current_row_groups[-1][0]:
            current_row_groups[-1][0]=max(current_row_groups[-1][0],current_frame_bottom)
            current_row_groups[-1][1]+=1
        else:
            current_row_groups.append([current_frame_bottom,1])
    if not current_row_groups:
        raise gr.Error('등록된 좌표맵에 프레임이 없습니다.')
    return max(current_row_group[1] for current_row_group in current_row_groups),len(current_row_groups)


def select_sprite_asset_image(current_asset_path,current_source_kind="assets"):
    if not current_asset_path:raise gr.Error('검색 결과에서 스프라이트를 선택하세요.')
    try:
        current_result_record=execute_remote_management_command('character-animation','sheet-image',{'path':current_asset_path,'source':current_source_kind})
    except ValueError as current_load_error:
        raise gr.Error(f'스프라이트를 가져오지 못했습니다: {current_load_error}') from current_load_error
    current_temporary_directory=Path(tempfile.mkdtemp(prefix='sprite-asset-input-'))
    current_image_path=current_temporary_directory/Path(current_asset_path).name
    current_image_path.write_bytes(base64.b64decode(current_result_record['image'],validate=True))
    if current_result_record.get('animation'):
        current_image_path.with_suffix('.animation.json').write_text(json.dumps(current_result_record['animation']))
    current_layout_values=calculate_registered_sheet_layout(current_result_record['animation']) if current_result_record.get('animation') else (current_result_record['layout']['columns'],current_result_record['layout']['rows']) if current_result_record.get('layout') else (gr.update(),gr.update())
    return str(current_image_path),{'source':current_source_kind,'path':current_asset_path,'metadataSha256':current_result_record['metadataSha256'],'animation':current_result_record.get('animation'),'runtimeDimensions':current_result_record.get('runtimeDimensions',{}),'imageSha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest()},f"{'베이스라인' if current_source_kind=='baseline' else '에셋'} 원본: {current_asset_path}\n원본으로 가져왔습니다. 좌표맵이 있으면 원본 열·행을 자동 반영합니다. 시트 불러오기를 누르세요. 기존 편집은 아직 변경하지 않았습니다.",*current_layout_values


def load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record=None):
    if not current_file_path:raise gr.Error('PNG 시트를 먼저 선택하세요.')
    current_image_bytes=Path(current_file_path).read_bytes()
    if len(current_image_bytes)>SPRITE_EDITOR_UPLOAD_LIMIT:raise gr.Error('PNG 시트는 8MB 이하여야 합니다.')
    with Image.open(BytesIO(current_image_bytes)) as current_image_value:
        if current_image_value.format!='PNG' or current_image_value.width*current_image_value.height>16_777_216:raise gr.Error('1600만 픽셀 이하의 PNG 시트가 필요합니다.')
        current_width_value,current_height_value=current_image_value.size
    if current_asset_record and current_asset_record.get('animation') and current_asset_record.get('imageSha256')==hashlib.sha256(current_image_bytes).hexdigest():
        current_animation_record=current_asset_record['animation']
        current_frame_rows=[[current_frame['rect']['x'],current_frame['rect']['y'],current_frame['rect']['width'],current_frame['rect']['height'],current_frame['anchor']['x'],current_frame['anchor']['y']] for current_frame in current_animation_record['frames']]
        current_cell_width=max(current_frame[2] for current_frame in current_frame_rows)
        current_cell_height=max(current_frame[3] for current_frame in current_frame_rows)
        return 'data:image/png;base64,'+base64.b64encode(current_image_bytes).decode(),current_frame_rows,SPRITE_EDITOR_DEFAULT_COLUMNS,gr.update(maximum=max(2,len(current_frame_rows)),value=1),'등록된 좌표맵의 프레임과 앵커를 불러왔습니다.'
    if any(type(current_value) not in (int,float) or int(current_value)!=current_value or current_value<1 for current_value in (current_columns_value,current_rows_value)):raise gr.Error('원본 열·행 수는 양의 정수여야 합니다.')
    current_column_count,current_row_count=int(current_columns_value),int(current_rows_value)
    if current_column_count*current_row_count>128 or current_column_count>current_width_value or current_row_count>current_height_value:raise gr.Error('최대 128프레임이며 각 셀은 최소 1픽셀이어야 합니다.')
    current_column_edges=[round(current_column_index*current_width_value/current_column_count) for current_column_index in range(current_column_count+1)]
    current_row_edges=[round(current_row_index*current_height_value/current_row_count) for current_row_index in range(current_row_count+1)]
    current_frame_rows=[]
    for current_row_index in range(current_row_count):
        for current_column_index in range(current_column_count):
            current_cell_width=current_column_edges[current_column_index+1]-current_column_edges[current_column_index]
            current_cell_height=current_row_edges[current_row_index+1]-current_row_edges[current_row_index]
            current_frame_rows.append([current_column_edges[current_column_index],current_row_edges[current_row_index],current_cell_width,current_cell_height,current_cell_width//2,current_cell_height-1])
    return 'data:image/png;base64,'+base64.b64encode(current_image_bytes).decode(),current_frame_rows,SPRITE_EDITOR_DEFAULT_COLUMNS,gr.update(maximum=max(2,len(current_frame_rows)),value=1),f'{current_column_count}열 × {current_row_count}행 · {len(current_frame_rows)}프레임으로 균등 분할했습니다. 나머지 픽셀은 경계에 분산하며 셀 크기는 최대 1px 차이입니다.'



def prepare_sprite_sheet_load(current_file_path,current_columns_value,current_rows_value,current_image_data,current_asset_record):
    if not current_file_path:raise gr.Error('PNG 시트를 먼저 선택하세요.')
    current_pending_load={'path':current_file_path,'columns':current_columns_value,'rows':current_rows_value,'asset':current_asset_record}
    if current_image_data:
        return (*([gr.update()]*4),'재불러오기 대기 중입니다. 시트 불러오기 바로 아래의 불러오기 확인을 누르면 변경한 행·열이 반영됩니다.',gr.update(visible=True),current_pending_load,gr.update(),gr.update(),gr.update(),gr.update(),gr.update(),gr.update())
    current_loaded_values=load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record)
    return (*current_loaded_values,gr.update(visible=False),{},gr.update(interactive=True),[current_frame_row[:4] for current_frame_row in current_loaded_values[1]],{},None,gr.update(visible=False),None)


def confirm_sprite_sheet_load(current_pending_load,current_file_path,current_columns_value,current_rows_value,current_asset_record):
    if current_pending_load!={'path':current_file_path,'columns':current_columns_value,'rows':current_rows_value,'asset':current_asset_record}:raise gr.Error('확인 후 입력이 변경되었습니다. 다시 불러오세요.')
    current_loaded_values=load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record)
    return (*current_loaded_values,gr.update(visible=False),{},gr.update(interactive=True),[current_frame_row[:4] for current_frame_row in current_loaded_values[1]],{},None,gr.update(visible=False),None)



def describe_loaded_sprite_source(current_source_record,current_file_path,current_frame_count):
    """검색 선택과 실제 편집 원본을 구분한다."""
    current_source_labels={'assets':'에셋','baseline':'베이스라인','upload':'직접 PNG'}
    return f"**현재 편집 원본 · {current_source_labels[current_source_record['source']]}** · {current_frame_count}프레임\n\n`{current_source_record.get('path') or Path(current_file_path).name}`"


def complete_sprite_source_load(current_candidate_record):
    """확정된 원본만 편집 상태와 저장 대상으로 반영한다."""
    current_file_path=current_candidate_record['path']
    current_source_record=current_candidate_record['asset']
    current_loaded_values=load_sprite_sheet_input(current_file_path,current_candidate_record['columns'],current_candidate_record['rows'],current_source_record)
    return (*current_loaded_values,gr.update(visible=False),{},gr.update(interactive=True),
            [current_frame_row[:4] for current_frame_row in current_loaded_values[1]],{},None,gr.update(visible=False),None,
            current_source_record,current_source_record.get('path',''),
            describe_loaded_sprite_source(current_source_record,current_file_path,len(current_loaded_values[1])),
            gr.update(open=False),False)


def prepare_registered_sprite_load(current_asset_path,current_source_kind,current_image_data):
    """등록 시트는 좌표 또는 레이아웃을 읽어 한 번에 불러온다."""
    current_file_path,current_source_record,_,current_column_count,current_row_count=select_sprite_asset_image(current_asset_path,current_source_kind)
    if not isinstance(current_column_count,int) or not isinstance(current_row_count,int):
        raise gr.Error('이 시트에는 좌표맵·행열 정보가 없습니다. 직접 PNG에서 파일과 행·열을 지정하세요.')
    current_candidate_record={'path':current_file_path,'columns':current_column_count,'rows':current_row_count,'asset':current_source_record,'selection':[current_source_kind,current_asset_path]}
    if current_image_data:
        return (*([gr.update()]*4),'기존 편집을 교체하려면 위의 불러오기 확인을 누르세요.',gr.update(visible=True),current_candidate_record,*([gr.update()]*11))
    return complete_sprite_source_load(current_candidate_record)


def prepare_uploaded_sprite_load(current_file_path,current_columns_value,current_rows_value,current_image_data):
    """직접 입력은 검색 목록과 독립적으로 균등 분할한다."""
    if not current_file_path:
        raise gr.Error('직접 PNG 파일을 먼저 선택하세요.')
    current_candidate_record={'path':current_file_path,'columns':current_columns_value,'rows':current_rows_value,'asset':{'source':'upload'},'selection':['upload',current_file_path,current_columns_value,current_rows_value]}
    if current_image_data:
        return (*([gr.update()]*4),'기존 편집을 교체하려면 위의 불러오기 확인을 누르세요.',gr.update(visible=True),current_candidate_record,*([gr.update()]*11))
    return complete_sprite_source_load(current_candidate_record)


def confirm_selected_sprite_load(current_pending_load,current_asset_path,current_source_kind,current_file_path,current_columns_value,current_rows_value):
    """확인 중 선택이 변경되면 편집 원본을 교체하지 않는다."""
    if not current_pending_load:
        raise gr.Error('불러올 원본을 먼저 선택하세요.')
    current_expected_selection=([current_source_kind,current_asset_path] if current_pending_load['asset']['source']!='upload'
                                else ['upload',current_file_path,current_columns_value,current_rows_value])
    if current_pending_load['selection']!=current_expected_selection:
        raise gr.Error('확인 중 원본 선택이 변경되었습니다. 다시 불러오세요.')
    return complete_sprite_source_load(current_pending_load)


def build_sprite_sheet_payload(current_image_data,current_frame_rows,current_columns_value,current_source_bounds=None):
    if not current_image_data:raise gr.Error('시트를 먼저 불러오세요.')
    current_values=[current_columns_value]
    if any(type(current_value) not in (int,float) or not float(current_value).is_integer() for current_value in current_values):raise gr.Error('출력 설정은 정수여야 합니다.')
    current_rows=current_frame_rows.values.tolist() if hasattr(current_frame_rows,'values') else current_frame_rows
    current_frames=[]
    for current_frame_row in current_rows:
        if len(current_frame_row)!=6 or any(type(current_value) not in (int,float) or not math.isfinite(current_value) for current_value in current_frame_row) or any(not float(current_value).is_integer() for current_value in current_frame_row[:4]):raise gr.Error('크롭은 정수, 앵커는 유한한 숫자여야 합니다.')
        current_frames.append(dict(zip(SPRITE_EDITOR_FRAME_FIELDS,[*map(int,current_frame_row[:4]),*current_frame_row[4:]])))
    current_request_record={'image':current_image_data.split(',',1)[1],'frames':current_frames,'columns':int(current_columns_value)}
    if current_source_bounds is not None:current_request_record['sourceFrames']=current_source_bounds
    return current_request_record


def export_sprite_sheet_result(current_image_data,current_frame_rows,current_columns_value,current_source_bounds=None):
    current_request_record=build_sprite_sheet_payload(current_image_data,current_frame_rows,current_columns_value,current_source_bounds)
    current_result_record=execute_remote_management_command('character-animation','sheet-export',current_request_record)
    current_download_directory=Path(tempfile.mkdtemp(prefix='sprite-sheet-download-'))
    current_image_path=current_download_directory/'sprite-sheet.png';current_map_path=current_download_directory/'coordinates.json'
    current_image_path.write_bytes(base64.b64decode(current_result_record['image'],validate=True))
    current_map_path.write_text(json.dumps(current_result_record['coordinates'],ensure_ascii=False,indent=2)+'\n')
    return [str(current_image_path),str(current_map_path)],f"완료 · 작업 ID {current_result_record['id']} · 시트와 좌표맵이 저장되었습니다."


def export_sprite_gif_result(current_image_data,current_frame_rows,current_source_bounds,current_playback_rate,current_first_frame,current_last_frame):
    """선택한 연속 프레임의 편집 좌표를 공용 GIF 명령으로 전달한다."""
    current_request_record=build_sprite_sheet_payload(current_image_data,current_frame_rows,SPRITE_EDITOR_DEFAULT_COLUMNS,current_source_bounds)
    current_frame_count=len(current_request_record['frames'])
    if any(type(current_value) not in (int,float) or not float(current_value).is_integer() for current_value in (current_first_frame,current_last_frame,current_playback_rate)):
        raise gr.Error('GIF 프레임 범위와 FPS는 정수여야 합니다.')
    current_first_index,current_last_index=int(current_first_frame)-1,int(current_last_frame)
    if not 0<=current_first_index<current_last_index<=current_frame_count:
        raise gr.Error(f'프레임 범위는 1~{current_frame_count} 안에서 시작이 끝보다 작거나 같아야 합니다.')
    current_request_record['frames']=current_request_record['frames'][current_first_index:current_last_index]
    if 'sourceFrames' in current_request_record:
        current_request_record['sourceFrames']=current_request_record['sourceFrames'][current_first_index:current_last_index]
    current_request_record['fps']=int(current_playback_rate)
    current_result_record=execute_remote_management_command('character-animation','sheet-gif',current_request_record)
    current_download_directory=Path(tempfile.mkdtemp(prefix='sprite-gif-download-'))
    current_gif_path=current_download_directory/'preview.gif'
    current_gif_path.write_bytes(base64.b64decode(current_result_record['gif'],validate=True))
    return str(current_gif_path),f"GIF 완료 · {current_result_record['frameCount']}프레임 · 프레임당 {current_result_record['durationMs']}ms · 작업 ID {current_result_record['id']}"


def detect_automatic_sprite_crops(current_image_data,current_padding_value):
    if not current_image_data:
        raise gr.Error('시트 불러오기를 먼저 실행하세요.')
    if current_padding_value is None or not float(current_padding_value).is_integer():
        raise gr.Error('여백은 정수여야 합니다.')
    current_image_bytes=base64.b64decode(current_image_data.split(',',1)[1],validate=True)
    if len(current_image_bytes)>SPRITE_EDITOR_UPLOAD_LIMIT:
        raise gr.Error('PNG 시트는 8MB 이하여야 합니다.')
    current_result_record=execute_remote_management_command('character-animation','sheet-auto',{'image':base64.b64encode(current_image_bytes).decode(),'padding':int(current_padding_value)})
    current_pending_record={'sha256':hashlib.sha256(current_image_bytes).hexdigest(),'padding':int(current_padding_value),'result':current_result_record}
    from PIL import ImageDraw
    with Image.open(BytesIO(current_image_bytes)) as current_source_image:
        current_overlay_image=current_source_image.convert('RGB')
    current_overlay_draw=ImageDraw.Draw(current_overlay_image)
    for current_frame_number,current_frame_record in enumerate(current_result_record['frames'],1):
        current_left_pixels,current_top_pixels=current_frame_record['x'],current_frame_record['y']
        current_overlay_draw.rectangle((current_left_pixels,current_top_pixels,current_left_pixels+current_frame_record['width']-1,current_top_pixels+current_frame_record['height']-1),outline='red',width=3)
        current_overlay_draw.text((max(0,current_left_pixels)+4,max(0,current_top_pixels)+4),str(current_frame_number),fill='red')
    return current_pending_record,current_overlay_image,gr.update(visible=True),f"{len(current_result_record['frames'])}프레임 검출 · 빨간 선은 여백 포함 크롭 후보입니다. 검수 시작을 누르면 현재 편집을 교체합니다. 아직 결과 이미지는 생성하지 않았습니다."


def apply_automatic_sprite_crops(current_pending_record,current_image_data,current_padding_value):
    if not current_image_data:
        raise gr.Error('시트 불러오기를 먼저 실행하세요.')
    current_image_bytes=base64.b64decode(current_image_data.split(',',1)[1],validate=True)
    if not current_pending_record or current_pending_record['padding']!=current_padding_value or hashlib.sha256(current_image_bytes).hexdigest()!=current_pending_record['sha256']:
        raise gr.Error('검출 이후 불러온 시트 또는 여백이 변경되었습니다. 자동 검출을 다시 실행하세요.')
    current_result_record=current_pending_record['result']
    current_frame_rows=[[current_frame_record[current_field_name] for current_field_name in SPRITE_EDITOR_FRAME_FIELDS] for current_frame_record in current_result_record['frames']]
    return current_image_data,current_frame_rows,current_result_record['columns'],gr.update(maximum=max(2,len(current_frame_rows)),value=1),'크롭라인을 불러왔습니다. 프레임별 검수·수정 후 이미지와 좌표맵 생성을 누르세요.',gr.update(interactive=True),current_result_record['sourceFrames'],{},gr.update(visible=False)


def prepare_sprite_sheet_update(current_asset_record,current_asset_choice,*current_editor_values):
    if not current_asset_record or current_asset_record.get('path')!=current_asset_choice or not current_asset_record.get('metadataSha256'):raise gr.Error('좌표맵이 하나 등록된 에셋을 검색해서 다시 가져오세요.')
    current_pending_record={'path':current_asset_record['path'],'metadataSha256':current_asset_record['metadataSha256'],'payload':build_sprite_sheet_payload(*current_editor_values),'confirm':True}
    current_original_frames=(current_asset_record.get('animation') or {}).get('frames',[])
    current_edited_frames=current_pending_record['payload']['frames']
    if len(current_original_frames)!=len(current_edited_frames):
        raise gr.Error('원본 업데이트는 기존 프레임 수를 유지해야 합니다. 다른 구성은 다운로드로 저장하세요.')
    current_changed_count=sum(any(current_original_frame['rect'][current_field_name]!=current_edited_frame[current_field_name] for current_field_name in ('x','y','width','height')) or current_original_frame['anchor']['x']!=current_edited_frame['anchorX'] or current_original_frame['anchor']['y']!=current_edited_frame['anchorY'] for current_original_frame,current_edited_frame in zip(current_original_frames,current_edited_frames))
    current_change_summary=f'\n\n좌표 변경: **{current_changed_count} / {len(current_edited_frames)}프레임** · 출력 {current_pending_record["payload"]["columns"]}열. 저장 시 시트 이미지를 재배치합니다.'
    if current_asset_record.get('source')=='baseline':
        current_pending_record['source']='baseline'
        return current_pending_record,gr.update(visible=True),f"**베이스라인 갱신 대상:** {current_asset_record['path']}\n\n이미지·좌표맵·YAML 크기와 해시를 갱신합니다. 프레임 ID와 동작 구분을 유지하고 변경 전 사본을 보관합니다."+current_change_summary
    return current_pending_record,gr.update(visible=True),f"**갱신 대상:** {current_asset_record['path']}\n\n기존 이미지와 애니메이션 좌표맵·등록부·잠금 해시를 갱신합니다. 프레임 ID와 재생 클립은 유지하고 변경 전 사본을 보관합니다."+current_change_summary


def confirm_sprite_sheet_update(current_pending_record,current_asset_record,current_asset_choice,*current_editor_values):
    current_comparison_record,_,_=prepare_sprite_sheet_update(current_asset_record,current_asset_choice,*current_editor_values)
    if current_pending_record!=current_comparison_record:raise gr.Error('확인 이후 대상 또는 편집값이 변경되었습니다. 다시 확인하세요.')
    current_result_record=execute_remote_management_command('character-animation','sheet-update',current_pending_record)
    return {},gr.update(visible=False),f"원본 갱신 완료 · {current_result_record['path']} · 기록 {current_result_record['id']} · 추가 편집 전 다시 불러오세요."


def update_and_reload_sprite_sheet(current_pending_record,current_asset_record,current_asset_choice,*current_editor_values):
    """저장 성공 후 새 좌표·해시로 편집 원본을 갱신한다."""
    current_update_values=confirm_sprite_sheet_update(current_pending_record,current_asset_record,current_asset_choice,*current_editor_values)
    try:
        current_loaded_values=list(prepare_registered_sprite_load(current_asset_choice,current_asset_record.get('source','assets'),''))
    except Exception as current_reload_error:
        # 저장 자체는 성공했다. 오래된 해시로 재저장하지 않도록 차단한다.
        current_loaded_values=[gr.update() for current_output_index in range(18)]
        current_loaded_values[4]=current_update_values[2]+f' 최신 원본 재조회 실패: {current_reload_error}'
        current_loaded_values[13]={**current_asset_record,'metadataSha256':None}
        return (*current_loaded_values,{},gr.update(visible=False))
    current_loaded_values[4]=current_update_values[2].replace('추가 편집 전 다시 불러오세요.','최신 원본을 다시 불러왔습니다. 계속 편집할 수 있습니다.')
    return (*current_loaded_values,{},gr.update(visible=False))


def save_sprite_anchor_history(current_source_record,current_frame_rows):
    """현재 시트의 앵커만 공용 이력으로 저장하고 원본은 변경하지 않는다."""
    from tools.review.domains.character_animation.anchor_history import validate_anchor_document
    current_animation_record=current_source_record.get('animation') or {}
    current_original_frames=current_animation_record.get('frames',[])
    if not current_animation_record.get('animationId') or not current_animation_record.get('version'):
        raise gr.Error('등록된 애니메이션 식별자가 필요합니다. 직접 PNG는 좌표맵을 다운로드하세요.')
    if len(current_original_frames)!=len(current_frame_rows):raise gr.Error('원본 프레임 구성과 다릅니다.')
    current_image_name=Path(current_source_record['path']).name
    current_history_frames=[]
    for current_original_frame,current_frame_row in zip(current_original_frames,current_frame_rows):
        current_original_rect=current_original_frame['rect']
        if list(current_frame_row[:4])!=[current_original_rect[current_field_name] for current_field_name in ('x','y','width','height')]:
            raise gr.Error('크롭 변경을 먼저 원본 업데이트로 저장한 뒤 앵커 이력을 저장하세요.')
        current_direction_name=current_original_frame.get('direction')
        if not current_direction_name:
            current_direction_names={current_clip_record.get('direction') for current_clip_record in current_animation_record.get('clips',[]) if any(current_clip_frame['frameId']==current_original_frame['frameId'] for current_clip_frame in current_clip_record['frames'])}
            if len(current_direction_names)!=1:raise gr.Error('프레임의 등록 방향을 확정할 수 없습니다.')
            current_direction_name=current_direction_names.pop()
        current_anchor_point={'x':float(current_frame_row[4]),'y':float(current_frame_row[5])}
        current_history_frames.append({'frameId':current_original_frame['frameId'],'direction':current_direction_name,'image':current_image_name,'rect':current_original_rect,'points':[current_anchor_point],'anchor':current_anchor_point})
    current_history_document={'schemaVersion':1,'artifactType':'character-animation-anchor-review','description':'스프라이트 시트 편집기에서 저장한 현재 시트 앵커','coordinateMode':'anchor','source':{'animationId':current_animation_record['animationId'],'animationVersion':current_animation_record['version'],'sheets':[{'image':current_image_name,'sha256':current_source_record['imageSha256']}]},'frames':current_history_frames}
    validate_anchor_document(current_history_document)
    current_saved_record=execute_remote_management_command('character-animation','anchor-save',{'document':current_history_document})
    return list_sprite_anchor_history(current_source_record),'앵커 이력 저장 완료 · 원본 이미지는 변경하지 않았습니다. '+str(current_saved_record.get('id',''))


def list_sprite_anchor_history(current_source_record):
    """현재 등록 버전의 공용 좌표 이력을 조회한다."""
    current_animation_record=current_source_record.get('animation') or {}
    if not current_animation_record.get('animationId') or not current_animation_record.get('version'):
        return gr.update(choices=[],value=None,interactive=False)
    current_history_result=execute_remote_management_command('character-animation','anchor-history',{'animation_id':current_animation_record['animationId'],'animation_version':current_animation_record['version']})
    return gr.update(choices=[(current_history_item['id'],current_history_item['id']) for current_history_item in current_history_result['items']],value=None,interactive=bool(current_history_result['items']))


def prepare_sprite_anchor_restore(current_history_identifier,current_source_record,current_frame_rows):
    """이미지와 원본 프레임이 일치하는 이력을 검수 후보로 준비한다."""
    if not current_history_identifier:raise gr.Error('복원할 좌표 이력을 선택하세요.')
    current_history_document=execute_remote_management_command('character-animation','anchor-load',{'id':current_history_identifier})['document']
    current_animation_record=current_source_record.get('animation') or {}
    current_history_source=current_history_document['source']
    if current_history_document['coordinateMode'] not in ('anchor','foot-centers','endpoints') or current_history_source['animationId']!=current_animation_record.get('animationId') or current_history_source['animationVersion']!=current_animation_record.get('version'):
        raise gr.Error('현재 시트의 애니메이션·버전 또는 지원 좌표 모드와 일치하지 않습니다.')
    current_matching_images={current_sheet_record['image'] for current_sheet_record in current_history_source['sheets'] if current_sheet_record['sha256']==current_source_record.get('imageSha256')}
    current_history_frames={current_frame_record['frameId']:current_frame_record for current_frame_record in current_history_document['frames'] if current_frame_record['image'] in current_matching_images}
    current_original_frames=current_animation_record.get('frames',[])
    if not current_original_frames or len(current_history_frames)!=len(current_original_frames):raise gr.Error('현재 이미지 해시 또는 프레임 구성이 이력과 다릅니다.')
    current_restored_rows=[]
    current_restored_feet={}
    for current_original_frame in current_original_frames:
        current_history_frame=current_history_frames.get(current_original_frame['frameId'])
        if not current_history_frame or current_history_frame['rect']!=current_original_frame['rect']:raise gr.Error('현재 프레임 영역과 이력이 다릅니다.')
        current_coordinate_mode=current_history_document['coordinateMode']
        if current_coordinate_mode!='anchor':
            current_point_records=current_history_frame['points']
            current_restored_feet[str(len(current_restored_rows))]=current_point_records if current_coordinate_mode=='foot-centers' else [{'x':(current_point_records[current_point_index]['x']+current_point_records[current_point_index+1]['x'])/2,'y':(current_point_records[current_point_index]['y']+current_point_records[current_point_index+1]['y'])/2} for current_point_index in (0,2)]
        current_frame_rect=current_history_frame['rect'];current_frame_anchor=current_history_frame['anchor']
        current_restored_rows.append([current_frame_rect[current_field_name] for current_field_name in ('x','y','width','height')]+[current_frame_anchor['x'],current_frame_anchor['y']])
    return {'source':current_source_record,'before':current_frame_rows,'rows':current_restored_rows,'feet':current_restored_feet},gr.update(visible=True)


def confirm_sprite_anchor_restore(current_pending_restore,current_source_record,current_frame_rows):
    if not current_pending_restore or current_pending_restore['source']!=current_source_record or current_pending_restore['before']!=current_frame_rows:
        raise gr.Error('복원 확인 중 원본 또는 편집이 변경되었습니다. 이력을 다시 선택하세요.')
    return current_pending_restore['rows'],{},gr.update(visible=False),'좌표 이력을 편집 상태로 불러왔습니다. 원본 업데이트 전까지 저장되지 않습니다.',current_pending_restore['feet']


def load_linked_sprite_sheet(request: gr.Request):
    """편집기 직접 링크의 등록 원본만 초기 진입 시 불러온다."""
    current_query_values=request.query_params
    current_source_path=current_query_values.get('sprite_path')
    current_action_identifier=current_query_values.get('action','')
    if not current_source_path and current_action_identifier:
        if not current_action_identifier.startswith('asset:'):raise gr.Error('지원하지 않는 애니메이션 링크입니다.')
        current_animation_identifier=current_action_identifier.removeprefix('asset:')
        current_search_result=execute_remote_management_command('character-animation','sheet-search',{'query':current_animation_identifier,'source':'assets'})
        current_matching_paths=[current_item_record['path'] for current_item_record in current_search_result['items'] if current_animation_identifier in current_item_record.get('animationIds',[])]
        if len(current_matching_paths)!=1:raise gr.Error('연결된 시트가 없거나 여러 개입니다. 에셋 검색에서 동작 ID로 검색하여 시트를 선택하세요: '+current_animation_identifier)
        current_source_path=current_matching_paths[0]
    if not current_source_path:return tuple(gr.update() for current_output_index in range(18))
    current_source_kind=current_query_values.get('sprite_source','assets')
    if current_source_kind not in ('assets','baseline'):raise gr.Error('지원하지 않는 링크 원본입니다.')
    return prepare_registered_sprite_load(current_source_path,current_source_kind,'')


def build_sprite_sheet_editor_interface(current_review_port):
    current_preview_script=Path(__file__).with_name('sprite_sheet_editor_preview.js').read_text()
    current_canvas_apply_script=Path(__file__).with_name('sprite_sheet_canvas_apply.js').read_text()
    current_bulk_script=Path(__file__).with_name('sprite_sheet_bulk_edit.js').read_text()
    current_clip_select_script=Path(__file__).with_name('sprite_sheet_clip_select.js').read_text()
    with gr.Blocks(title='스프라이트 시트 편집기') as current_interface_blocks:
        gr.Markdown('## 스프라이트 시트 편집기\n원본 불러오기 → 크롭·앵커 편집 → 재생 검수 → 결과 저장')
        with gr.Accordion('1. 원본 검색 · 불러오기',open=True) as current_source_group:
            current_source_kind=gr.Radio(choices=[('에셋 스프라이트','assets'),('베이스라인 스프라이트','baseline')],value='assets',label='검색 원본')
            gr.Markdown('에셋은 게임 등록 원본, 베이스라인은 제작 기준입니다. 베이스라인도 편집 후 원본 업데이트로 저장할 수 있습니다. 검색어 없이 검색하면 전체 목록을 표시합니다. 여러 단어를 띄어쓰기로 조합하거나 Enter로 검색하세요.')
            with gr.Row():
                current_search_text=gr.Textbox(label='스프라이트 검색',placeholder='이름 · ID · 경로 (예: rest, 휴식)',scale=4,lines=1)
                current_search_button=gr.Button('스프라이트 검색',scale=1)
            current_search_status=gr.Markdown('검색어 없이 검색하면 전체 목록을 표시합니다.')
            with gr.Row():
                current_asset_choice=gr.Dropdown(label='검색 결과 · 원본 선택',choices=[],scale=4)
                current_select_button=gr.Button('선택 시트 불러오기',scale=1)
            current_asset_record=gr.State({})
            current_loaded_path=gr.State('')
            current_pending_update=gr.State({})
            with gr.Accordion('직접 PNG · 원본 행·열 설정',open=False):
                current_input_file=gr.File(label='원본 PNG',file_types=['.png'],type='filepath')
                with gr.Row():
                    current_input_columns=gr.Number(label='원본 열',value=4,precision=0)
                    current_input_rows=gr.Number(label='원본 행',value=2,precision=0)
                    current_load_button=gr.Button('시트 불러오기')
            with gr.Group(visible=False) as current_confirm_group:
                current_confirm_summary=gr.Markdown('기존 편집 내용을 새 시트로 바꿉니다. 저장하지 않은 변경은 사라집니다.')
                with gr.Row():
                    current_confirm_button=gr.Button('불러오기 확인')
                    current_cancel_button=gr.Button('취소')
            gr.Markdown('미등록 PNG는 원본 열·행으로 전체 영역을 균등 분할합니다. 나누어떨어지지 않는 픽셀은 분산하며 자동 크롭하지 않습니다.')
        current_loaded_summary=gr.Markdown('**현재 편집 원본:** 아직 불러온 시트가 없습니다.')
        with gr.Row():
            with gr.Column(scale=2,min_width=SPRITE_EDITOR_PREVIEW_MIN_WIDTH):
                current_canvas_target=gr.Radio(['전체','현재 프레임','선택 프레임'],value='전체',label='캔버스 편집 적용 대상')
                gr.Markdown('### 2. 편집·재생 검수\n대상 선택 → 드래그 → 편집 반영. 전체는 프레임별 앵커 차이를 유지합니다.')
                current_canvas_selection=gr.Dropdown(choices=[str(current_frame_number) for current_frame_number in range(1,129)],multiselect=True,label='선택 프레임 번호',visible=False)
                current_canvas_mode=gr.Radio(['크롭','앵커'],value='크롭',label='캔버스 편집 도구')
                with gr.Accordion('크롭·앵커 조작 안내',open=False):
                    gr.Markdown('회색 영역은 이미지 바깥입니다. 크롭을 바깥으로 드래그하면 투명 여백을 확장합니다. 큰 확장은 고급 좌표 설정의 음수 여백을 사용하세요. 앵커는 클릭하거나 드래그하세요. 크롭으로 앵커가 영역 밖이 되면 가장 가까운 내부 경계로 이동합니다. 선택·전체 프레임에는 같은 크롭 여백과 앵커 이동량을 적용하며 기존 프레임별 앵커 차이를 유지합니다. 드래그는 현재 프레임의 미리보기만 변경합니다. 선택한 대상에 편집 반영을 눌러 선택한 범위에 반영하세요.')
                gr.HTML('<canvas id="sprite-sheet-alignment-preview" width="640" height="640" style="width:100%;max-width:640px;aspect-ratio:1;background:#fff;touch-action:none" aria-label="프레임 크롭과 앵커 정렬 미리보기"></canvas>')
                with gr.Row():
                    current_frame_index=gr.Slider(label='프레임',minimum=1,maximum=2,value=1,step=1)
                    current_play_enabled=gr.Checkbox(label='재생 상태',value=False,visible=False)
                    current_play_button=gr.Button('재생',interactive=False)
                    current_stop_button=gr.Button('정지',interactive=False)
                current_preview_clip=gr.Dropdown(label='검수 동작 · 방향',choices=[('현재 시트 전체','')],value='',interactive=False)
                gr.Markdown('동작·방향 선택은 재생 범위만 변경합니다. 편집 적용 대상 전체는 현재 시트의 모든 프레임입니다.')
                current_playback_rate=gr.Dropdown(label='검수 재생 속도 (FPS)',choices=[4,6,8,12,16,24,30],value=6,interactive=True)
                with gr.Row():
                    current_canvas_apply=gr.Button('선택한 대상에 편집 반영',variant='primary',interactive=False)
                    current_canvas_undo=gr.Button('직전 반영 되돌리기',interactive=False)
                    current_canvas_discard=gr.Button('드래그 취소',interactive=False)
                current_canvas_status=gr.Textbox(label='캔버스 편집 상태',value='대상을 선택하고 드래그한 뒤 편집 반영을 누르세요. 에셋 저장은 별도입니다.',interactive=False)
                gr.Markdown('등록 에셋과 베이스라인은 원본 업데이트로 저장하세요. 직접 첨부 이미지는 이미지와 좌표맵 생성으로 내려받으세요. 다운로드는 원본을 바꾸지 않습니다.')
                with gr.Accordion('검수 오버레이 · 출력 제외',open=False):
                    current_feet_enabled=gr.Checkbox(label='등록된 양발 중심 표시',value=False)
                    current_shadow_enabled=gr.Checkbox(label='바닥 그림자 표시',value=False)
                    current_baseline_enabled=gr.Checkbox(label='앵커 높이 기준선',value=True)
                    current_onion_enabled=gr.Checkbox(label='이전 프레임 겹쳐보기',value=False)
                    gr.Markdown('이전 프레임은 동일한 화면 앵커·배율로 표시합니다. 첫 프레임에는 이전 프레임을 표시하지 않습니다.')
                with gr.Accordion('게임 출력 크기 검수 · 출력 제외',open=False):
                    current_game_size_enabled=gr.Checkbox(label='게임 픽셀 크기로 표시',value=False)
                    current_reference_height=gr.Number(label='원본 캐릭터 신체 높이 (px)',value=None,minimum=1)
                    current_game_body_height=gr.Number(label='게임 출력 신체 높이 (px)',value=None,minimum=1)
                    gr.Markdown('원본 신체 높이는 여백을 제외한 서 있는 캐릭터 높이입니다. 게임 출력 높이 ÷ 원본 신체 높이의 고정 배율로 모든 프레임을 표시합니다. 등록된 referenceBodyHeight·gameBodyHeight가 있으면 자동 입력합니다. 캔버스 표시 크기에 따른 화면 축소는 별도입니다.')
                current_preview_status=gr.Textbox(label='미리보기',interactive=False)
            with gr.Column(scale=1,min_width=SPRITE_EDITOR_SETTINGS_MIN_WIDTH):
                gr.Markdown('### 3. 편집 설정')
                with gr.Accordion('자동 크롭 · 선택 사항',open=False):
                    gr.Markdown('### 크롭 범위 찾기 → 검수\n흰색·투명 배경에서 행·열과 캐릭터 영역을 찾습니다. 여백을 포함한 크롭라인을 검수하고 수정한 뒤 이미지를 생성하세요. 가로 크기는 전체 프레임의 최대 너비로 통일하고, 세로 크기는 각 행의 최대 높이로 맞춥니다. 같은 행의 프레임 높이와 모든 열의 너비가 같습니다. 캐릭터는 확대·축소하지 않고 가로 중앙·하단 기준으로 정렬합니다. 서로 붙거나 떨어진 신체 부위는 검출 오류가 생길 수 있습니다.')
                    current_auto_padding=gr.Number(label='상하좌우 최소 여백 (px)',value=30,precision=0,minimum=0,maximum=500)
                    current_auto_button=gr.Button('자동 크롭 범위 찾기',interactive=False)
                    gr.Markdown('먼저 시트 불러오기를 실행하세요. 자동 크롭은 현재 불러온 이미지에 적용됩니다.')
                    current_auto_pending=gr.State({})
                    current_auto_preview=gr.Image(label='크롭 후보 검수 · 빨간 선 · 원본 밖 여백은 프레임 캔버스에서 확인',interactive=False)
                    with gr.Group(visible=False) as current_auto_confirm:
                        gr.Markdown('검수 시작은 현재 편집을 검출한 크롭라인으로 교체합니다. 저장하지 않은 편집을 확인하세요. 결과 파일은 생성하지 않습니다.')
                        with gr.Row():
                            current_auto_apply=gr.Button('크롭라인 검수 시작')
                            current_auto_cancel=gr.Button('검출 취소')
                current_image_data=gr.Textbox(value='',visible=False)
                current_pending_load=gr.State({})
                current_source_bounds=gr.JSON(value=[],visible=False)
                with gr.Accordion('고급 좌표 설정',open=False):
                    current_frame_rows=gr.Dataframe(headers=['x','y','width','height','anchorX','anchorY'],datatype=['number']*6,row_count=(1,'dynamic'),col_count=(6,'fixed'),label='프레임별 원본 크롭과 앵커',type='array')
                    with gr.Accordion('숫자로 일괄 적용',open=False):
                        current_bulk_target=gr.Radio(['전체','지정 프레임'],value='전체',label='적용 대상')
                        current_bulk_selection=gr.Textbox(label='프레임 번호 (1부터)',placeholder='예: 1,3-5')
                        current_bulk_mode=gr.Radio(['크롭','앵커'],value='크롭',label='편집 종류')
                        gr.Markdown('양수 여백은 크롭, 음수 여백은 투명 영역 확장입니다. 원본 셀 밖의 인접 이미지는 포함하지 않고 앵커 위치를 보존합니다. 숫자 앵커는 선택 범위에 동일 좌표를 지정합니다. 프레임 간 차이를 유지한 상대 이동은 캔버스 앵커 드래그를 사용하세요. 프레임 전환 시 현재 앵커 좌표가 자동 입력됩니다. 범위 오류가 있으면 전체 적용을 취소합니다.')
                        with gr.Row():
                            current_bulk_left=gr.Number(label='왼쪽 여백',value=0,precision=0)
                            current_bulk_top=gr.Number(label='위쪽 여백',value=0,precision=0)
                            current_bulk_right=gr.Number(label='오른쪽 여백',value=0,precision=0)
                            current_bulk_bottom=gr.Number(label='아래쪽 여백',value=0,precision=0)
                        with gr.Row():
                            current_bulk_anchor_x=gr.Number(label='동일 좌표 지정 · 앵커 X',value=0)
                            current_bulk_anchor_y=gr.Number(label='동일 좌표 지정 · 앵커 Y',value=0)
                        current_bulk_apply=gr.Button('일괄 적용')
        gr.Markdown('### 4. 결과 저장\n다운로드용 파일 생성과 등록 에셋 업데이트 중 선택하세요.')
        with gr.Row():
            current_output_columns=gr.Number(label='출력 열',value=SPRITE_EDITOR_DEFAULT_COLUMNS,precision=0)
        current_export_button=gr.Button('이미지와 좌표맵 생성',variant='primary',interactive=False)
        gr.Markdown('생성 버튼은 원본 PNG를 불러온 뒤 사용할 수 있습니다.')
        with gr.Accordion('GIF 애니메이션 검수',open=False):
            gr.Markdown('편집 반영된 크롭과 앵커를 사용합니다. 프레임 범위는 시트 번호이며 흰 배경·반복 재생입니다. GIF 시간 해상도로 실제 속도는 선택 FPS와 약간 다를 수 있습니다. 먼저 시트를 불러오세요.')
            with gr.Row():
                current_gif_first=gr.Number(label='시작 프레임',value=1,precision=0,minimum=1)
                current_gif_last=gr.Number(label='끝 프레임',value=1,precision=0,minimum=1)
            current_gif_button=gr.Button('GIF 생성',interactive=False)
            current_gif_output=gr.File(label='GIF 다운로드',interactive=False)
        current_update_button=gr.Button('원본 업데이트',interactive=False)
        with gr.Group(visible=False) as current_update_group:
            current_update_summary=gr.Markdown()
            with gr.Row():
                current_update_confirm=gr.Button('업데이트 확인')
                current_update_cancel=gr.Button('업데이트 취소')
        with gr.Accordion('앵커 이력 저장 · 복원',open=False):
            gr.Markdown('현재 이미지·등록 버전에 일치하는 앵커 이력을 불러옵니다. 복원은 현재 크롭·앵커 편집을 교체하며 원본 저장은 별도입니다.')
            current_history_save=gr.Button('현재 앵커를 이력으로 저장')
            current_history_choice=gr.Dropdown(label='좌표 이력',choices=[],interactive=False)
            current_history_prepare=gr.Button('선택 이력 복원 준비')
            current_history_pending=gr.State({})
            current_restored_feet=gr.State({})
            with gr.Group(visible=False) as current_history_group:
                gr.Markdown('현재 편집을 선택 이력으로 교체합니다. 계속하려면 복원을 확인하세요.')
                current_history_confirm=gr.Button('복원 확인')
                current_history_cancel=gr.Button('복원 취소')
        current_output_files=gr.File(label='결과 다운로드',file_count='multiple',interactive=False)
        current_status_text=gr.Textbox(label='상태',interactive=False)
        current_image_data.change(lambda current_loaded_image:gr.update(interactive=bool(current_loaded_image)),current_image_data,current_auto_button,queue=False)
        current_image_data.change(lambda current_loaded_image:gr.update(interactive=bool(current_loaded_image)),current_image_data,current_gif_button,queue=False)
        current_frame_rows.change(lambda current_rows:len(current_rows) if current_rows is not None else 1,current_frame_rows,current_gif_last,queue=False)
        current_gif_button.click(export_sprite_gif_result,[current_image_data,current_frame_rows,current_source_bounds,current_playback_rate,current_gif_first,current_gif_last],[current_gif_output,current_status_text],trigger_mode='once')
        current_image_data.change(lambda current_loaded_image: [gr.update(interactive=bool(current_loaded_image)) for current_control_index in range(5)],current_image_data,[current_play_button,current_stop_button,current_canvas_apply,current_canvas_undo,current_canvas_discard],queue=False)
        current_auto_button.click(detect_automatic_sprite_crops,[current_image_data,current_auto_padding],[current_auto_pending,current_auto_preview,current_auto_confirm,current_status_text],trigger_mode='once')
        current_auto_cancel.click(lambda:({},gr.update(visible=False),'자동 검출을 취소했습니다. 기존 편집은 유지됩니다.'),outputs=[current_auto_pending,current_auto_confirm,current_status_text],queue=False)
        current_search_button.click(search_sprite_asset_choices,[current_search_text,current_source_kind],[current_asset_choice,current_search_status])
        current_search_text.submit(search_sprite_asset_choices,[current_search_text,current_source_kind],[current_asset_choice,current_search_status])
        current_source_kind.change(search_sprite_asset_choices,[current_search_text,current_source_kind],[current_asset_choice,current_search_status])
        current_asset_record.change(build_sprite_clip_choices,current_asset_record,current_preview_clip,queue=False)
        current_asset_record.change(lambda current_source_value: ((current_source_value.get('runtimeDimensions') or current_source_value.get('animation') or {}).get('referenceBodyHeight'),(current_source_value.get('runtimeDimensions') or current_source_value.get('animation') or {}).get('gameBodyHeight')),current_asset_record,[current_reference_height,current_game_body_height],queue=False)
        current_asset_record.change(list_sprite_anchor_history,current_asset_record,current_history_choice)
        current_history_save.click(save_sprite_anchor_history,[current_asset_record,current_frame_rows],[current_history_choice,current_status_text],trigger_mode='once')
        current_history_prepare.click(prepare_sprite_anchor_restore,[current_history_choice,current_asset_record,current_frame_rows],[current_history_pending,current_history_group])
        current_history_cancel.click(lambda:({},gr.update(visible=False)),outputs=[current_history_pending,current_history_group],queue=False)
        current_update_inputs=[current_asset_record,current_loaded_path,current_image_data,current_frame_rows,current_output_columns,current_source_bounds]
        current_asset_record.change(lambda current_loaded_record: gr.update(interactive=bool(current_loaded_record.get('metadataSha256'))),current_asset_record,current_update_button)
        current_update_button.click(prepare_sprite_sheet_update,current_update_inputs,[current_pending_update,current_update_group,current_update_summary])
        current_update_cancel.click(lambda:({},gr.update(visible=False)),outputs=[current_pending_update,current_update_group],queue=False)
        current_canvas_target.change(lambda current_target_mode:gr.update(visible=current_target_mode=='선택 프레임'),current_canvas_target,current_canvas_selection,queue=False)
        current_anchor_sync_script="(currentFrameRows,currentFrameIndex)=>{const currentRows=Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data;const currentFrameRow=currentRows?.[Number(currentFrameIndex)-1];return currentFrameRow?[Number(currentFrameRow[4]),Number(currentFrameRow[5])]:[0,0];}"
        for current_coordinate_component in (current_frame_index,current_frame_rows):
            current_coordinate_component.change(fn=None,inputs=[current_frame_rows,current_frame_index],outputs=[current_bulk_anchor_x,current_bulk_anchor_y],js=current_anchor_sync_script,queue=False)
        current_preview_inputs=[current_image_data,current_frame_rows,current_frame_index,current_play_enabled,current_shadow_enabled,current_canvas_mode,current_source_bounds,current_playback_rate,current_baseline_enabled,current_onion_enabled,current_preview_clip,current_asset_record,current_game_size_enabled,current_reference_height,current_game_body_height,current_feet_enabled,current_restored_feet]
        current_history_confirm.click(confirm_sprite_anchor_restore,[current_history_pending,current_asset_record,current_frame_rows],[current_frame_rows,current_history_pending,current_history_group,current_status_text,current_restored_feet]).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_image_data.change(lambda:{},outputs=current_restored_feet,queue=False)
        current_preview_clip.input(fn=None,inputs=[current_preview_clip,current_asset_record,current_frame_index],outputs=[current_play_enabled,current_frame_index],js=current_clip_select_script,queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_play_button.click(fn=None,inputs=[],outputs=current_play_enabled,js='()=>true',queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_stop_button.click(fn=None,inputs=current_frame_index,outputs=[current_play_enabled,current_frame_index],js="(currentFrameIndex)=>[false,(document.getElementById('sprite-sheet-alignment-preview')?.spriteEditorState?.displayedIndex??(Number(currentFrameIndex)-1))+1]",queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        for current_action_button,current_action_name in ((current_canvas_apply,'apply'),(current_canvas_undo,'undo'),(current_canvas_discard,'discard')):
            current_action_button.click(fn=None,inputs=[current_frame_rows,current_canvas_target,current_canvas_selection],outputs=[current_frame_rows,current_canvas_status],js='(...currentArguments)=>('+current_canvas_apply_script+')( ...currentArguments, '+json.dumps(current_action_name)+')',queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_bulk_apply.click(fn=None,inputs=[current_frame_rows,current_bulk_target,current_bulk_selection,current_bulk_mode,current_bulk_left,current_bulk_top,current_bulk_right,current_bulk_bottom,current_bulk_anchor_x,current_bulk_anchor_y],outputs=[current_frame_rows,current_status_text],js=current_bulk_script,queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_auto_apply.click(apply_automatic_sprite_crops,[current_auto_pending,current_image_data,current_auto_padding],[current_image_data,current_frame_rows,current_output_columns,current_frame_index,current_status_text,current_export_button,current_source_bounds,current_auto_pending,current_auto_confirm],trigger_mode='once').then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_load_outputs=[current_image_data,current_frame_rows,current_output_columns,current_frame_index,current_status_text,
                              current_confirm_group,current_pending_load,current_export_button,current_source_bounds,current_auto_pending,
                              current_auto_preview,current_auto_confirm,current_output_files,current_asset_record,current_loaded_path,
                              current_loaded_summary,current_source_group,current_play_enabled]
        current_interface_blocks.load(load_linked_sprite_sheet,outputs=current_load_outputs).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_update_confirm.click(update_and_reload_sprite_sheet,[current_pending_update,*current_update_inputs],[*current_load_outputs,current_pending_update,current_update_group],trigger_mode='once').then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_select_button.click(prepare_registered_sprite_load,[current_asset_choice,current_source_kind,current_image_data],current_load_outputs,trigger_mode='once').then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_load_button.click(prepare_uploaded_sprite_load,[current_input_file,current_input_columns,current_input_rows,current_image_data],current_load_outputs,trigger_mode='once').then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_confirm_button.click(confirm_selected_sprite_load,[current_pending_load,current_asset_choice,current_source_kind,current_input_file,current_input_columns,current_input_rows],current_load_outputs,trigger_mode='once').then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_pending_load.change(lambda current_candidate_record: '기존 편집을 교체합니다. 저장하지 않은 변경은 사라집니다.\n\n**새 원본:** '+str(current_candidate_record.get('asset',{}).get('path',current_candidate_record.get('path',''))),current_pending_load,current_confirm_summary)
        current_cancel_button.click(lambda:(gr.update(visible=False),{},'불러오기를 취소했습니다. 기존 편집 내용이 유지됩니다.'),outputs=[current_confirm_group,current_pending_load,current_status_text],queue=False)
        for current_input_component in [*current_preview_inputs[1:6],current_playback_rate,current_baseline_enabled,current_onion_enabled,current_game_size_enabled,current_reference_height,current_game_body_height,current_feet_enabled]:current_input_component.input(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_export_button.click(export_sprite_sheet_result,[current_image_data,current_frame_rows,current_output_columns,current_source_bounds],[current_output_files,current_status_text],trigger_mode='once')
    return current_interface_blocks
