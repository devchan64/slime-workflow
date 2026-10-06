"""브라우저 프레임 재생·탐색을 위한 Gradio 공용 컨트롤."""
import json
import re

import gradio as gr


def build_frame_navigator(current_playback_handler, current_seek_handler, current_feedback_output):
    """1부터 시작하는 번호를 전달하며 실제 범위와 재생 상태는 편집기가 관리한다."""
    if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', current_seek_handler):
        raise ValueError('프레임 이동 함수 이름 형식 오류')
    current_frame_number,current_action_buttons,current_seek_button=build_frame_navigation_widgets()
    if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', current_playback_handler):
        raise ValueError('브라우저 명령 함수 이름 형식 오류')
    for current_action_name,current_action_button in current_action_buttons:
        current_action_script="""async()=>{try{
 const currentActionHandler=window[HANDLER];
 if(typeof currentActionHandler!=='function')throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');
 return await currentActionHandler(ACTION);
}catch(currentErrorValue){return currentErrorValue.message;}}""".replace('HANDLER',json.dumps(current_playback_handler)).replace('ACTION',json.dumps(current_action_name))
        current_action_button.click(fn=None,outputs=current_feedback_output,queue=False,js=current_action_script)
    current_seek_script="""async(currentFrameNumber)=>{
try{
 const currentSeekHandler=window[HANDLER];
 if(typeof currentSeekHandler!=='function')throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');
 return await currentSeekHandler(currentFrameNumber);
}catch(currentErrorValue){return currentErrorValue.message;}
}""".replace('HANDLER',json.dumps(current_seek_handler))
    for current_seek_event in (current_seek_button.click,current_frame_number.submit):
        current_seek_event(fn=None,inputs=current_frame_number,outputs=current_feedback_output,queue=False,js=current_seek_script)
    return current_frame_number


def build_frame_navigation_widgets():
    """편집기와 결과 플레이어가 공유하는 표준 탐색 UI를 구성한다."""
    with gr.Group():
        gr.Markdown('#### 프레임 탐색기')
        with gr.Row():
            current_action_buttons=[(current_action_name,gr.Button(current_button_label)) for current_action_name,current_button_label in (('prev','이전 프레임'),('next','다음 프레임'),('play','재생'),('stop','정지'))]
        with gr.Row():
            current_frame_number=gr.Number(label='이동할 프레임 번호',value=1,minimum=1,precision=0)
            current_seek_button=gr.Button('프레임으로 이동')
    return current_frame_number,current_action_buttons,current_seek_button
