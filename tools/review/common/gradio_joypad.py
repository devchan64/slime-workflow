"""브라우저 편집기에서 공유하는 위치·배율 조이패드."""
import json
import re

import gradio as gr

JOY_PAD_POSITION_STEP = 1
JOY_PAD_SCALE_STEP = 0.001


def build_transform_joypad(current_handler_name, current_feedback_output, current_scale_enabled=True, current_separate_axes=False):
    """명령 처리기는 action, payload를 받아 x/y/scale/message를 반환한다."""
    if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', current_handler_name):
        raise ValueError('조이패드 명령 함수 이름 형식 오류')
    with gr.Group():
        gr.Markdown('#### 위치·배율 조이패드\n현재 값 읽기로 선택 대상을 확인하세요. 방향 버튼은 현재 위치에서 이동하고, 수치 적용은 해당 항목만 변경합니다. 여러 대상은 첫 대상의 값을 표시하며, 배율은 이미지 배율입니다.' if current_scale_enabled else '#### 위치 조이패드\n현재 값 읽기로 선택 좌표를 확인하세요. 방향 버튼은 1px씩 이동하며 수치 적용은 해당 축만 변경합니다.')
        current_position_step=gr.Number(value=JOY_PAD_POSITION_STEP,visible=False)
        current_scale_step=gr.Number(value=JOY_PAD_SCALE_STEP,visible=False)
        with gr.Row():
            current_position_x=gr.Number(label='X 위치',value=0)
            current_position_y=gr.Number(label='Y 위치',value=0)
            current_scale_value=gr.Number(label='가로 배율' if current_separate_axes else '배율',value=1,step=JOY_PAD_SCALE_STEP,minimum=0.01,maximum=8,visible=current_scale_enabled)
        if current_separate_axes:
            current_vertical_scale=gr.Number(label='세로 배율',value=1,step=JOY_PAD_SCALE_STEP,minimum=0.01,maximum=8)
        current_input_fields=[current_position_x,current_position_y,current_scale_value,current_position_step,current_scale_step]
        current_output_fields=[current_position_x,current_position_y,current_scale_value,current_feedback_output]

        if current_separate_axes:
            current_input_fields.append(current_vertical_scale)
            current_output_fields.insert(3,current_vertical_scale)

        def bind_joypad_button(current_action_name,current_button_label):
            current_button_component=gr.Button(current_button_label)
            current_button_script="""async(currentPositionX,currentPositionY,currentScaleValue,currentPositionStep,currentScaleStep)=>{
try{
 const currentActionHandler=window[HANDLER];
 if(typeof currentActionHandler!=='function')throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');
 const currentResultRecord=await currentActionHandler(ACTION,{x:currentPositionX,y:currentPositionY,scale:currentScaleValue,positionStep:currentPositionStep,scaleStep:currentScaleStep});
 return [currentResultRecord.x,currentResultRecord.y,currentResultRecord.scale,currentResultRecord.message];
}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message];}
}""".replace('HANDLER',json.dumps(current_handler_name)).replace('ACTION',json.dumps(current_action_name))
            if current_separate_axes:
                current_button_script=current_button_script.replace('currentScaleStep)=>','currentScaleStep,currentVerticalScale)=>').replace('scale:currentScaleValue,','scaleX:currentScaleValue,scaleY:currentVerticalScale,').replace('currentResultRecord.scale,currentResultRecord.message','currentResultRecord.scaleX,currentResultRecord.scaleY,currentResultRecord.message').replace("{__type__:'update'},currentErrorValue.message","{__type__:'update'},{__type__:'update'},currentErrorValue.message")
            current_button_component.click(fn=None,inputs=current_input_fields,outputs=current_output_fields,queue=False,js=current_button_script)
            return current_button_component

        with gr.Row():
            bind_joypad_button('set-x','X 적용')
            bind_joypad_button('set-y','Y 적용')
            if current_scale_enabled:
                bind_joypad_button('set-scaleX' if current_separate_axes else 'set-scale','가로 배율 적용' if current_separate_axes else '배율 적용')
                if current_separate_axes:bind_joypad_button('set-scaleY','세로 배율 적용')
        for current_button_row in ((None,('up','↑ 위로'),None),(('left','← 왼쪽'),('read','현재 값 읽기'),('right','오른쪽 →')),(None,('down','↓ 아래로'),None)):
            with gr.Row():
                for current_button_record in current_button_row:
                    with gr.Column(min_width=0):
                        if current_button_record:
                            bind_joypad_button(*current_button_record)
        if current_scale_enabled:
            with gr.Row():
                bind_joypad_button('scaleX-down' if current_separate_axes else 'scale-down','가로 줄이기 −' if current_separate_axes else '배율 줄이기 −')
                bind_joypad_button('scaleX-up' if current_separate_axes else 'scale-up','가로 늘리기 +' if current_separate_axes else '배율 늘리기 +')
            if current_separate_axes:
                with gr.Row():
                    bind_joypad_button('scaleY-down','세로 줄이기 −')
                    bind_joypad_button('scaleY-up','세로 늘리기 +')
    return current_input_fields


def read_joypad_browser_script():
    """편집기 초기화 전에 공용 수치 계산기를 설치한다."""
    from pathlib import Path
    return (Path(__file__).parents[1]/'ui/shared/transform-joypad.js').read_text()
