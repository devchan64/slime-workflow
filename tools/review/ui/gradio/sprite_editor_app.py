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
    for current_button_name in ('prev','play','stop','next','undo','reset'):
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
    return '<main id="sprite-editor-root">'+current_markup_text+'</main>'

def create_sprite_editor_loader(review_server_port):
    return f"""()=>{{{read_joypad_browser_script()}
window.spriteEditorServerBase='http://127.0.0.1:{review_server_port}';const currentScriptElement=document.querySelector('script[data-sprite-editor-component]');if(currentScriptElement)return;const nextScriptElement=document.createElement('script');nextScriptElement.src=window.spriteEditorServerBase+'/character-animation/sprite-editor.js';nextScriptElement.dataset.spriteEditorComponent='true';document.body.append(nextScriptElement);}}"""

def build_sprite_editor_interface(review_server_port):
    with gr.Blocks(title='스프라이트 정규화 편집기') as interface_blocks_value:
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
        build_transform_joypad('spriteEditorJoypadControls',current_playback_feedback)
        with gr.Row():
            for current_action_name,current_action_label in (('undo','실행 취소'),('reset','선택 프레임 원본 복원')):
                build_browser_action_button(current_action_label,'spriteEditorEditControls',current_action_name,current_playback_feedback)
        gr.HTML(read_sprite_editor_markup())
    return interface_blocks_value



if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/sprite-editor/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start()
    build_sprite_editor_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=read_sprite_editor_styles(),js=create_sprite_editor_loader(arguments_value.review_port),allowed_paths=[])
