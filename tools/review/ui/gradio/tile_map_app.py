"""타일 에셋 생성기의 공용 게이트웨이 Gradio 클라이언트."""
import argparse
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.management_gateway import execute_management_command

def execute_tile_gateway(command_name_value,payload_value):return execute_management_command('tile-map',command_name_value,payload_value)
def build_tile_request(tile_type_value,user_prompt_value,width_value,step_value,seed_value,use_base_value,use_style_value,use_reference_style_value):
    return {'action':'generate','tile_type':tile_type_value,'user_prompt':user_prompt_value.strip(),'width':int(width_value),'height':int(width_value),'steps':int(step_value),'seed':int(seed_value),'use_base_prompt':use_base_value,'use_style_prompt':use_style_value,'use_reference_style_prompt':use_reference_style_value,'images':[]}
def build_tile_interface(server_base_address):
    catalog_record_value=execute_tile_gateway('catalog',{})
    tile_choices=[(record['label'],name) for name,record in catalog_record_value['types'].items()]
    with gr.Blocks(title='타일 에셋 생성기') as blocks_value:
        gr.Markdown('## 타일 에셋 생성기\n고정 기본·화풍 프롬프트와 사용자 요구를 결합해 정사각형 타일을 생성합니다.')
        with gr.Row():
            with gr.Column():
                tile_value=gr.Dropdown(tile_choices,value=tile_choices[0][1],label='타일 종류');prompt_value=gr.Textbox(label='사용자 프롬프트',lines=5)
                base_value=gr.Checkbox(value=True,label='기본 프롬프트 적용');style_value=gr.Checkbox(value=True,label='화풍 프롬프트 적용');reference_style_value=gr.Checkbox(value=False,label='참조 화풍 보존 적용')
                width_value=gr.Dropdown([512,768,1024],value=1024,label='정사각형 해상도');step_value=gr.Radio([4,30],value=4,label='생성 스텝');seed_value=gr.Number(value=10107,precision=0,label='Seed')
                start_value=gr.Button('타일 생성 시작',variant='primary');status_value=gr.Markdown('생성 가능 · 최종 프롬프트는 100단어 미만이어야 합니다.')
            with gr.Column():identifier_value=gr.Textbox(label='생성 ID',interactive=False);history_value=gr.Radio(choices=[],label='생성 이력');refresh_value=gr.Button('이력 새로고침')
        def start_tile(*input_values):
            record_value=execute_tile_gateway('generate',build_tile_request(*input_values));return record_value['id'],'상태: running'
        start_value.click(start_tile,[tile_value,prompt_value,width_value,step_value,seed_value,base_value,style_value,reference_style_value],[identifier_value,status_value])
        def refresh_history():
            records=execute_tile_gateway('history',{}).get('records',[]);return gr.update(choices=[(f"{record['id']} · {record.get('status',{}).get('status','unknown')}",record['id']) for record in records])
        blocks_value.load(refresh_history,outputs=history_value);refresh_value.click(refresh_history,outputs=history_value,queue=False)
    return blocks_value
if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/tile-map-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_tile_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path)
