"""Qwen 2511 3참조 생성기의 Gradio 클라이언트."""
import argparse
import base64
import html
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.management_gateway import execute_management_command

def execute_reference_gateway(command_name_value,payload_value):return execute_management_command('qwen-2511',command_name_value,payload_value)
def build_reference_request(prompt_text_value,reference_file_values,width_value,height_value,step_value,seed_value):
    reference_bytes_values=[] if not reference_file_values else list(reference_file_values)
    return {'action':'generate','prompt':prompt_text_value.strip(),'images':[base64.b64encode(current_file_value).decode() for current_file_value in reference_bytes_values],'width':int(width_value),'height':int(height_value),'steps':int(step_value),'seed':int(seed_value)}
def result_preview_html(image_url_value):return f'<img class="qwen-result-image" src="{html.escape(image_url_value,quote=True)}" alt="Qwen 생성 결과">' if image_url_value else '<div class="image-result-empty">완료된 결과를 선택하세요.</div>'

def build_qwen_2511_interface(server_base_address):
    with gr.Blocks(title='Qwen 2511 3참조 생성기') as interface_blocks_value:
        gr.Markdown('## Qwen 2511 3참조 생성기\n참조 이미지는 업로드한 순서대로 모델에 전달됩니다.')
        with gr.Row():
            with gr.Column(scale=1):
                prompt_text_value=gr.Textbox(label='프롬프트',lines=6)
                reference_file_values=gr.File(label='참조 PNG · 최대 3장 · 순서 유지',file_count='multiple',type='binary')
                gr.Markdown('참조 조건: 512×512 RGB/RGBA PNG, 투명 배경 불가. 순서를 바꾸려면 다시 업로드하세요.')
                with gr.Row():width_value=gr.Dropdown([512,768,1024,1280],value=1024,label='너비');height_value=gr.Dropdown([512,768,1024,1280],value=1024,label='높이')
                with gr.Row():step_value=gr.Radio([4,30],value=4,label='생성 스텝');seed_value=gr.Number(value=10107,precision=0,label='Seed')
                gr.Markdown('예상 시간: 실행 이력 기반 추정 자료를 수집 중입니다. 실행 로그에서 진행 단계를 확인하세요.')
                generation_button_value=gr.Button('이미지 생성 시작',variant='primary');status_value=gr.Markdown('생성 가능 · 설정을 확인하세요.');cancel_button_value=gr.Button('생성 취소')
            with gr.Column(scale=2):
                identifier_value=gr.Textbox(label='생성 ID',interactive=False);preview_value=gr.HTML(result_preview_html(None))
        log_value,refresh_log_value,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(execute_reference_gateway,server_base_address,'이력 목록만 초기화합니다. 결과 이미지·참조 입력 사본·로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',record_folder_route='/image-generation-2511')
        def start_generation(*input_values):
            generation_record_value=execute_reference_gateway('generate',build_reference_request(*input_values));return generation_record_value['id'],'상태: running'
        generation_button_value.click(start_generation,[prompt_text_value,reference_file_values,width_value,height_value,step_value,seed_value],[identifier_value,status_value])
        def refresh_status(identifier_text_value,refresh_log_enabled):
            if not identifier_text_value:return '생성 ID를 선택하세요.',gr.skip(),gr.skip()
            status_record_value=execute_reference_gateway('status',{'id':identifier_text_value});return '상태: '+status_record_value['status'],gr.update(value=status_record_value.get('log','')) if refresh_log_enabled else gr.skip(),result_preview_html(status_record_value.get('image')) if status_record_value.get('image') else gr.skip()
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values);gr.Button('상태 새로고침').click(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],show_progress='hidden')
        cancel_button_value.click(lambda identifier_text_value:execute_reference_gateway('cancel',{'id':identifier_text_value}),identifier_value,status_value)
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/three-reference-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda: (time.sleep(1),os._exit(0)) if os.getppid()!=arguments_value.owner_pid else None,daemon=True).start()
    build_qwen_2511_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=LOG_PANEL_STYLES+'.qwen-result-image{max-width:100%;max-height:700px}.image-result-empty{min-height:360px;display:grid;place-items:center}'+MANAGEMENT_DENSITY_STYLES,allowed_paths=[])
