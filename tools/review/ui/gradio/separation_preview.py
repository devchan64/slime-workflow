"""복장 분리 결과를 독립된 Gradio 캔버스와 공용 조작부로 표시한다."""
import json
import re
from pathlib import Path

import gradio as gr
from tools.review.common.gradio_frame_navigator import build_frame_navigator
from tools.review.common.gradio_joypad import build_transform_joypad, read_joypad_browser_script

SEPARATION_PLAYER_SCRIPT_PATH = Path(__file__).parents[1] / 'shared/separation-player.js'
SEPARATION_PLAYER_TEMPLATE = '<div data-player-images style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr))"></div><p data-player-status role="status">완료된 결과를 조회하세요.</p>@children'


def build_separation_player(current_player_identifier, current_player_visible=True):
    """결과 탭과 이력의 재생·합성 상태 및 명령 이름을 분리한다."""
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]+', current_player_identifier):
        raise ValueError('재생기 식별자 형식 오류')
    current_player_script = read_joypad_browser_script() + '\nconst currentPlayerIdentifier=' + json.dumps(current_player_identifier) + ';\n' + SEPARATION_PLAYER_SCRIPT_PATH.read_text()
    with gr.HTML(value='', visible=current_player_visible, elem_id=current_player_identifier, html_template=SEPARATION_PLAYER_TEMPLATE, js_on_load=current_player_script) as current_player_component:
        current_preview_feedback = gr.Textbox(label='비교·재생 안내', value='완료된 결과를 먼저 조회하세요.', interactive=False)
        current_view_choice = gr.Radio([('원본 · 합성', 'compare'), ('신체 · 복장', 'parts'), ('전체 비교', 'all')], value='compare', label='검수 보기',interactive=False)
        current_view_choice.input(fn=None, inputs=current_view_choice, outputs=current_preview_feedback, queue=False, js="currentViewName=>{try{return window[" + json.dumps(current_player_identifier + 'View') + "](currentViewName);}catch(currentErrorValue){return currentErrorValue.message;}}")
        current_navigation_controls=[]
        current_frame_input = build_frame_navigator(current_player_identifier + 'Playback', current_player_identifier + 'Seek', current_preview_feedback,current_navigation_controls)
        with gr.Accordion('겹쳐보기 위치·배율 조정', open=False):
            gr.Markdown('검수 화면에만 적용됩니다. 저장된 이미지는 바뀌지 않습니다.')
            current_transform_controls=[]
            current_transform_inputs = build_transform_joypad(current_player_identifier + 'Transform', current_preview_feedback,current_readiness_controls=current_transform_controls)
            current_reset_button = gr.Button('위치·배율 초기화',interactive=False)
            current_reset_button.click(fn=None, outputs=[*current_transform_inputs[:3], current_preview_feedback], queue=False, js="()=>{try{const currentResultRecord=window[" + json.dumps(current_player_identifier + 'Transform') + "]('reset',{});return [currentResultRecord.x,currentResultRecord.y,currentResultRecord.scale,currentResultRecord.message];}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
        current_readiness_notice=gr.Markdown('완료된 결과를 먼저 조회하세요. 로딩이 끝나면 비교·위치 조정을 사용할 수 있습니다.')
        current_ready_controls=[current_view_choice,*current_transform_controls,current_reset_button,*current_navigation_controls]
        current_control_updates=[]
        for current_control_value in current_ready_controls:
            current_enabled_expression='Boolean(currentReadyRecord.ready)'
            if getattr(current_control_value,'value',None)=='재생':current_enabled_expression+='&&currentReadyRecord.frameCount>1'
            elif getattr(current_control_value,'value',None)=='정지':current_enabled_expression+='&&Boolean(currentReadyRecord.playing)'
            current_control_updates.append("{__type__:'update',interactive:"+current_enabled_expression+"}")
        current_readiness_script="()=>{const currentReadyRecord=window["+json.dumps(current_player_identifier+'Readiness')+"]?.()??{ready:false,message:'재생기를 준비 중입니다. 잠시 후 다시 조회하세요.'};return ["+','.join(current_control_updates)+",currentReadyRecord.ready?(currentReadyRecord.frameCount===1?'단일 프레임입니다. 재생 없이 비교·위치 조정을 사용하세요.':'비교·재생·위치 조정을 사용할 수 있습니다. 정지는 재생 중에 활성화됩니다.'):currentReadyRecord.message];}"
        gr.Timer(0.5).tick(fn=None,outputs=[*current_ready_controls,current_readiness_notice],queue=False,js=current_readiness_script)
        current_player_component.change(lambda: ['compare', 1, 0, 0, 1, '프레임 표시 상태를 확인하고 재생·비교를 조작하세요.'], outputs=[current_view_choice, current_frame_input, *current_transform_inputs[:3], current_preview_feedback], queue=False)
    return current_player_component
