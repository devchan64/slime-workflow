"""Gradio 안에서 브라우저 기반 v2 편집기를 제공한다."""
import argparse
import re
import sys
from pathlib import Path
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.ui_assets import resolve_review_ui_asset
from tools.review.common.gradio_browser_controls import build_browser_action_button
from tools.review.common.gradio_frame_navigator import build_frame_navigator
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_joypad import build_transform_joypad, read_joypad_browser_script


def create_sprite_project_script(current_action_name):
    """Gradio 입력을 기존 브라우저 편집기의 공용 작업 명령으로 전달한다."""
    if current_action_name not in ('create','list','load','history','revision','save','export','delete'):
        raise ValueError('지원하지 않는 스프라이트 작업 명령입니다.')
    return "async(currentProjectName,currentOutputSize,currentSelectedId,currentRevisionId)=>{try{if(!window.spriteV2ProjectControls)throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');return await window.spriteV2ProjectControls('"+current_action_name+"',currentProjectName,currentOutputSize,currentSelectedId,currentRevisionId);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message,{__type__:'update'}];}}"


def create_sprite_v2_loader(review_server_port):
    current_loader_script=f"""async()=>{{
{read_joypad_browser_script()}
if(document.querySelector('script[data-sprite-v2]'))return;
if(!document.getElementById('sv2-reference'))await new Promise((resolveEditorReady,rejectEditorReady)=>{{
 const currentMountObserver=new MutationObserver(()=>{{if(document.getElementById('sv2-reference')){{clearTimeout(currentMountTimeout);currentMountObserver.disconnect();resolveEditorReady();}}}});
 const currentMountTimeout=setTimeout(()=>{{currentMountObserver.disconnect();rejectEditorReady(new Error('편집기 화면을 준비하지 못했습니다. 새로고침하세요.'));}},10000);
 currentMountObserver.observe(document.body,{{childList:true,subtree:true}});
}});
window.spriteV2ServerBase='http://127.0.0.1:{review_server_port}';
const currentScriptElement=document.createElement('script');currentScriptElement.dataset.spriteV2='true';
currentScriptElement.src=window.spriteV2ServerBase+'/character-animation/sprite-editor-v2.js';
currentScriptElement.onerror=()=>{{document.getElementById('sv2-status').textContent='편집기 스크립트 연결에 실패했습니다. 관리 서버 연결 후 새로고침하세요.';currentScriptElement.remove();}};
document.body.append(currentScriptElement);
const currentSlicerScript=document.createElement('script');currentSlicerScript.src=window.spriteV2ServerBase+'/character-animation/sprite-sheet-slicer.js';document.body.append(currentSlicerScript);
}}"""
    return current_loader_script


def build_sprite_v2_interface():
    current_markup_text=resolve_review_ui_asset('sprite-editor-v2.html').read_text()
    # 이 HTML에는 캔버스·썸네일·드롭 영역·브라우저 타임라인만 둔다.
    current_markup_text=re.sub(r'<style>.*?</style>','',current_markup_text,flags=re.S)
    with gr.Blocks(title='스프라이트 정규화 편집기 v2',fill_width=True) as current_interface_blocks:
        gr.Markdown('## 스프라이트 정규화 편집기 v2')
        with gr.Accordion('새 작업 만들기',open=False):
            with gr.Row():
                current_project_name=gr.Textbox(label='새 작업명',value='새 스프라이트 작업',max_length=120)
                current_output_size=gr.Dropdown(label='새 작업 출력 크기',choices=[384,256],value=384)
            current_create_button=gr.Button('작업 생성')
        current_project_choice=gr.Dropdown(label='저장된 작업',choices=[],interactive=True)
        with gr.Row():
            current_refresh_button=gr.Button('작업 목록 새로고침')
            current_load_button=gr.Button('불러오기')
            current_delete_button=gr.Button('작업 삭제')
        current_delete_target=gr.Textbox(value='',visible=False)
        with gr.Group(visible=False) as current_delete_panel:
            gr.Markdown('### 선택한 작업을 삭제할까요?\n등록 이미지·전체 수정 이력·출력 파일과 열려 있는 해당 작업의 미저장 편집이 삭제됩니다. 되돌릴 수 없습니다.')
            current_delete_display=build_generation_identifier('삭제할 작업 ID')
            with gr.Row():
                current_cancel_button=gr.Button('취소')
                current_confirm_button=gr.Button('작업 삭제 확인',variant='stop')
        def close_project_delete():
            return gr.update(visible=False),'',''
        def open_project_delete(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('삭제할 작업을 선택하세요.')
            return gr.update(visible=True),current_selected_identifier,current_selected_identifier
        current_delete_outputs=[current_delete_panel,current_delete_target,current_delete_display]
        current_delete_button.click(open_project_delete,current_project_choice,current_delete_outputs,preprocess=False,queue=False)
        current_cancel_button.click(close_project_delete,outputs=current_delete_outputs,queue=False)
        current_project_choice.change(close_project_delete,outputs=current_delete_outputs,queue=False)
        current_feedback_text=gr.Textbox(label='작업 안내',value='목록을 새로고침하여 저장된 작업을 선택하거나 새 작업을 만드세요.',interactive=False)
        with gr.Accordion('현재 작업명·출력 크기 변경',open=False):
            gr.Markdown('현재 작업 정보는 비교 화면 위에 표시됩니다. 빈 작업명과 크기 유지는 기존 값을 보존합니다. 적용 후 수정본 저장으로 이력에 기록하세요.')
            with gr.Row():
                current_rename_input=gr.Textbox(label='변경할 작업명',value='',max_length=120)
                current_resize_choice=gr.Dropdown(label='변경할 출력 크기',choices=[('유지','keep'),('384 × 384','384'),('256 × 256','256')],value='keep')
            current_metadata_button=gr.Button('작업명·출력 크기 적용')
            current_metadata_button.click(fn=None,inputs=[current_rename_input,current_resize_choice],outputs=current_feedback_text,queue=False,js="async(currentNameValue,currentSizeValue)=>{try{if(!window.spriteV2MetadataControls)throw Error('편집기를 준비 중입니다.');return await window.spriteV2MetadataControls(currentNameValue,currentSizeValue);}catch(currentErrorValue){return currentErrorValue.message;}}")
        with gr.Accordion('이미지 등록',open=False):
            current_upload_choice=gr.Dropdown(label='입력 대상',choices=[('레퍼런스','reference'),('프레임 추가','append'),('선택 프레임 교체','replace')],value='reference')
            current_upload_choice.input(fn=None,inputs=current_upload_choice,js="(currentTargetValue)=>{if(!window.spriteV2UploadTarget)throw Error('편집기를 준비 중입니다.');window.spriteV2UploadTarget(currentTargetValue);}",queue=False)
            gr.Markdown('작업을 먼저 생성하거나 불러오세요. PNG/JPEG/WebP · 한 장당 8MB · 최대 128프레임. 투명도를 유지하며 흰 배경은 제거하지 않습니다.')
            with gr.Row():
                build_browser_action_button('파일 불러오기','spriteV2UploadControls','upload',current_feedback_text)
                build_browser_action_button('클립보드 붙여넣기','spriteV2UploadControls','paste',current_feedback_text)
            gr.Markdown('삭제는 현재 편집본에 적용됩니다. 실행 취소로 복원할 수 있으며, 수정본 저장 전까지 저장된 작업은 유지됩니다.')
            with gr.Row():
                build_browser_action_button('레퍼런스 이미지 삭제','spriteV2ImageDeleteControls','reference',current_feedback_text)
                build_browser_action_button('선택 프레임 이미지 삭제','spriteV2FrameControls','remove',current_feedback_text)
        with gr.Accordion('애니메이션 시트 분할',open=False):
            gr.Markdown('① 시트 불러오기 → ② 행·열로 분할선 만들기 → ③ 빨간 분할선 드래그 → ④ 프레임 추가. 번호 순서대로 왼쪽에서 오른쪽, 위에서 아래로 입력됩니다. 원본 투명도를 유지합니다.')
            with gr.Row():
                build_browser_action_button('시트 파일 불러오기','spriteSheetActionControls','upload',current_feedback_text)
                build_browser_action_button('시트 클립보드 붙여넣기','spriteSheetActionControls','paste',current_feedback_text)
            with gr.Row():
                current_sheet_columns=gr.Number(label='열 수 · 가로 칸',value=4,precision=0,minimum=1,maximum=128)
                current_sheet_rows=gr.Number(label='행 수 · 세로 칸',value=2,precision=0,minimum=1,maximum=128)
            current_sheet_grid=gr.Button('균등 분할선 만들기 · 기존 선 초기화')
            gr.HTML('<p id="sprite-sheet-notice" role="status">시트 이미지를 불러오세요. PNG/JPEG/WebP · 최대 32MB, 3200만 픽셀.</p><canvas id="sprite-sheet-preview" aria-label="시트 분할 미리보기 · 빨간 선 드래그" style="max-width:100%;height:auto;touch-action:none" width="1" height="1"></canvas>')
            with gr.Accordion('분할선 좌표 직접 입력',open=False):
                gr.Markdown('첫 좌표와 마지막 좌표는 잘라낼 외곽입니다. 드래그 후 현재 좌표 읽기로 값을 확인하세요. 좌표는 원본 이미지 픽셀 기준입니다.')
                current_sheet_x=gr.Textbox(label='세로 분할선 X 좌표 · 쉼표 구분')
                current_sheet_y=gr.Textbox(label='가로 분할선 Y 좌표 · 쉼표 구분')
                current_sheet_read=gr.Button('현재 분할 좌표 읽기')
                current_sheet_coordinates=gr.Button('입력 좌표로 미리보기 갱신')
            current_sheet_outputs=[current_sheet_x,current_sheet_y,current_feedback_text]
            current_sheet_errors="[{__type__:'update'},{__type__:'update'},currentErrorValue.message]"
            current_sheet_grid.click(fn=None,inputs=[current_sheet_columns,current_sheet_rows],outputs=current_sheet_outputs,queue=False,js="(currentColumnsValue,currentRowsValue)=>{try{return window.spriteSheetControls.grid(currentColumnsValue,currentRowsValue);}catch(currentErrorValue){return "+current_sheet_errors+";}}")
            current_sheet_read.click(fn=None,outputs=current_sheet_outputs,queue=False,js="()=>{try{return window.spriteSheetControls.read();}catch(currentErrorValue){return "+current_sheet_errors+";}}")
            current_sheet_coordinates.click(fn=None,inputs=[current_sheet_x,current_sheet_y],outputs=current_sheet_outputs,queue=False,js="(currentXValues,currentYValues)=>{try{return window.spriteSheetControls.coordinates(currentXValues,currentYValues);}catch(currentErrorValue){return "+current_sheet_errors+";}}")
            build_browser_action_button('분할 결과를 프레임으로 추가','spriteSheetActionControls','apply',current_feedback_text)
        with gr.Accordion('비교 화면 표시',open=False):
            with gr.Row():
                current_zoom_choice=gr.Dropdown(label='화면 확대',choices=[('맞춤','fit'),('100%','1'),('200%','2'),('400%','4')],value='fit')
                current_background_choice=gr.Dropdown(label='배경',choices=[('투명 체크','checker'),('흰색','white'),('어둡게','dark')],value='checker')
            with gr.Row():
                current_overlay_check=gr.Checkbox(label='레퍼런스 겹침',value=False)
                current_onion_check=gr.Checkbox(label='이전 프레임 겹침',value=False)
                current_guides_check=gr.Checkbox(label='가이드 표시',value=True)
        current_view_inputs=[current_zoom_choice,current_background_choice,current_overlay_check,current_onion_check,current_guides_check]
        for current_view_control in current_view_inputs:
            current_view_control.input(fn=None,inputs=current_view_inputs,js="(...currentViewValues)=>{if(!window.spriteV2ViewControls)throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');window.spriteV2ViewControls(...currentViewValues);}",queue=False)
        with gr.Row():
            with gr.Column(scale=3,min_width=360):
                gr.HTML(current_markup_text)
                build_frame_navigator('spriteV2PlaybackControls','spriteV2SeekControls',current_feedback_text)
            with gr.Column(scale=2,min_width=280):
                with gr.Accordion('이동·배율·가이드 조정',open=True):
                    gr.Markdown('편집 대상을 선택하면 즉시 조이패드에 적용됩니다. 캔버스 드래그는 해당 이미지만 움직이며 선택한 편집 대상을 바꾸지 않습니다. 가이드는 별도로 편집합니다.')
                    with gr.Row():
                        current_target_choice=gr.Dropdown(label='설정할 편집 대상',choices=[('현재 프레임','frame'),('레퍼런스','reference'),('체크한 프레임','selected'),('전체 프레임','all')],value='frame')
                    current_target_event=current_target_choice.input(fn=None,inputs=current_target_choice,outputs=current_feedback_text,queue=False,js="(currentTargetValue)=>{try{return window.spriteV2TargetControls(currentTargetValue);}catch(currentErrorValue){return currentErrorValue.message;}}")
                    with gr.Accordion('가이드라인 위치 편집',open=False) as current_guide_panel:
                        gr.Markdown('**① 공통 가이드 불러오기 → ② 가이드 선택 → ③ 위치(px) 입력 → ④ 가이드 수정 적용**\n\n얼굴 원도 가이드 목록에서 선택합니다. 원은 중심 X·Y와 지름을 함께 입력해 적용합니다. 좌표는 출력 이미지의 왼쪽 위가 0입니다. 가로선은 위에서부터 Y, 세로선은 왼쪽에서부터 X 거리입니다. 예: 가로선 100은 위에서 100px입니다. 숫자가 커지면 아래·오른쪽으로 이동합니다. 레퍼런스와 현재 프레임의 가이드는 양쪽 비교 화면에 같은 좌표로 표시됩니다. 녹색 가이드는 레퍼런스의 공통 기준이며 양쪽 화면에서 함께 이동합니다.')
                        current_guide_refresh=gr.Button('현재 대상의 가이드 불러오기')
                        current_guide_choice=gr.Dropdown(label='② 편집할 가이드',choices=[],interactive=True)
                        with gr.Row():
                            current_guide_name=gr.Textbox(label='가이드 이름',value='',max_length=40)
                            current_guide_axis=gr.Dropdown(label='가이드 방향',choices=[('가로선 (Y)','y'),('세로선 (X)','x')],value='y')
                        current_guide_position=gr.Number(label='③ 가이드 위치 · px',value=0,info='가이드를 불러오면 현재 위치가 표시됩니다. 값을 입력한 뒤 아래 적용 버튼을 누르세요.')
                        with gr.Row():
                            current_circle_center_x=gr.Number(label='원 중심 X · px',value=0,visible=False)
                            current_circle_center_y=gr.Number(label='원 중심 Y · px',value=0,visible=False)
                            current_circle_diameter_value=gr.Number(label='원 지름 · px',value=1,minimum=0.01,visible=False)
                        current_guide_outputs=[current_guide_choice,current_guide_name,current_guide_axis,current_guide_position,current_feedback_text,current_circle_center_x,current_circle_center_y,current_circle_diameter_value]
                        current_guide_error="[{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message,{__type__:'update'},{__type__:'update'},{__type__:'update'}]"
                        current_guide_apply=gr.Button('④ 가이드 수정 적용',variant='primary')
                        gr.Markdown('화면 반영 후 **수정본 저장**을 누르면 보존됩니다. 가이드 편집은 이미지 편집 대상과 무관하게 레퍼런스의 공통 기준에 적용됩니다.')
                        current_guide_refresh.click(fn=None,outputs=current_guide_outputs,queue=False,js="()=>{try{return window.spriteV2GuideControls.list();}catch(currentErrorValue){return "+current_guide_error+";}}")
                        current_target_event.then(fn=None,outputs=current_guide_outputs,queue=False,js="()=>{try{return window.spriteV2GuideControls.list();}catch(currentErrorValue){return "+current_guide_error+";}}")
                        current_guide_axis.input(fn=None,inputs=current_guide_axis,outputs=current_guide_position,queue=False,js="(currentAxisValue)=>({__type__:'update',label:currentAxisValue==='y'?'③ 위에서부터 위치 Y · px':'③ 왼쪽에서부터 위치 X · px',info:currentAxisValue==='y'?'0은 위쪽 끝입니다. 값이 커지면 아래로 이동합니다.':'0은 왼쪽 끝입니다. 값이 커지면 오른쪽으로 이동합니다.'})")
                        current_guide_panel.expand(fn=None,outputs=current_guide_outputs,queue=False,js="()=>{try{return window.spriteV2GuideControls.list();}catch(currentErrorValue){return "+current_guide_error+";}}")
                        current_guide_choice.input(fn=None,inputs=current_guide_choice,outputs=current_guide_outputs[1:],queue=False,js="(currentGuideValue)=>{try{return window.spriteV2GuideControls.select(currentGuideValue);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message,{__type__:'update'},{__type__:'update'},{__type__:'update'}];}}")
                        current_guide_apply.click(fn=None,inputs=[current_guide_choice,current_guide_name,current_guide_axis,current_guide_position,current_circle_center_x,current_circle_center_y,current_circle_diameter_value],outputs=current_guide_outputs,queue=False,js="async(currentGuideValue,currentLabelValue,currentAxisValue,currentPositionValue,currentCircleCenterX,currentCircleCenterY,currentCircleDiameter)=>{try{return await window.spriteV2GuideControls.apply(currentGuideValue,currentLabelValue,currentAxisValue,currentPositionValue,currentCircleCenterX,currentCircleCenterY,currentCircleDiameter);}catch(currentErrorValue){return "+current_guide_error+";}}")
                        with gr.Row():
                            for current_edit_action,current_edit_label in (('guide-add','가로선 추가'),('guide-vertical','세로선 추가'),('guide-remove','선택 가이드 삭제')):
                                current_guide_action_button=gr.Button(current_edit_label)
                                current_guide_action_button.click(fn=None,inputs=current_guide_choice,outputs=current_guide_outputs,queue=False,js="async(currentGuideValue)=>{try{return await window.spriteV2GuideControls.change('"+current_edit_action+"',currentGuideValue);}catch(currentErrorValue){return "+current_guide_error+";}}")
                    build_transform_joypad('spriteV2JoypadControls',current_feedback_text,current_separate_axes=True)
                    build_browser_action_button('실행 취소','spriteV2FrameControls','undo',current_feedback_text)
        with gr.Accordion('프레임 순서·복제·삭제',open=False):
            gr.Markdown('### 프레임 편집\n선택한 프레임의 순서를 바꾸거나 복제·삭제합니다. 전체 프레임 삭제는 레퍼런스를 유지합니다. 삭제는 실행 취소할 수 있으며 수정본 저장 전에는 저장된 작업을 바꾸지 않습니다.')
            with gr.Row():
                for current_frame_action,current_frame_label in (('earlier','한 칸 앞으로'),('later','한 칸 뒤로'),('duplicate','선택 프레임 복제'),('remove','선택 프레임 삭제'),('remove-all','전체 프레임 삭제')):
                    build_browser_action_button(current_frame_label,'spriteV2FrameControls',current_frame_action,current_feedback_text)
            with gr.Row():
                current_order_number=gr.Number(label='선택 프레임을 옮길 순번',value=1,minimum=1,precision=0)
                current_order_button=gr.Button('지정 순번으로 옮기기')
            current_order_button.click(fn=None,inputs=current_order_number,outputs=current_feedback_text,queue=False,js="async(currentTargetNumber)=>{try{if(!window.spriteV2ReorderControls)throw Error('편집기를 준비 중입니다.');return await window.spriteV2ReorderControls(currentTargetNumber);}catch(currentErrorValue){return currentErrorValue.message;}}")
            gr.Markdown('목록에서 옮길 프레임을 선택한 뒤 순번을 입력하세요. 목록·재생·내보내기 순서가 함께 바뀌며, 수정본 저장 전까지 실행 취소할 수 있습니다.')
        with gr.Accordion('재생 시간 조정',open=False):
            gr.Markdown('현재 설정은 비교 화면 아래에 표시됩니다. 변경할 항목을 체크하고 값을 입력하세요. 유지 시간은 현재 선택한 프레임에 적용하며 0이면 작업 FPS를 사용합니다.')
            with gr.Row():
                current_fps_enabled=gr.Checkbox(label='FPS 변경',value=False)
                current_fps_input=gr.Number(label='변경할 FPS',value=8,minimum=1,maximum=60)
                current_duration_enabled=gr.Checkbox(label='유지 시간 변경',value=False)
                current_duration_input=gr.Number(label='선택 프레임 유지 시간 · ms',value=0,minimum=0,maximum=10000)
            current_timing_button=gr.Button('재생 시간 적용')
            current_timing_button.click(fn=None,inputs=[current_fps_input,current_duration_input,current_fps_enabled,current_duration_enabled],outputs=current_feedback_text,queue=False,js="async(fps,duration,changeFps,changeDuration)=>{try{if(!window.spriteV2TimingControls)throw Error('편집기를 준비 중입니다.');return await window.spriteV2TimingControls(changeFps?fps:null,changeDuration?duration:null);}catch(error){return error.message;}}")
        gr.Markdown('### 저장 · 출력\n현재 작업을 불러온 뒤 사용할 수 있습니다. 이전 버전을 불러와 저장하면 새 수정 이력으로 남습니다. 가이드는 출력 이미지에 포함하지 않습니다.')
        with gr.Row():
            current_save_button=gr.Button('수정본 저장')
            current_export_button=gr.Button('현재 편집 저장 후 PNG·시트·GIF 내보내기')
        current_revision_choice=gr.Dropdown(label='수정 이력',choices=[],interactive=True)
        current_revision_identifier=build_generation_identifier('수정 이력 ID')
        current_revision_choice.change(fn=None,inputs=current_revision_choice,outputs=current_revision_identifier,queue=False,js="(currentRevisionIdentifier)=>currentRevisionIdentifier ?? ''")
        with gr.Row():
            current_history_button=gr.Button('수정 이력 새로고침')
            current_revision_button=gr.Button('선택 버전 불러오기')
        with gr.Accordion('선택 수정본 삭제',open=False):
            gr.Markdown('선택한 수정 이력만 삭제합니다. 최신 수정본이면 직전 저장본이 최신이 됩니다. 마지막 한 개는 유지합니다. 현재 편집 초안·등록 이미지·내보낸 파일은 유지됩니다.')
            current_revision_confirm=gr.Checkbox(label='선택한 수정본 삭제 확인',value=False)
            current_revision_delete=gr.Button('선택 수정본 삭제',variant='stop')
        current_revision_choice.change(fn=None,outputs=current_revision_confirm,js='()=>false',queue=False)
        current_revision_delete.click(fn=None,inputs=[current_project_choice,current_revision_choice,current_revision_confirm],outputs=[current_revision_choice,current_feedback_text,current_revision_confirm],queue=False,js="async(currentProjectIdentifier,currentRevisionIdentifier,currentConfirmedValue)=>{try{if(!window.spriteV2DeleteRevision)throw Error('편집기를 준비 중입니다.');return await window.spriteV2DeleteRevision(currentProjectIdentifier,currentRevisionIdentifier,currentConfirmedValue);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message,false];}}")
        gr.Markdown('GIF는 흰 배경으로 검수합니다. 내보내기는 현재 편집을 새 수정본으로 저장한 후 다운로드합니다.')
        for current_action_name,current_action_button in (('create',current_create_button),('list',current_refresh_button),('load',current_load_button),('save',current_save_button),('export',current_export_button),('history',current_history_button),('revision',current_revision_button)):
            current_action_button.click(fn=None,inputs=[current_project_name,current_output_size,current_project_choice,current_revision_choice],outputs=[current_project_choice,current_feedback_text,current_revision_choice],js=create_sprite_project_script(current_action_name),queue=False)

        current_delete_script="""async(currentProjectName,currentOutputSize,currentSelectedId,currentConfirmedId)=>{
const currentNoChange={__type__:'update'};
try{
 if(!currentSelectedId||currentSelectedId!==currentConfirmedId)throw Error('삭제 대상이 변경되었습니다. 다시 확인하세요.');
 if(!window.spriteV2ProjectControls)throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');
 const currentResultValues=await window.spriteV2ProjectControls('delete',currentProjectName,currentOutputSize,currentSelectedId,null);
 return [...currentResultValues,{__type__:'update',visible:false},'',''];
}catch(currentErrorValue){
 return [currentNoChange,currentErrorValue.message,currentNoChange,currentNoChange,currentNoChange,currentNoChange];
}
}"""
        current_confirm_button.click(fn=None,inputs=[current_project_name,current_output_size,current_project_choice,current_delete_target],outputs=[current_project_choice,current_feedback_text,current_revision_choice,*current_delete_outputs],js=current_delete_script,queue=False)

    return current_interface_blocks


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/sprite-editor-v2/')
    current_argument_values=current_argument_parser.parse_args()
    current_markup_text=resolve_review_ui_asset('sprite-editor-v2.html').read_text()
    current_style_text=re.search(r'<style>(.*?)</style>',current_markup_text,re.S).group(1)
    current_loader_script=create_sprite_v2_loader(current_argument_values.review_port)
    build_sprite_v2_interface().queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,css=current_style_text,js=current_loader_script,allowed_paths=[])
