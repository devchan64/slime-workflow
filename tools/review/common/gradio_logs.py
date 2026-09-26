"""Gradio 관리도구의 공용 실행 로그 패널."""
import inspect
import gradio as gr

LOG_PANEL_STYLES = '.management-log-output textarea{font-family:ui-monospace,monospace!important;font-size:13px!important;line-height:1.65!important;background:#0d1420!important;color:#c8d7e9!important;overflow:auto!important;resize:vertical!important}'

def create_copyable_log_textbox(**textbox_keyword_values):
    copy_option_name='show_copy_button' if 'show_copy_button' in inspect.signature(gr.Textbox).parameters else 'buttons'
    textbox_keyword_values[copy_option_name]=True if copy_option_name=='show_copy_button' else ['copy']
    return gr.Textbox(**textbox_keyword_values)

def build_execution_logs():
    with gr.Accordion('실행 로그 · 펼쳐서 확인',open=False) as log_panel_element:
        with gr.Row():
            log_refresh_enabled=gr.Checkbox(value=True,label='자동 갱신 · 끄면 현재 내용을 유지합니다')
            log_follow_enabled=gr.Checkbox(value=True,label='최신 줄 따라가기')
            log_latest_button=gr.Button('마지막 줄로 이동')
        gr.Markdown('선택한 작업의 최근 12,000자를 표시합니다. 전체 로그는 기록 폴더의 worker.log에 보존됩니다. 복사 버튼으로 표시된 내용을 복사할 수 있습니다.')
        log_output_element=create_copyable_log_textbox(label='작업을 선택하세요',lines=18,max_lines=30,interactive=False,autoscroll=False,elem_id='management-execution-log',elem_classes=['management-log-output'])
    # Gradio의 autoscroll은 갱신 때 부모 페이지까지 이동시킬 수 있다. 로그 내부 이동은 명시적 버튼으로만 수행한다.
    log_follow_enabled.change(lambda follow_enabled:gr.update(autoscroll=False),log_follow_enabled,log_output_element,queue=False)
    log_scroll_script="() => {requestAnimationFrame(()=>{const element=document.querySelector('#management-execution-log textarea');if(element)element.scrollTop=element.scrollHeight;});}"
    log_latest_button.click(fn=None,js=log_scroll_script,queue=False)
    return log_output_element,log_refresh_enabled,log_panel_element
