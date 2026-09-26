"""공용 명령 게이트웨이를 사용하는 Qwen 2512 Gradio 클라이언트."""
import argparse
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

IMAGE_SIZE_VALUES=(512,768,1024,1280)
IMAGE_STEP_VALUES=(4,30)
DEFAULT_IMAGE_SEED=251204

def execute_image_gateway(command_name_value,payload_value):
    return execute_management_command('qwen-2512',command_name_value,payload_value)

def count_prompt_words(prompt_text_value):
    return len((prompt_text_value or '').split())

def build_generation_request(prompt_text_value,width_value,height_value,step_value,seed_value):
    return {'action':'generate','prompt':prompt_text_value.strip(),'width':int(width_value),'height':int(height_value),'steps':int(step_value),'seed':int(seed_value)}

def restore_generation_inputs(current_history_record):
    current_request_record=current_history_record.get('request',{})
    restored_prompt_text=current_request_record.get('prompt','')
    return restored_prompt_text,current_request_record.get('width',1024),current_request_record.get('height',1024),current_request_record.get('steps',4),current_request_record.get('seed',DEFAULT_IMAGE_SEED),f'최종 프롬프트: **{count_prompt_words(restored_prompt_text)}단어**','선택한 이력의 입력값을 불러왔습니다. 생성 전에 내용을 확인하세요.'

def format_generation_status(status_record_value):
    progress_record_value=status_record_value.get('progress') or {}
    progress_text_value=''
    if progress_record_value.get('total'):
        progress_text_value=f" · {progress_record_value.get('step',0)} / {progress_record_value['total']} 단계"
    elif progress_record_value.get('percent') is not None:
        progress_text_value=f" · {progress_record_value['percent']}%"
    detail_text_value=status_record_value.get('error') or status_record_value.get('message') or ''
    return f"상태: {status_record_value.get('status','unknown')}{progress_text_value}"+(f' · {detail_text_value}' if detail_text_value else '')

def create_result_preview_html(image_url_value):
    if not image_url_value:return '<div class="image-result-empty">완료된 결과 이미지를 선택하면 여기에 표시됩니다.</div>'
    return f'<img class="qwen-result-image" src="{html.escape(image_url_value,quote=True)}" alt="Qwen 생성 결과">'

def build_qwen_2512_interface(server_base_address):
    with gr.Blocks(title='Qwen 2512 이미지 생성기') as interface_blocks_value:
        gr.Markdown('## Qwen 2512 이미지 생성기\n프롬프트와 고정 생성 설정으로 이미지를 만들고, 실행 이력·로그·결과를 같은 기록에서 확인합니다.')
        with gr.Row():
            with gr.Column(scale=1,min_width=360):
                prompt_text_value=gr.Textbox(label='프롬프트',placeholder='생성할 장면을 짧고 구체적으로 입력하세요.',lines=8,max_lines=12)
                prompt_word_count_value=gr.Markdown('최종 프롬프트: **0단어**')
                with gr.Row():
                    width_select_value=gr.Dropdown(IMAGE_SIZE_VALUES,value=1024,label='너비')
                    height_select_value=gr.Dropdown(IMAGE_SIZE_VALUES,value=1024,label='높이')
                with gr.Row():
                    step_select_value=gr.Radio(IMAGE_STEP_VALUES,value=4,label='생성 스텝')
                    seed_number_value=gr.Number(value=DEFAULT_IMAGE_SEED,precision=0,label='Seed')
                gr.Markdown('예상 시간: 실행 이력 기반 추정 자료를 수집 중입니다. 실행 로그의 단계와 완료 시각을 확인하세요.')
                with gr.Row():
                    prepare_button_value=gr.Button('모델 준비 확인')
                    generation_button_value=gr.Button('이미지 생성 시작',variant='primary')
                model_status_value=gr.Markdown('모델 상태를 확인하세요.')
                generation_status_value=gr.Markdown('생성 가능 · 프롬프트를 입력하세요.')
                cancel_button_value=gr.Button('생성 취소')
            with gr.Column(scale=2,min_width=520):
                generation_identifier_value=gr.Textbox(label='생성 ID',interactive=False)
                result_preview_value=gr.HTML(create_result_preview_html(None))
        log_output_value,log_refresh_enabled,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(
            execute_image_gateway,
            server_base_address,
            '이력 목록만 초기화합니다. 결과 이미지와 로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',
            restore_input_callback=restore_generation_inputs,
            restore_output_components=[prompt_text_value,width_select_value,height_select_value,step_select_value,seed_number_value,prompt_word_count_value,generation_status_value],
            record_folder_route='/image-generation',
        )
        prompt_text_value.change(lambda prompt_text_value:f'최종 프롬프트: **{count_prompt_words(prompt_text_value)}단어**',prompt_text_value,prompt_word_count_value,queue=False)
        def check_model_ready():
            model_record_value=execute_image_gateway('model-status',{})
            return ('모델 준비됨 · '+model_record_value['message']) if model_record_value.get('ready') else ('모델 준비 필요 · '+model_record_value['message'])
        prepare_button_value.click(check_model_ready,outputs=model_status_value,queue=False)
        def start_generation(prompt_text_value,width_value,height_value,step_value,seed_value):
            generation_record_value=execute_image_gateway('generate',build_generation_request(prompt_text_value,width_value,height_value,step_value,seed_value))
            return generation_record_value['id'],'상태: running · 생성 작업을 시작했습니다.'
        generation_button_value.click(start_generation,[prompt_text_value,width_select_value,height_select_value,step_select_value,seed_number_value],[generation_identifier_value,generation_status_value])
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
        def refresh_generation_status(generation_identifier_value,refresh_log_enabled):
            if not generation_identifier_value:return '생성 ID를 선택하세요.',gr.skip(),gr.skip()
            status_record_value=execute_image_gateway('status',{'id':generation_identifier_value})
            log_update_value=gr.update(value=status_record_value.get('log','')) if refresh_log_enabled else gr.skip()
            result_update_value=create_result_preview_html(status_record_value.get('image')) if status_record_value.get('image') else gr.skip()
            return format_generation_status(status_record_value),log_update_value,result_update_value
        refresh_button_value=gr.Button('상태 새로고침')
        refresh_button_value.click(refresh_generation_status,[generation_identifier_value,log_refresh_enabled],[generation_status_value,log_output_value,result_preview_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_generation_status,[generation_identifier_value,log_refresh_enabled],[generation_status_value,log_output_value,result_preview_value],show_progress='hidden')
        def cancel_generation(generation_identifier_value):
            if not generation_identifier_value:raise gr.Error('취소할 생성 ID를 선택하세요.')
            cancel_record_value=execute_image_gateway('cancel',{'id':generation_identifier_value})
            return '상태: '+cancel_record_value['status']
        cancel_button_value.click(cancel_generation,generation_identifier_value,generation_status_value)
    return interface_blocks_value

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/image-generator/');arguments_value=parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    application_css_text=LOG_PANEL_STYLES+'''.qwen-result-image{display:block;max-width:100%;max-height:720px;margin:auto;border:1px solid #314055;border-radius:12px;background:#10151f}.image-result-empty{min-height:420px;display:grid;place-items:center;border:1px dashed #40516a;border-radius:12px;color:#a7b5c8}'''
    build_qwen_2512_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=application_css_text,allowed_paths=[])
