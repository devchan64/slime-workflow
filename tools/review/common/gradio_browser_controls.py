"""브라우저 편집 상태를 사용하는 기본 Gradio 명령 버튼."""
import json
import re

import gradio as gr


def build_browser_action_button(current_button_label, current_handler_name, current_action_name, current_feedback_output):
    """고정된 공개 JS 명령에 연결하며 서버 이벤트·숨긴 버튼 클릭을 만들지 않는다."""
    if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', current_handler_name):
        raise ValueError('브라우저 명령 함수 이름 형식 오류')
    current_handler_json=json.dumps(current_handler_name)
    current_action_json=json.dumps(current_action_name)
    current_button_component=gr.Button(current_button_label)
    current_button_component.click(fn=None,outputs=current_feedback_output,queue=False,js=f"""async()=>{{
try{{
 const currentActionHandler=window[{current_handler_json}];
 if(typeof currentActionHandler!=='function')throw Error('편집기를 준비 중입니다. 잠시 후 다시 시도하세요.');
 return await currentActionHandler({current_action_json});
}}catch(currentActionError){{return currentActionError.message;}}
}}""")
    return current_button_component
