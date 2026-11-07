"""프레임 크롭과 공통 앵커를 검수하는 스프라이트 시트 클라이언트."""
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
import tempfile
import gradio as gr
from PIL import Image
from tools.review.common.management_client import execute_remote_management_command

SPRITE_EDITOR_FRAME_FIELDS = ('x','y','width','height','anchorX','anchorY')
SPRITE_EDITOR_UPLOAD_LIMIT = 8_000_000
SPRITE_EDITOR_DEFAULT_COLUMNS = 4


def search_sprite_asset_choices(current_search_text):
    current_result_record=execute_remote_management_command('character-animation','sheet-search',{'query':current_search_text or ''})
    return gr.update(choices=[(current_asset_record['label']+' · '+current_asset_record['path'],current_asset_record['path']) for current_asset_record in current_result_record['items']],value=None),f"{len(current_result_record['items'])}개 스프라이트를 찾았습니다. 선택 후 원본으로 가져오세요."


def select_sprite_asset_image(current_asset_path):
    if not current_asset_path:raise gr.Error('검색 결과에서 스프라이트를 선택하세요.')
    try:
        current_result_record=execute_remote_management_command('character-animation','sheet-image',{'path':current_asset_path})
    except ValueError as current_load_error:
        raise gr.Error(f'스프라이트를 가져오지 못했습니다: {current_load_error}') from current_load_error
    current_temporary_directory=Path(tempfile.mkdtemp(prefix='sprite-asset-input-'))
    current_image_path=current_temporary_directory/Path(current_asset_path).name
    current_image_path.write_bytes(base64.b64decode(current_result_record['image'],validate=True))
    if current_result_record.get('animation'):
        current_image_path.with_suffix('.animation.json').write_text(json.dumps(current_result_record['animation']))
    return str(current_image_path),{'path':current_asset_path,'metadataSha256':current_result_record['metadataSha256'],'animation':current_result_record.get('animation'),'imageSha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest()},'원본으로 가져왔습니다. 원본 열·행을 지정하고 시트 불러오기를 누르세요. 기존 편집은 아직 변경하지 않았습니다.'


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
        return (*([gr.update()]*4),'현재 편집 내용이 바뀝니다. 아래에서 확인하거나 취소하세요.',gr.update(visible=True),current_pending_load,gr.update(),gr.update())
    current_loaded_values=load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record)
    return (*current_loaded_values,gr.update(visible=False),{},gr.update(interactive=True),[current_frame_row[:4] for current_frame_row in current_loaded_values[1]])


def confirm_sprite_sheet_load(current_pending_load,current_file_path,current_columns_value,current_rows_value,current_asset_record):
    if current_pending_load!={'path':current_file_path,'columns':current_columns_value,'rows':current_rows_value,'asset':current_asset_record}:raise gr.Error('확인 후 입력이 변경되었습니다. 다시 불러오세요.')
    current_loaded_values=load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record)
    return (*current_loaded_values,gr.update(visible=False),{},gr.update(interactive=True),[current_frame_row[:4] for current_frame_row in current_loaded_values[1]])


def build_sprite_sheet_payload(current_image_data,current_frame_rows,current_columns_value,current_source_bounds=None):
    if not current_image_data:raise gr.Error('시트를 먼저 불러오세요.')
    current_values=[current_columns_value]
    if any(type(current_value) not in (int,float) or not float(current_value).is_integer() for current_value in current_values):raise gr.Error('출력 설정은 정수여야 합니다.')
    current_rows=current_frame_rows.values.tolist() if hasattr(current_frame_rows,'values') else current_frame_rows
    current_frames=[]
    for current_frame_row in current_rows:
        if len(current_frame_row)!=6 or any(type(current_value) not in (int,float) or not float(current_value).is_integer() for current_value in current_frame_row):raise gr.Error('프레임 좌표는 모두 정수여야 합니다.')
        current_frames.append(dict(zip(SPRITE_EDITOR_FRAME_FIELDS,map(int,current_frame_row))))
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


def prepare_sprite_sheet_update(current_asset_record,current_asset_choice,*current_editor_values):
    if not current_asset_record or current_asset_record.get('path')!=current_asset_choice or not current_asset_record.get('metadataSha256'):raise gr.Error('좌표맵이 하나 등록된 에셋을 검색해서 다시 가져오세요.')
    current_pending_record={'path':current_asset_record['path'],'metadataSha256':current_asset_record['metadataSha256'],'payload':build_sprite_sheet_payload(*current_editor_values),'confirm':True}
    return current_pending_record,gr.update(visible=True),f"**갱신 대상:** {current_asset_record['path']}\n\n기존 이미지와 애니메이션 좌표맵·등록부·잠금 해시를 갱신합니다. 프레임 ID와 재생 클립은 유지하고 변경 전 사본을 보관합니다."


def confirm_sprite_sheet_update(current_pending_record,current_asset_record,current_asset_choice,*current_editor_values):
    current_comparison_record,_,_=prepare_sprite_sheet_update(current_asset_record,current_asset_choice,*current_editor_values)
    if current_pending_record!=current_comparison_record:raise gr.Error('확인 이후 대상 또는 편집값이 변경되었습니다. 다시 확인하세요.')
    current_result_record=execute_remote_management_command('character-animation','sheet-update',current_pending_record)
    return {},gr.update(visible=False),f"기존 에셋 갱신 완료 · {current_result_record['path']} · 기록 {current_result_record['id']} · 추가 편집 전 다시 불러오세요."


def build_sprite_sheet_editor_interface(current_review_port):
    current_preview_script=Path(__file__).with_name('sprite_sheet_editor_preview.js').read_text()
    current_canvas_apply_script=Path(__file__).with_name('sprite_sheet_canvas_apply.js').read_text()
    current_bulk_script=Path(__file__).with_name('sprite_sheet_bulk_edit.js').read_text()
    with gr.Blocks(title='스프라이트 시트 편집기') as current_interface_blocks:
        gr.Markdown('## 스프라이트 시트 편집기\nPNG 시트를 균등 분할한 뒤 프레임별 크롭과 앵커를 픽셀 단위로 조정합니다. 앵커는 크롭 영역의 왼쪽 위를 기준으로 합니다. 다운로드는 별도 파일을 만들며, 기존 에셋 업데이트는 확인 후 원본 이미지와 좌표맵을 갱신합니다.')
        with gr.Row():
            with gr.Column():
                gr.Markdown('### 에셋 저장소에서 찾기')
                current_search_text=gr.Textbox(label='스프라이트 검색',placeholder='이름 · ID · 경로 (예: rest, slime)')
                current_search_button=gr.Button('스프라이트 검색')
                current_asset_choice=gr.Dropdown(label='등록 스프라이트',choices=[])
                current_select_button=gr.Button('선택 스프라이트를 원본으로 가져오기')
                current_asset_record=gr.State({})
                current_pending_update=gr.State({})
                current_input_file=gr.File(label='원본 PNG',file_types=['.png'],type='filepath')
                with gr.Row():
                    current_input_columns=gr.Number(label='원본 열',value=4,precision=0)
                    current_input_rows=gr.Number(label='원본 행',value=2,precision=0)
                    current_load_button=gr.Button('시트 불러오기')
                gr.Markdown('미등록 PNG는 원본 열·행으로 전체 영역을 균등 분할합니다. 나누어떨어지지 않는 픽셀은 분산하며 자동 크롭하지 않습니다.')
                current_image_data=gr.Textbox(value='',visible=False)
                current_pending_load=gr.State({})
                current_source_bounds=gr.JSON(value=[],visible=False)
                with gr.Group(visible=False) as current_confirm_group:
                    gr.Markdown('기존 편집 내용을 새 시트로 바꿉니다. 저장하지 않은 변경은 사라집니다.')
                    with gr.Row():
                        current_confirm_button=gr.Button('불러오기 확인')
                        current_cancel_button=gr.Button('취소')
                with gr.Accordion('고급 좌표 설정',open=False):
                    current_frame_rows=gr.Dataframe(headers=['x','y','width','height','anchorX','anchorY'],datatype=['number']*6,row_count=(1,'dynamic'),col_count=(6,'fixed'),label='프레임별 원본 크롭과 앵커',type='array')
                    with gr.Accordion('숫자로 일괄 적용',open=False):
                        current_bulk_target=gr.Radio(['전체','지정 프레임'],value='전체',label='적용 대상')
                        current_bulk_selection=gr.Textbox(label='프레임 번호 (1부터)',placeholder='예: 1,3-5')
                        current_bulk_mode=gr.Radio(['크롭','앵커'],value='크롭',label='편집 종류')
                        gr.Markdown('양수 여백은 크롭, 음수 여백은 투명 영역 확장입니다. 원본 셀 밖의 인접 이미지는 포함하지 않고 앵커 위치를 보존합니다. 앵커는 크롭 내부 좌표로 지정합니다. 범위 오류가 있으면 전체 적용을 취소합니다.')
                        with gr.Row():
                            current_bulk_left=gr.Number(label='왼쪽 여백',value=0,precision=0)
                            current_bulk_top=gr.Number(label='위쪽 여백',value=0,precision=0)
                            current_bulk_right=gr.Number(label='오른쪽 여백',value=0,precision=0)
                            current_bulk_bottom=gr.Number(label='아래쪽 여백',value=0,precision=0)
                        with gr.Row():
                            current_bulk_anchor_x=gr.Number(label='앵커 X',value=0,precision=0)
                            current_bulk_anchor_y=gr.Number(label='앵커 Y',value=0,precision=0)
                        current_bulk_apply=gr.Button('일괄 적용')
                with gr.Row():
                    current_output_columns=gr.Number(label='출력 열',value=SPRITE_EDITOR_DEFAULT_COLUMNS,precision=0)
                current_export_button=gr.Button('이미지와 좌표맵 생성',variant='primary',interactive=False)
                gr.Markdown('생성 버튼은 원본 PNG를 불러온 뒤 사용할 수 있습니다.')
                current_update_button=gr.Button('기존 에셋 업데이트')
                with gr.Group(visible=False) as current_update_group:
                    current_update_summary=gr.Markdown()
                    with gr.Row():
                        current_update_confirm=gr.Button('업데이트 확인')
                        current_update_cancel=gr.Button('업데이트 취소')
                current_output_files=gr.File(label='결과 다운로드',file_count='multiple',interactive=False)
                current_status_text=gr.Textbox(label='상태',interactive=False)
            with gr.Column():
                current_canvas_mode=gr.Radio(['크롭','앵커'],value='크롭',label='캔버스 편집 도구')
                gr.Markdown('회색 영역은 이미지 바깥입니다. 크롭을 바깥으로 드래그하면 투명 여백을 확장합니다. 큰 확장은 고급 좌표 설정의 음수 여백을 사용하세요. 앵커는 클릭하거나 드래그하세요. 크롭으로 앵커가 영역 밖이 되면 가장 가까운 내부 경계로 이동합니다. 선택 프레임에는 같은 크롭 여백과 크롭 내부 앵커를 적용합니다.')
                gr.HTML('<canvas id="sprite-sheet-alignment-preview" width="640" height="640" style="width:100%;max-width:640px;aspect-ratio:1;background:#fff;touch-action:none" aria-label="프레임 크롭과 앵커 정렬 미리보기"></canvas>')
                with gr.Row():
                    current_frame_index=gr.Slider(label='프레임',minimum=1,maximum=2,value=1,step=1)
                    current_play_enabled=gr.Checkbox(label='재생 (6fps)',value=False)
                current_canvas_target=gr.Radio(['현재 프레임','선택 프레임','전체'],value='현재 프레임',label='캔버스 편집 적용 대상')
                current_canvas_selection=gr.Dropdown(choices=[str(current_frame_number) for current_frame_number in range(1,129)],multiselect=True,label='선택 프레임 번호')
                with gr.Row():
                    current_canvas_apply=gr.Button('캔버스 편집 적용',variant='primary')
                    current_canvas_undo=gr.Button('실행 취소')
                current_shadow_enabled=gr.Checkbox(label='바닥 그림자 표시 (검수용 · 출력 제외)',value=False)
                current_preview_status=gr.Textbox(label='미리보기',interactive=False)
        current_search_button.click(search_sprite_asset_choices,current_search_text,[current_asset_choice,current_status_text])
        current_select_button.click(select_sprite_asset_image,current_asset_choice,[current_input_file,current_asset_record,current_status_text])
        current_update_inputs=[current_asset_record,current_asset_choice,current_image_data,current_frame_rows,current_output_columns,current_source_bounds]
        current_update_button.click(prepare_sprite_sheet_update,current_update_inputs,[current_pending_update,current_update_group,current_update_summary])
        current_update_confirm.click(confirm_sprite_sheet_update,[current_pending_update,*current_update_inputs],[current_pending_update,current_update_group,current_status_text],trigger_mode='once')
        current_update_cancel.click(lambda:({},gr.update(visible=False)),outputs=[current_pending_update,current_update_group],queue=False)
        current_preview_inputs=[current_image_data,current_frame_rows,current_frame_index,current_play_enabled,current_shadow_enabled,current_canvas_mode,current_source_bounds]
        for current_action_button,current_action_name in ((current_canvas_apply,'apply'),(current_canvas_undo,'undo')):
            current_action_button.click(fn=None,inputs=[current_frame_rows,current_canvas_target,current_canvas_selection],outputs=[current_frame_rows,current_status_text],js='(...currentArguments)=>('+current_canvas_apply_script+')( ...currentArguments, '+json.dumps(current_action_name)+')',queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_bulk_apply.click(fn=None,inputs=[current_frame_rows,current_bulk_target,current_bulk_selection,current_bulk_mode,current_bulk_left,current_bulk_top,current_bulk_right,current_bulk_bottom,current_bulk_anchor_x,current_bulk_anchor_y],outputs=[current_frame_rows,current_status_text],js=current_bulk_script,queue=False).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_load_outputs=[current_image_data,current_frame_rows,current_output_columns,current_frame_index,current_status_text]
        current_load_button.click(prepare_sprite_sheet_load,[current_input_file,current_input_columns,current_input_rows,current_image_data,current_asset_record],[*current_load_outputs,current_confirm_group,current_pending_load,current_export_button,current_source_bounds]).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_confirm_button.click(confirm_sprite_sheet_load,[current_pending_load,current_input_file,current_input_columns,current_input_rows,current_asset_record],[*current_load_outputs,current_confirm_group,current_pending_load,current_export_button,current_source_bounds]).then(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_cancel_button.click(lambda:(gr.update(visible=False),{},'불러오기를 취소했습니다. 기존 편집 내용이 유지됩니다.'),outputs=[current_confirm_group,current_pending_load,current_status_text],queue=False)
        for current_input_component in current_preview_inputs[1:6]:current_input_component.input(fn=None,inputs=current_preview_inputs,outputs=current_preview_status,js=current_preview_script,queue=False)
        current_export_button.click(export_sprite_sheet_result,[current_image_data,current_frame_rows,current_output_columns,current_source_bounds],[current_output_files,current_status_text],trigger_mode='once')
    return current_interface_blocks
