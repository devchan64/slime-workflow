"""표준 Gradio 조작부와 브라우저 프레임 재생을 연결한다."""
from pathlib import Path
import json
import re

import gradio as gr
from tools.review.common.gradio_frame_navigator import build_frame_navigation_widgets

FRAME_PLAYER_SCRIPT_PATH=Path(__file__).resolve().parents[1]/'ui/shared/frame-player.js'
FRAME_PLAYER_DIRECTION_CHOICES=[('등록 첫 방향','first'),('전방 좌측','down_left'),('전방 우측','down_right'),('후방 좌측','up_left'),('후방 우측','up_right')]


def build_browser_frame_player(current_player_identifier='generation-result-player',initial_player_payload='',current_player_visible=False,defer_image_loading=False):
    """결과 JSON만 서버에서 받고 이동·재생은 브라우저 안에서 수행한다."""
    if not re.fullmatch(r'[a-z][a-z0-9-]+',current_player_identifier):
        raise ValueError('재생기 식별자 형식 오류')
    current_direction_argument="'first'" if defer_image_loading else 'direction'
    current_player_script='const currentPlayerIdentifier='+json.dumps(current_player_identifier)+';'+FRAME_PLAYER_SCRIPT_PATH.read_text()
    with gr.HTML(value=initial_player_payload,visible=current_player_visible,elem_id=current_player_identifier,html_template='<div data-player-images style="display:flex;flex-wrap:wrap"></div><p data-player-status role="status">결과를 조회하세요.</p>@children',js_on_load=current_player_script) as current_player_component:
        with gr.Row():
            current_direction_component=gr.State('first') if defer_image_loading else gr.Dropdown(FRAME_PLAYER_DIRECTION_CHOICES,value='first',label='재생 방향')
            current_framerate_component=gr.Dropdown([4,8,12,16],value=8,label='재생 FPS')
        current_feedback_component=gr.Textbox(label='재생 조작 안내',interactive=False,value='결과를 조회한 뒤 재생하거나 프레임을 이동하세요.')
        current_load_button=gr.Button('미리보기 불러오기') if defer_image_loading else None
        current_frame_component,current_navigation_buttons,current_seek_button=build_frame_navigation_widgets()
        current_action_buttons=[('previous' if current_action_name=='prev' else current_action_name,current_action_button) for current_action_name,current_action_button in current_navigation_buttons]
        current_action_buttons.append(('seek',current_seek_button))
        if defer_image_loading:
            current_action_buttons.insert(0,('load',current_load_button))
        for current_action_name,current_button_component in current_action_buttons:
            current_button_component.click(fn=None,inputs=[current_direction_component,current_framerate_component,current_frame_component],outputs=current_feedback_component,queue=False,js="(direction, fps, frame)=>{try {return window.generationFramePlayerCommands["+json.dumps(current_player_identifier)+"]('"+current_action_name+"',"+current_direction_argument+",fps,frame);}catch(error){return '재생기를 준비하지 못했습니다. 결과를 다시 조회하세요. '+error.message;}}")
        current_configuration_script="(direction,fps,frame)=>{try{return window.generationFramePlayerCommands["+json.dumps(current_player_identifier)+"]('configure',"+current_direction_argument+",fps,frame);}catch(error){return '재생기를 준비 중입니다.';}}"
        for current_control_component in ([current_framerate_component] if defer_image_loading else [current_direction_component,current_framerate_component]):
            current_control_component.input(fn=None,inputs=[current_direction_component,current_framerate_component,current_frame_component],outputs=current_feedback_component,queue=False,js=current_configuration_script)
    return current_player_component
