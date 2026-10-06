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


def create_sprite_project_script(current_action_name):
    """Gradio 입력을 기존 브라우저 편집기의 공용 작업 명령으로 전달한다."""
    if current_action_name not in ('create','list','load','history','revision','save','export'):
        raise ValueError('지원하지 않는 스프라이트 작업 명령입니다.')
    return "async(currentProjectName,currentOutputSize,currentSelectedId,currentRevisionId)=>{try{if(!window.spriteV2ProjectControls)throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');return await window.spriteV2ProjectControls('"+current_action_name+"',currentProjectName,currentOutputSize,currentSelectedId,currentRevisionId);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message,{__type__:'update'}];}}"


def create_sprite_v2_loader(review_server_port):
    current_loader_script=f"""async()=>{{
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
}}"""
    return current_loader_script


def build_sprite_v2_interface():
    current_markup_text=resolve_review_ui_asset('sprite-editor-v2.html').read_text()
    # 새 작업과 저장 작업 선택은 표준 컴포넌트에서 제공한다.
    current_markup_text=re.sub(r'<style>.*?</style>','',current_markup_text,flags=re.S)
    for current_control_identifier in ('sv2-create','sv2-project-refresh','sv2-load','sv2-save','sv2-export','sv2-revision-load','sv2-prev','sv2-play','sv2-next','sv2-earlier','sv2-later','sv2-duplicate','sv2-remove','sv2-undo','sv2-upload','sv2-paste','sv2-smaller','sv2-larger','sv2-face-match','sv2-guide-add','sv2-guide-vertical','sv2-guide-remove','sv2-guide-copy'):
        current_markup_text=re.sub(r'<button id="'+current_control_identifier+r'">.*?</button>','',current_markup_text)
    current_markup_text=re.sub(r'<button data-sv2-move=.*?</button>','',current_markup_text)
    current_markup_text=re.sub(r'<div class="sv2-controls">.*?(?=<div class="sv2-fields">)','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<select id="sv2-projects".*?</select>','',current_markup_text)
    current_markup_text=re.sub(r'<select id="sv2-history".*?</select>','',current_markup_text)
    current_markup_text=re.sub(r'<h2>5. 저장 · 출력</h2>.*?</p>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<label>입력 대상 <select id="sv2-upload-target".*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<h1>.*?</h1>','',current_markup_text)
    current_markup_text=current_markup_text.replace('<h2>1. 작업</h2>','<h2>현재 작업 편집</h2>')
    current_markup_text=re.sub(r'<div class="sv2-toolbar"><label>화면 확대 .*?</div>','',current_markup_text,flags=re.S)
    current_markup_text=re.sub(r'<label>FPS <input id="sv2-fps".*?</label>','',current_markup_text)
    current_markup_text=re.sub(r'<label>현재 프레임 유지 ms <input id="sv2-duration".*?</label>','',current_markup_text)
    current_markup_text=current_markup_text.replace('<span>0은 FPS 기준</span>','<p id="sv2-timing-summary" role="status">작업을 불러와 재생 설정을 확인하세요.</p>')
    with gr.Blocks(title='스프라이트 정규화 편집기 v2') as current_interface_blocks:
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
        current_feedback_text=gr.Textbox(label='작업 안내',value='목록을 새로고침하여 저장된 작업을 선택하거나 새 작업을 만드세요.',interactive=False)
        with gr.Accordion('이미지 등록',open=True):
            current_upload_choice=gr.Dropdown(label='입력 대상',choices=[('레퍼런스','reference'),('프레임 추가','append'),('선택 프레임 교체','replace')],value='reference')
            current_upload_choice.input(fn=None,inputs=current_upload_choice,js="(currentTargetValue)=>{if(!window.spriteV2UploadTarget)throw Error('편집기를 준비 중입니다.');window.spriteV2UploadTarget(currentTargetValue);}",queue=False)
            gr.Markdown('작업을 먼저 생성하거나 불러오세요. PNG/JPEG/WebP · 한 장당 8MB · 최대 128프레임. 투명도를 유지하며 흰 배경은 제거하지 않습니다.')
            with gr.Row():
                build_browser_action_button('파일 불러오기','spriteV2UploadControls','upload',current_feedback_text)
                build_browser_action_button('클립보드 붙여넣기','spriteV2UploadControls','paste',current_feedback_text)
        with gr.Accordion('비교 화면 표시',open=True):
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
        gr.HTML(current_markup_text)
        with gr.Accordion('이동·배율·가이드 조정',open=True):
            gr.Markdown('위에서 편집 대상과 조절 대상을 선택하세요. 이동은 1px, 이미지 배율은 0.01씩 조정합니다.')
            with gr.Row():
                for current_edit_action,current_edit_label in (('move-up','위로 1px'),('move-left','왼쪽으로 1px'),('move-right','오른쪽으로 1px'),('move-down','아래로 1px')):
                    build_browser_action_button(current_edit_label,'spriteV2EditControls',current_edit_action,current_feedback_text)
            with gr.Row():
                build_browser_action_button('배율 −0.01','spriteV2EditControls','smaller',current_feedback_text)
                build_browser_action_button('배율 +0.01','spriteV2EditControls','larger',current_feedback_text)
            with gr.Row():
                for current_edit_action,current_edit_label in (('guide-add','가로선 추가'),('guide-vertical','세로선 추가'),('guide-remove','선택 가이드 삭제')):
                    build_browser_action_button(current_edit_label,'spriteV2EditControls',current_edit_action,current_feedback_text)
            with gr.Row():
                build_browser_action_button('레퍼런스 얼굴 원 크기 복사','spriteV2EditControls','face-match',current_feedback_text)
                build_browser_action_button('레퍼런스 가이드·얼굴 원 복사','spriteV2EditControls','guide-copy',current_feedback_text)
        gr.Markdown('### 프레임 편집\n선택한 프레임의 순서를 바꾸거나 복제·삭제합니다. 삭제는 실행 취소할 수 있으며 수정본 저장 전에는 저장된 작업을 바꾸지 않습니다.')
        with gr.Row():
            for current_frame_action,current_frame_label in (('earlier','프레임 앞으로'),('later','프레임 뒤로'),('duplicate','선택 프레임 복제'),('remove','선택 프레임 삭제'),('undo','실행 취소')):
                build_browser_action_button(current_frame_label,'spriteV2FrameControls',current_frame_action,current_feedback_text)
        with gr.Row():
            for current_playback_name,current_playback_label in (('prev','이전 프레임'),('play','재생 / 일시정지'),('next','다음 프레임')):
                build_browser_action_button(current_playback_label,'spriteV2PlaybackControls',current_playback_name,current_feedback_text)
        with gr.Accordion('재생 시간 조정',open=True):
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
        with gr.Row():
            current_history_button=gr.Button('수정 이력 새로고침')
            current_revision_button=gr.Button('선택 버전 불러오기')
        gr.Markdown('GIF는 흰 배경으로 검수합니다. 내보내기는 현재 편집을 새 수정본으로 저장한 후 다운로드합니다.')
        for current_action_name,current_action_button in (('create',current_create_button),('list',current_refresh_button),('load',current_load_button),('save',current_save_button),('export',current_export_button),('history',current_history_button),('revision',current_revision_button)):
            current_action_button.click(fn=None,inputs=[current_project_name,current_output_size,current_project_choice,current_revision_choice],outputs=[current_project_choice,current_feedback_text,current_revision_choice],js=create_sprite_project_script(current_action_name),queue=False)

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
