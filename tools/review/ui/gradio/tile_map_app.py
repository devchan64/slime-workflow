"""타일 에셋 생성기의 공용 게이트웨이 Gradio 클라이언트."""
import argparse
import base64
import io
import urllib.request
from PIL import Image
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.tile.tile_generation import REFERENCE_STYLE_PROMPT

def execute_tile_gateway(command_name_value,payload_value):return execute_management_command('tile-map',command_name_value,payload_value)
def build_tile_request(tile_type_value,user_prompt_value,width_value,step_value,seed_value,use_base_value,use_style_value,use_reference_style_value,*reference_image_values):
    encoded_reference_values=[]
    for current_reference_image in reference_image_values:
        if current_reference_image is None:continue
        image_output_buffer=io.BytesIO();current_reference_image.save(image_output_buffer,format='PNG')
        encoded_reference_values.append(base64.b64encode(image_output_buffer.getvalue()).decode())
    return {'action':'generate','tile_type':tile_type_value,'user_prompt':user_prompt_value.strip(),'width':int(width_value),'height':int(width_value),'steps':int(step_value),'seed':int(seed_value),'use_base_prompt':use_base_value,'use_style_prompt':use_style_value,'use_reference_style_prompt':use_reference_style_value,'images':encoded_reference_values}
def restore_tile_inputs(current_history_record,server_base_address):
    request_record_value=current_history_record['request']
    reference_name_values=request_record_value.get('references',[])
    if reference_name_values!=[f'reference-{index+1}.png' for index in range(len(reference_name_values))] or len(reference_name_values)>3:
        raise ValueError('저장된 참조 이미지 목록이 올바르지 않습니다.')
    restored_image_values=[]
    for current_reference_name in reference_name_values:
        reference_image_url=f"{server_base_address.rstrip('/')}/tile-map-generator/jobs/{current_history_record['id']}/{current_reference_name}"
        with urllib.request.urlopen(reference_image_url,timeout=15) as current_image_response:
            with Image.open(io.BytesIO(current_image_response.read())) as current_image_value:
                restored_image_values.append(current_image_value.copy())
    return [request_record_value['tile_type'],request_record_value['user_prompt'],request_record_value['width'],request_record_value['steps'],request_record_value['seed'],request_record_value.get('use_base_prompt',True),request_record_value.get('use_style_prompt',True),request_record_value.get('use_reference_style_prompt',False),*restored_image_values,*([None]*(3-len(restored_image_values))),'입력값과 참조 사본을 불러왔습니다. 고정 프롬프트는 현재 설정을 사용하며 자동 생성하지 않습니다.']

def build_tile_interface(server_base_address):
    catalog_record_value=execute_tile_gateway('catalog',{})
    tile_choices=[(record['label'],name) for name,record in catalog_record_value['types'].items()]
    with gr.Blocks(title='타일 에셋 생성기') as blocks_value:
        gr.Markdown('## 타일 에셋 생성기\n고정 기본·화풍 프롬프트와 사용자 요구를 결합해 정사각형 타일을 생성합니다.')
        with gr.Row():
            with gr.Column():
                tile_value=gr.Dropdown(tile_choices,value=tile_choices[0][1],label='타일 종류');prompt_value=gr.Textbox(label='사용자 프롬프트',lines=5)
                base_value=gr.Checkbox(value=True,label='기본 프롬프트 적용');style_value=gr.Checkbox(value=True,label='화풍 프롬프트 적용');reference_style_value=gr.Checkbox(value=False,label='참조 화풍 보존 적용')
                with gr.Accordion('참조 이미지 · 최대 3장',open=False):
                    reference_image_controls=[gr.Image(type='pil',label=f'참조 이미지 {index+1}') for index in range(3)]
                initial_base_prompt=catalog_record_value['types'][tile_choices[0][1]]['base_prompt']
                with gr.Accordion('기본 프롬프트 · 고정',open=False):
                    base_prompt_display=gr.Textbox(value=initial_base_prompt,label=f'기본 프롬프트 · {len(initial_base_prompt.split())}단어',interactive=False,lines=4)
                with gr.Accordion('화풍 프롬프트 · 고정',open=False):
                    gr.Textbox(value=catalog_record_value['style_prompt'],label=f"화풍 프롬프트 · {len(catalog_record_value['style_prompt'].split())}단어",interactive=False,lines=3)
                with gr.Accordion('참조 화풍 보존 프롬프트 · 고정',open=False):
                    gr.Textbox(value=REFERENCE_STYLE_PROMPT,label=f'참조 화풍 보존 · {len(REFERENCE_STYLE_PROMPT.split())}단어',interactive=False,lines=3)
                def update_base_prompt(selected_tile_kind):
                    current_prompt_text=catalog_record_value['types'][selected_tile_kind]['base_prompt']
                    return gr.update(value=current_prompt_text,label=f'기본 프롬프트 · {len(current_prompt_text.split())}단어')
                tile_value.change(update_base_prompt,inputs=tile_value,outputs=base_prompt_display,queue=False)
                width_value=gr.Dropdown([512,768,1024],value=512,label='정사각형 해상도');step_value=gr.Radio([4,30],value=4,label='생성 스텝');seed_value=gr.Number(value=10107,precision=0,label='Seed')
                start_value=gr.Button('타일 생성 시작',variant='primary');status_value=gr.Markdown('생성 가능 · 최종 프롬프트는 100단어 미만이어야 합니다.')
                identifier_value=gr.Textbox(label='실행 중 생성 ID',interactive=False)
            with gr.Column(scale=2):
                read_history_page,history_output_values=build_generation_history_view(execute_tile_gateway,server_base_address,'이력 목록만 초기화합니다. 결과·참조 사본·로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',lambda record:restore_tile_inputs(record,server_base_address),[tile_value,prompt_value,width_value,step_value,seed_value,base_value,style_value,reference_style_value,*reference_image_controls,status_value],record_folder_route='/tile-map-generator')
        def start_tile(*input_values):
            record_value=execute_tile_gateway('generate',build_tile_request(*input_values));return record_value['id'],'상태: running'
        start_value.click(start_tile,[tile_value,prompt_value,width_value,step_value,seed_value,base_value,style_value,reference_style_value,*reference_image_controls],[identifier_value,status_value])
        blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
    return blocks_value
if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/tile-map-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_tile_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path)
