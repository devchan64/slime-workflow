"""기존 브라우저 프레임 편집기를 Gradio 작업 영역에 연결한다."""
import argparse
import re
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.ui_assets import resolve_review_ui_asset
from tools.review.common.gradio_browser_controls import build_browser_action_button
from tools.review.common.gradio_frame_navigator import build_frame_navigator
from tools.review.common.gradio_logs import create_copyable_log_textbox
from tools.review.common.gradio_joypad import build_transform_joypad, read_joypad_browser_script

def read_sprite_editor_styles():
    editor_source_text=resolve_review_ui_asset('sprite-editor.html').read_text()
    editor_style_match=re.search(r'<style>(.*?)</style>',editor_source_text,re.DOTALL)
    if editor_style_match is None:raise ValueError('스프라이트 편집기 스타일을 찾을 수 없습니다.')
    return re.sub(r'\.gradio-container[^{}]*\{[^{}]*\}','',editor_style_match.group(1))

def read_sprite_editor_markup():
    editor_source_text=resolve_review_ui_asset('sprite-editor.html').read_text()
    editor_markup_match=re.search(r'<main>(.*)</main>',editor_source_text,re.DOTALL)
    if editor_markup_match is None:raise ValueError('스프라이트 편집기 본문을 찾을 수 없습니다.')
    current_markup_text=editor_markup_match.group(1)
    current_markup_text=re.sub(r'<header><h1>.*?</h1><p>.*?</p>', '<header>',current_markup_text,flags=re.S)
    for current_button_name in ('prev','play','stop','next','undo','reset','frames-all','frames-none','save'):
        current_markup_text=re.sub(r'<button id="sprite-'+current_button_name+r'"[^>]*>.*?</button>','',current_markup_text)
    for current_control_label,current_control_name in (('화면 확대','zoom'),('배경','background'),('재생 속도','speed'),('캔버스 조작','mode')):
        current_markup_text=re.sub(r'<label>'+current_control_label+r'<select id="sprite-'+current_control_name+r'".*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<label><input type="checkbox" id="sprite-(?:guides|onion)"[^>]*>.*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<label>등록 캐릭터·몬스터 스프라이트<select.*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<button id="sprite-asset-load">.*?</button>','',current_markup_text)
    current_markup_text=re.sub(r'<label>방향<select id="sprite-direction".*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<p id="sprite-asset-help">.*?</p>','',current_markup_text)
    current_markup_text=re.sub(r'<div class="sprite-fine-pads">.*?(?=<div class="sprite-fine-summary">)','',current_markup_text,flags=re.S)
    current_markup_text=current_markup_text.replace('방향키: 위치 이동 · ＋/−: 몸체 높이 조절','공용 조이패드: 위치 이동 · 이미지 배율 조절').replace('편집 범위 · 1px 미세 조절','편집 범위 · 위치·배율 조절').replace('출력 기준 1px · 비율·기준점 유지','기준점 유지')
    current_markup_text=re.sub(r'<fieldset id="sprite-scope">.*?</fieldset>', '<p id="sprite-scope-summary" role="status">원본을 불러오세요.</p>',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<fieldset id="sprite-frame-selection">.*?</fieldset>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<h3>3\. 선택 범위에 작업 적용</h3>.*?</section>','</section>',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<h3>2\. 속성값</h3>.*?</section>','</section>',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<details open><summary>추가 가이드라인</summary>.*?</details>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<h2>저장 이력</h2>.*?</section>','</section>',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<details><summary>작업 로그</summary><pre id="sprite-log"></pre></details>','',current_markup_text)
    current_markup_text=re.sub(r'<section class="studio-panel"><h2>전체 결과 검수</h2>.*?</section>','',current_markup_text,flags=re.S)
    return '<main id="sprite-editor-root">'+current_markup_text+'</main>'

def create_sprite_editor_loader(review_server_port):
    return f"""()=>{{{read_joypad_browser_script()}
window.spriteEditorServerBase='http://127.0.0.1:{review_server_port}';const currentScriptElement=document.querySelector('script[data-sprite-editor-component]');if(currentScriptElement)return;const nextScriptElement=document.createElement('script');nextScriptElement.src=window.spriteEditorServerBase+'/character-animation/sprite-editor.js';nextScriptElement.dataset.spriteEditorComponent='true';document.body.append(nextScriptElement);}}"""

def build_sprite_editor_interface(review_server_port):
    with gr.Blocks(title='스프라이트 정규화 편집기') as interface_blocks_value:
        gr.Markdown('## 스프라이트 정규화 편집기\n편집본을 확대해 조정하고 네 방향을 같은 프레임으로 재생합니다. 저장은 검수 사본에만 적용됩니다.')
        current_playback_feedback=gr.Textbox(label='재생 안내',value='등록 에셋을 불러온 뒤 재생할 수 있습니다.',interactive=False)
        with gr.Group():
            current_asset_choice=gr.Dropdown(label='등록 캐릭터·몬스터 스프라이트',choices=[],interactive=True)
            with gr.Row():
                current_asset_refresh=gr.Button('등록 에셋 목록 읽기')
                current_asset_load=gr.Button('에셋 불러오기')
            current_direction_choice=gr.Dropdown(label='편집 방향',choices=[],interactive=True)
            gr.Markdown('목록 읽기로 현재 등록 에셋과 불러온 방향을 확인하세요. 에셋 변경은 저장되지 않은 편집이 있을 때 확인을 요청합니다.')
        for current_command_name,current_command_button in (('list',current_asset_refresh),('load',current_asset_load)):
            current_command_button.click(fn=None,inputs=current_asset_choice,outputs=[current_asset_choice,current_direction_choice,current_playback_feedback],queue=False,js="async(currentAssetValue)=>{try{return await window.spriteEditorSourceControls('"+current_command_name+"',currentAssetValue);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
        current_direction_choice.input(fn=None,inputs=current_direction_choice,outputs=current_playback_feedback,queue=False,js="(currentDirectionValue)=>{try{return window.spriteEditorDirectionControls(currentDirectionValue);}catch(currentErrorValue){return currentErrorValue.message;}}")
        build_frame_navigator('spriteEditorPlaybackControls','spriteEditorSeekControls',current_playback_feedback)
        with gr.Row():
            current_zoom_choice=gr.Dropdown(label='화면 확대',choices=[('너비 맞춤','fit'),('100%','1'),('150%','1.5'),('200%','2'),('300%','3'),('400%','4')],value='2')
            current_background_choice=gr.Dropdown(label='배경',choices=[('투명 체크','checker'),('어두운 배경','dark'),('흰 배경','white')],value='checker')
            current_speed_choice=gr.Dropdown(label='재생 속도',choices=[('0.5배','0.5'),('1배','1'),('2배','2')],value='1')
        with gr.Row():
            current_guides_toggle=gr.Checkbox(label='가이드 표시',value=True)
            current_onion_toggle=gr.Checkbox(label='이전 프레임 겹침',value=False)
        current_canvas_mode=gr.Dropdown(label='캔버스 조작',choices=[('배치 이동','move'),('기준점 지정','anchor'),('중심선 지정','center'),('바닥선 지정','floor'),('머리선 지정','head')],value='move')
        for current_option_name,current_option_component in (('zoom',current_zoom_choice),('background',current_background_choice),('speed',current_speed_choice),('guides',current_guides_toggle),('onion',current_onion_toggle),('mode',current_canvas_mode)):
            current_option_component.input(fn=None,inputs=current_option_component,outputs=current_playback_feedback,queue=False,js="(currentOptionValue)=>{try{return window.spriteEditorViewControls('"+current_option_name+"',currentOptionValue);}catch(currentErrorValue){return currentErrorValue.message;}}")
        with gr.Row():
            current_scope_choice=gr.Dropdown(label='설정할 편집 범위',choices=[('현재 프레임','selected'),('현재 방향','direction'),('모든 프레임','clip'),('체크한 프레임','custom')],value='selected')
            current_scope_button=gr.Button('편집 범위 적용')
        current_scope_button.click(fn=None,inputs=current_scope_choice,outputs=current_playback_feedback,queue=False,js="(currentScopeName)=>{try{return window.spriteEditorScopeControls(currentScopeName);}catch(currentErrorValue){return currentErrorValue.message;}}")
        gr.Markdown('프레임 체크 선택 시 체크한 프레임 범위로 전환됩니다. 실제 적용 범위는 편집 화면의 적용 대상 표시를 확인하세요.')
        with gr.Row():
            for current_action_name,current_button_label in (('all','전체 프레임 선택'),('none','선택 해제')):
                build_browser_action_button(current_button_label,'spriteEditorSelectionControls',current_action_name,current_playback_feedback)
        current_frame_choices=gr.CheckboxGroup(label='적용할 프레임 선택',choices=[],value=[])
        current_frame_choices.input(fn=None,inputs=current_frame_choices,outputs=[current_frame_choices,current_playback_feedback],queue=False,js="currentFrameSelection=>{try{return [window.spriteEditorFrameChoices(currentFrameSelection),'선택한 프레임 범위로 전환했습니다.'];}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        current_selection_timer=gr.Timer(1)
        current_selection_timer.tick(fn=None,outputs=current_frame_choices,queue=False,show_progress='hidden',js="()=>{if(typeof window.spriteEditorFrameChoices!=='function')return {__type__:'update'};const currentSelectionRecord=window.spriteEditorFrameChoices();const currentSelectionSignature=JSON.stringify(currentSelectionRecord);if(window.spriteSelectionSignature===currentSelectionSignature)return {__type__:'update'};window.spriteSelectionSignature=currentSelectionSignature;return currentSelectionRecord;}")
        build_transform_joypad('spriteEditorJoypadControls',current_playback_feedback)
        with gr.Row():
            for current_action_name,current_action_label in (('undo','실행 취소'),('reset','선택 프레임 원본 복원')):
                build_browser_action_button(current_action_label,'spriteEditorEditControls',current_action_name,current_playback_feedback)
        with gr.Accordion('추가 가이드라인',open=False):
            gr.Markdown('전체 프레임 공통이며 출력 이미지에는 포함되지 않습니다. 작업 불러오기·실행 취소 후 목록을 다시 읽으세요. 수정은 저장 전 실행 취소할 수 있습니다.')
            current_guide_list=gr.Textbox(label='가이드 목록',interactive=False,lines=4)
            with gr.Row():
                current_guide_number=gr.Number(label='가이드 번호',value=1,minimum=1,precision=0)
                current_guide_position=gr.Number(label='가이드 위치 · px',value=0,minimum=0)
            with gr.Row():
                for current_guide_action,current_guide_label in (('read','가이드 목록 읽기'),('horizontal','가로 가이드 추가'),('vertical','세로 가이드 추가'),('apply','가이드 위치 적용'),('remove','가이드 삭제')):
                    current_guide_button=gr.Button(current_guide_label)
                    current_guide_button.click(fn=None,inputs=[current_guide_number,current_guide_position],outputs=[current_guide_list,current_playback_feedback],queue=False,js="(currentGuideNumber,currentGuidePosition)=>{try{return [window.spriteEditorGuideControls('"+current_guide_action+"',currentGuideNumber,currentGuidePosition),'가이드 목록을 확인하세요.'];}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        with gr.Accordion('원본 기준선·기준점 수치',open=False):
            gr.Markdown('현재 프레임의 값을 읽고 선택한 편집 범위에 해당 항목만 적용합니다. 위치·배율은 공용 조이패드에서 조절하세요.')
            with gr.Row():
                current_numeric_field=gr.Dropdown(label='기준 수치 항목',choices=[('원본 중심 X','center'),('원본 바닥 Y','floor'),('원본 머리 Y','head'),('기준점 X','anchorX'),('기준점 Y','anchorY')],value='center')
                current_numeric_value=gr.Number(label='기준 수치 · px',value=0)
            with gr.Row():
                for current_numeric_action,current_numeric_label in (('read','기준 수치 읽기'),('apply','기준 수치 적용')):
                    current_numeric_button=gr.Button(current_numeric_label)
                    current_numeric_button.click(fn=None,inputs=[current_numeric_field,current_numeric_value],outputs=[current_numeric_value,current_playback_feedback],queue=False,js="(currentFieldName,currentFieldValue)=>{try{return window.spriteEditorNumericControls('"+current_numeric_action+"',currentFieldName,currentFieldValue);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        with gr.Accordion('선택 범위 정렬',open=False):
            gr.Markdown('바닥은 Y 위치, 중심은 X 위치만 조정합니다. 몸체 높이는 중심과 발 위치를 유지하며 배율을 변경합니다. 목표값은 출력 셀 내부의 양수로 입력하세요.')
            with gr.Row():
                current_alignment_choice=gr.Dropdown(label='정렬 작업',choices=[('바닥 정렬 · Y','floor'),('중심 정렬 · X','center'),('몸체 높이 맞춤','height'),('현재 프레임 설정 복사','copy')],value='floor')
                current_alignment_target=gr.Number(label='목표 바닥 Y 또는 몸체 높이 · px',value=None)
            gr.Markdown('중심 정렬과 설정 복사는 목표 수치를 사용하지 않습니다. 설정 복사는 현재 프레임의 모든 속성을 선택 범위에 적용합니다.')
            current_alignment_button=gr.Button('선택 범위에 정렬 적용')
            current_alignment_button.click(fn=None,inputs=[current_alignment_choice,current_alignment_target],outputs=current_playback_feedback,queue=False,js="(currentActionName,currentTargetValue)=>{try{return window.spriteEditorAlignmentControls(currentActionName,currentTargetValue);}catch(currentErrorValue){return currentErrorValue.message;}}")
        gr.HTML(read_sprite_editor_markup())
        with gr.Column(elem_id='sprite-results-root'):
            gr.Markdown('### 전체 결과 검수')
            with gr.Accordion('전체 방향 동기 검수',open=False) as current_direction_panel:
                gr.HTML('<div id="sprite-directions" class="sprite-direction-grid"></div>')
            current_direction_panel.expand(fn=None,queue=False,js="()=>{window.spriteEditorDirectionPreview?.();}")
            with gr.Accordion('전체 출력 시트 · 방향별 행 / 시간순 열',open=False) as current_sheet_panel:
                gr.HTML('<p id="sprite-sheet-info"></p><canvas id="sprite-sheet" class="sprite-preview" aria-label="전체 출력 시트"></canvas>')
            current_sheet_panel.expand(fn=None,queue=False,js="()=>{window.spriteEditorSheetVisibility?.(true);}")
            current_sheet_panel.collapse(fn=None,queue=False,js="()=>{window.spriteEditorSheetVisibility?.(false);}")
        with gr.Accordion('작업 로그',open=False):
            gr.Markdown('현재 브라우저 편집 세션의 최근 40개 안내를 표시합니다.')
            current_editor_log=create_copyable_log_textbox(label='편집 작업 로그',interactive=False,lines=6,max_lines=12)
        current_editor_timer=gr.Timer(1)
        current_editor_timer.tick(fn=None,inputs=current_editor_log,outputs=current_editor_log,queue=False,show_progress='hidden',js="currentDisplayedLog=>{if(typeof window.spriteEditorReadLog!=='function')return {__type__:'update'};const currentLogText=window.spriteEditorReadLog();return currentLogText===currentDisplayedLog?{__type__:'update'}:currentLogText;}")
        build_browser_action_button('프로젝트 저장','spriteEditorSaveControls','save',current_playback_feedback)
        gr.Markdown('현재 편집을 새 저장 이력으로 보존합니다. 원본 에셋은 변경하지 않습니다.')
        with gr.Accordion('저장 이력',open=True):
            current_revision_choice=gr.Dropdown(label='저장 이력 선택',choices=[],interactive=True)
            current_revision_document=gr.Textbox(label='선택 이력 입력값',interactive=False,lines=8,max_lines=16)
            with gr.Row():
                for current_history_action,current_history_label in (('list','저장 이력 새로고침'),('inspect','이력 입력값 조회'),('restore','이력 편집기로 불러오기')):
                    current_history_button=gr.Button(current_history_label)
                    current_history_button.click(fn=None,inputs=current_revision_choice,outputs=[current_revision_choice,current_revision_document,current_playback_feedback],queue=False,js="async(currentRevisionId)=>{try{return await window.spriteEditorHistoryControls('"+current_history_action+"',currentRevisionId);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
            with gr.Accordion('이력 수동 초기화',open=False):
                gr.Markdown('확인 후 목록에서 제외합니다. 원본과 저장 파일, 현재 편집은 유지됩니다.')
                for current_history_action,current_history_label in (('remove','선택 이력 제외'),('reset','전체 이력 초기화')):
                    current_history_button=gr.Button(current_history_label)
                    current_history_button.click(fn=None,inputs=current_revision_choice,outputs=[current_revision_choice,current_revision_document,current_playback_feedback],queue=False,js="async(currentRevisionId)=>{try{return await window.spriteEditorHistoryControls('"+current_history_action+"',currentRevisionId);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")

    return interface_blocks_value



if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/sprite-editor/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start()
    build_sprite_editor_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=read_sprite_editor_styles(),js=create_sprite_editor_loader(arguments_value.review_port),allowed_paths=[])
