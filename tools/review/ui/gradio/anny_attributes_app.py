"""ANNY의 표준 설정과 브라우저 체형 상태·3D 캔버스를 연결한다."""
import argparse
import json
import re
import threading
import time
import sys
from pathlib import Path

import gradio as gr


WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_browser_controls import build_browser_action_button
from tools.review.common.gradio_logs import create_copyable_log_textbox
from tools.review.common.gradio_browser_history import build_browser_history_controls

ANNY_ATTRIBUTE_PAGE_PATH=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/anny/anny-attributes.html'


def read_anny_attribute_markup():
    attribute_page_text=ANNY_ATTRIBUTE_PAGE_PATH.read_text()
    main_markup_match=re.search(r'(<main>.*?</main>\s*<dialog.*?</dialog>)',attribute_page_text,re.DOTALL)
    if main_markup_match is None:raise ValueError('ANNY 속성 편집기 본문을 찾을 수 없습니다.')
    current_markup_text=main_markup_match.group(1)
    for current_button_identifier in ('reset','generate-preview','retry'):
        current_markup_text=re.sub(r'<button[^>]*id="'+current_button_identifier+r'"[^>]*>.*?</button>','',current_markup_text)
    current_markup_text=re.sub(r'<section[^>]*id="generation-history"[^>]*></section>','',current_markup_text)
    current_markup_text=re.sub(r'<details id="logs">.*?</details>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<label for="baseline-profile">.*?</select>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<label for="render-rotation-y">.*?</output>','<p id="render-rotation-value">현재 렌더 Y축 회전: 0°</p>',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<div class="attribute-panel-header">.*?</div>','',current_markup_text,flags=re.S)
    current_markup_text=current_markup_text.replace('<div class="attribute-scroll-region"','<div hidden class="attribute-scroll-region"')
    current_markup_text=current_markup_text.replace('<canvas id="mesh-preview"','<canvas width="768" height="520" style="width:100%;height:520px;touch-action:none" id="mesh-preview"')
    return '<div id="anny-attribute-root">'+current_markup_text+'</div>'


def read_anny_attribute_script():
    attribute_page_text=ANNY_ATTRIBUTE_PAGE_PATH.read_text()
    inline_script_match=re.search(r'<script>\s*(const attributeLogViewer=.*?)</script>',attribute_page_text,re.DOTALL)
    if inline_script_match is None:raise ValueError('ANNY 속성 편집기 스크립트를 찾을 수 없습니다.')
    return inline_script_match.group(1)


def create_anny_attribute_loader(review_server_port):
    inline_script_text=json.dumps(read_anny_attribute_script()).replace('<','\\u003c')
    review_server_base=f'http://127.0.0.1:{review_server_port}'
    return f"""async()=>{{if(document.querySelector('script[data-anny-attribute-component]'))return;const componentScriptText={inline_script_text};const loadComponentScript=currentPathValue=>new Promise((resolve,reject)=>{{const nextScriptElement=document.createElement('script');nextScriptElement.src='{review_server_base}'+currentPathValue;nextScriptElement.dataset.annyAttributeComponent='true';nextScriptElement.onload=resolve;nextScriptElement.onerror=()=>reject(new Error('ANNY 구성 요소를 불러오지 못했습니다: '+currentPathValue));document.body.append(nextScriptElement);}});await loadComponentScript('/management/gpu-queue-confirmation.js');await loadComponentScript('/anny-attributes/log-viewer.js');await loadComponentScript('/anny-attributes/mesh-viewer.js');const inlineScriptElement=document.createElement('script');inlineScriptElement.dataset.annyAttributeComponent='true';inlineScriptElement.textContent=componentScriptText;document.body.append(inlineScriptElement);if(window.top===window)await loadComponentScript('/management/gpu-status.js');}}"""


def build_anny_attribute_interface(review_server_port):
    with gr.Blocks(title='Anny 속성 렌더러') as interface_blocks_value:
        current_action_feedback=gr.Textbox(label='작업 안내',value='체형을 설정한 뒤 프리뷰 생성 또는 이미지 렌더를 실행하세요.',interactive=False)
        with gr.Row():
            for current_section_name,current_section_label in (('attributes','체형 설정으로 이동'),('preview','프리뷰·렌더로 이동'),('history','이전 결과로 이동')):
                build_browser_action_button(current_section_label,'annyNavigationControls',current_section_name,current_action_feedback)
        current_profile_choice=gr.Dropdown(label='기준 체형',choices=[],interactive=True)
        with gr.Row():
            for current_profile_action,current_profile_label in (('list','기준 체형 목록 읽기'),('apply','기준 체형 적용')):
                current_profile_button=gr.Button(current_profile_label)
                current_profile_button.click(fn=None,inputs=current_profile_choice,outputs=[current_profile_choice,current_action_feedback],queue=False,js="async(currentProfileId)=>{try{return await window.annyProfileControls('"+current_profile_action+"',currentProfileId);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        with gr.Row():
            for current_action_name,current_button_label in (('reset','신체 기준값 복원'),('preview','프리뷰 생성'),('render','이미지 렌더')):
                build_browser_action_button(current_button_label,'annyAttributeActions',current_action_name,current_action_feedback)
        with gr.Accordion('신체 속성 편집',open=True,elem_id='anny-standard-attributes'):
            current_attribute_choice=gr.Dropdown(label='신체 속성',choices=[],interactive=True)
            current_attribute_value=gr.Number(label='속성값',value=0)
            with gr.Row():
                for current_attribute_action,current_attribute_label in (('read','속성 목록·현재 값 읽기'),('apply','속성값 적용')):
                    current_attribute_button=gr.Button(current_attribute_label)
                    current_attribute_button.click(fn=None,inputs=[current_attribute_choice,current_attribute_value],outputs=[current_attribute_choice,current_attribute_value,current_action_feedback],queue=False,js="(currentFieldName,currentFieldValue)=>{try{return window.annyNumericControls('"+current_attribute_action+"',currentFieldName,currentFieldValue);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
            current_attribute_choice.input(fn=None,inputs=[current_attribute_choice,current_attribute_value],outputs=[current_attribute_choice,current_attribute_value,current_action_feedback],queue=False,js="(currentFieldName,currentFieldValue)=>{try{return window.annyNumericControls('read',currentFieldName,currentFieldValue);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
        with gr.Accordion('기준 자세 상세',open=False):
            gr.Markdown('현재 적용한 기준 체형의 본 설정입니다. 체형을 변경한 뒤 다시 읽으세요.')
            current_pose_details=gr.Textbox(label='기준 자세 설정',lines=8,interactive=False)
            current_pose_button=gr.Button('기준 자세 읽기')
            current_pose_button.click(fn=None,inputs=[],outputs=current_pose_details,queue=False,js="()=>{try{return window.annyPoseDetails();}catch(currentErrorValue){return currentErrorValue.message;}}")
        with gr.Group():
            current_rotation_value=gr.Number(label='렌더 Y축 회전 · °',value=0,minimum=-180,maximum=180)
            with gr.Row():
                for current_rotation_action,current_rotation_label in (('read','현재 회전 읽기'),('apply','렌더 회전 적용')):
                    current_rotation_button=gr.Button(current_rotation_label)
                    current_rotation_button.click(fn=None,inputs=current_rotation_value,outputs=[current_rotation_value,current_action_feedback],queue=False,js="(currentRotationValue)=>{try{return window.annyRotationControls('"+current_rotation_action+"',currentRotationValue);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        gr.HTML(read_anny_attribute_markup())
        build_browser_history_controls('annyHistoryControls','anny-standard-history')
        with gr.Accordion('렌더 로그',open=False):
            current_log_refresh=gr.Checkbox(label='자동 갱신',value=True)
            current_log_output=create_copyable_log_textbox(label='현재 실행 로그 · 최근 12,000자',lines=12,interactive=False,autoscroll=False)
            current_log_timer=gr.Timer(1)
            current_log_timer.tick(fn=None,inputs=current_log_refresh,outputs=current_log_output,queue=False,js="(currentRefreshEnabled)=>currentRefreshEnabled?(window.annyExecutionLogText||''):{__type__:'update'}",show_progress='hidden')
    return interface_blocks_value


if __name__=='__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/anny-attributes/')
    argument_values = argument_parser_value.parse_args()
    threading.Thread(target=lambda: time.sleep(1), daemon=True).start()
    build_anny_attribute_interface(argument_values.review_port).queue().launch(
        server_name='127.0.0.1', server_port=argument_values.port, root_path=argument_values.root_path,
        js=create_anny_attribute_loader(argument_values.review_port), allowed_paths=[])
