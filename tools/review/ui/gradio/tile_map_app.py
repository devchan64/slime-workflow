"""타일 에셋 생성기의 공용 게이트웨이 Gradio 클라이언트."""
import argparse
import base64
import io
import urllib.request
from PIL import Image
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_history import HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.tile.tile_generation import REFERENCE_STYLE_PROMPT

WALL_TILE_KOREAN_EXAMPLE = '석재 벽면, 양옆에 기둥이 절반이 보이게 배치한다, 상단에 단을 배치한다.'
SMALL_WINDOW_WALL_KOREAN_EXAMPLE = '이미지 1은 밖에서 보는 벽면이다. 실내가 보이지 않는 작은 창문은 상단에 추가한다.'
GROUND_TILE_KOREAN_EXAMPLE = '불규칙한 모양의 커다란 평면 회색 대리석으로 6개로 이루어진 바닥'

def execute_tile_gateway(command_name_value,payload_value):return execute_management_command('tile-map',command_name_value,payload_value)
def generate_random_seed_value():return secrets.randbelow(4294967296)
def clear_user_prompt_value():return ''
def append_wall_tile_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if WALL_TILE_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return WALL_TILE_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+WALL_TILE_KOREAN_EXAMPLE
def append_small_window_wall_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if SMALL_WINDOW_WALL_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return SMALL_WINDOW_WALL_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+SMALL_WINDOW_WALL_KOREAN_EXAMPLE
def append_ground_tile_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if GROUND_TILE_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return GROUND_TILE_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+GROUND_TILE_KOREAN_EXAMPLE
def build_tile_request(tile_type_value,user_prompt_value,generation_tag_value,width_value,step_value,seed_value,use_base_value,use_style_value,use_reference_style_value,*reference_image_values):
    encoded_reference_values=[]
    for current_reference_image in reference_image_values:
        if current_reference_image is None:continue
        image_output_buffer=io.BytesIO();current_reference_image.save(image_output_buffer,format='PNG')
        encoded_reference_values.append(base64.b64encode(image_output_buffer.getvalue()).decode())
    return {'action':'generate','tile_type':tile_type_value,'user_prompt':user_prompt_value.strip(),'tag':generation_tag_value.strip(),'width':int(width_value),'height':int(width_value),'steps':int(step_value),'seed':int(seed_value),'use_base_prompt':use_base_value,'use_style_prompt':use_style_value,'use_reference_style_prompt':use_reference_style_value,'images':encoded_reference_values}
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
    return [request_record_value['tile_type'],request_record_value['user_prompt'],request_record_value.get('tag',''),request_record_value['width'],request_record_value['steps'],request_record_value['seed'],request_record_value.get('use_base_prompt',True),request_record_value.get('use_style_prompt',True),request_record_value.get('use_reference_style_prompt',False),*restored_image_values,*([None]*(3-len(restored_image_values))),'입력값과 참조 사본을 불러왔습니다. 고정 프롬프트는 현재 설정을 사용하며 자동 생성하지 않습니다.']

def refresh_tile_execution(current_generation_identifier):
    current_active_record=execute_tile_gateway('active',{})
    if current_active_record.get('running'):
        return current_active_record['id'],'GPU 작업이 실행 또는 대기 중입니다. 새 요청은 확인 후 대기열에 추가할 수 있습니다.',gr.update(interactive=True)
    current_status_message='실행 중인 작업이 없습니다. 생성 이력에서 결과와 실행 상태를 확인하세요.'
    if current_generation_identifier:
        current_status_record=execute_tile_gateway('status',{'id':current_generation_identifier})
        current_status_message='상태: '+str(current_status_record.get('status','unknown'))
    return current_generation_identifier or '',current_status_message,gr.update(interactive=True)

def build_tile_interface(server_base_address):
    catalog_record_value=execute_tile_gateway('catalog',{})
    tile_choices=[(record['label'],name) for name,record in catalog_record_value['types'].items()]
    with gr.Blocks(title='타일 에셋 생성기',js=HISTORY_CARD_SELECTION_SCRIPT,elem_classes=['management-generator-root']) as blocks_value:
        gr.Markdown('## 타일 에셋 생성기\n고정 기본·화풍 프롬프트와 사용자 요구를 결합해 정사각형 타일을 생성합니다.')
        with gr.Row():
            with gr.Column():
                tile_value=gr.Dropdown(tile_choices,value=tile_choices[0][1],label='타일 종류');prompt_value=gr.Textbox(label='사용자 프롬프트',lines=5)
                with gr.Row():
                    clear_prompt_button_value=gr.Button('사용자 프롬프트 초기화',size='sm',scale=1)
                    wall_example_button_value=gr.Button('벽 타일 한글 예시 넣기',visible=tile_choices[0][1]=='wall',size='sm',scale=1)
                    small_window_example_button_value=gr.Button('작은창문 한글 예시 넣기',visible=tile_choices[0][1]=='wall',size='sm',scale=1)
                    ground_example_button_value=gr.Button('바닥 타일 예시 넣기',visible=tile_choices[0][1]=='ground',size='sm',scale=1)
                gr.Markdown('> **주의:** 프롬프트에 `타일`을 입력하면 분리된 타일 형태로 생성될 수 있습니다. 연속된 바닥이나 지면을 원하면 원하는 표면·재질·구성을 직접 설명하세요.')
                generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 이슬온 시장 외벽 후보',max_lines=1)
                base_value=gr.Checkbox(value=True,label='기본 프롬프트 적용');style_value=gr.Checkbox(value=True,label='화풍 프롬프트 적용');reference_style_value=gr.Checkbox(value=False,label='참조 화풍 보존 적용')
                with gr.Accordion('참조 이미지 · 최대 3장',open=False,elem_id='tile-reference-images'):
                    with gr.Row(elem_classes=['tile-reference-upload-grid']):
                        reference_image_controls=[gr.Image(type='pil',sources=['upload','clipboard'],label=f'참조 이미지 {index+1}',height=160,scale=1,min_width=180) for index in range(3)]
                initial_base_prompt=catalog_record_value['types'][tile_choices[0][1]]['base_prompt']
                with gr.Accordion('기본 프롬프트 · 고정',open=False):
                    base_prompt_display=gr.Textbox(value=initial_base_prompt,label=f'기본 프롬프트 · {len(initial_base_prompt.split())}단어',interactive=False,lines=4)
                with gr.Accordion('화풍 프롬프트 · 고정',open=False):
                    gr.Textbox(value=catalog_record_value['style_prompt'],label=f"화풍 프롬프트 · {len(catalog_record_value['style_prompt'].split())}단어",interactive=False,lines=3)
                with gr.Accordion('참조 화풍 보존 프롬프트 · 고정',open=False):
                    gr.Textbox(value=REFERENCE_STYLE_PROMPT,label=f'참조 화풍 보존 · {len(REFERENCE_STYLE_PROMPT.split())}단어',interactive=False,lines=3)
                def update_base_prompt(selected_tile_kind):
                    current_prompt_text=catalog_record_value['types'][selected_tile_kind]['base_prompt']
                    return gr.update(value=current_prompt_text,label=f'기본 프롬프트 · {len(current_prompt_text.split())}단어'),gr.update(visible=selected_tile_kind=='wall'),gr.update(visible=selected_tile_kind=='wall'),gr.update(visible=selected_tile_kind=='ground')
                tile_value.change(update_base_prompt,inputs=tile_value,outputs=[base_prompt_display,wall_example_button_value,small_window_example_button_value,ground_example_button_value],queue=False)
                clear_prompt_button_value.click(clear_user_prompt_value,outputs=prompt_value,queue=False)
                wall_example_button_value.click(append_wall_tile_example,inputs=prompt_value,outputs=prompt_value,queue=False)
                small_window_example_button_value.click(append_small_window_wall_example,inputs=prompt_value,outputs=prompt_value,queue=False)
                ground_example_button_value.click(append_ground_tile_example,inputs=prompt_value,outputs=prompt_value,queue=False)
                width_value=gr.Dropdown([512,768,1024],value=512,label='정사각형 해상도');step_value=gr.Radio([4,30],value=4,label='생성 스텝')
                with gr.Group(elem_classes=['seed-control-group']):
                    with gr.Row():
                        seed_value=gr.Number(value=10107,precision=0,label='Seed',scale=4,min_width=0)
                        randomize_seed_value=gr.Button('무작위 생성',scale=1,min_width=120)
                randomize_seed_value.click(generate_random_seed_value,outputs=seed_value,queue=False)
                start_value=gr.Button('타일 생성 시작',variant='primary');status_value=gr.Markdown('생성 가능 · 최종 프롬프트는 100단어 미만이어야 합니다.')
                execution_refresh_value=gr.Button('진행 상태 새로고침')
                gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요.')
                identifier_value=gr.Textbox(label='실행 중 생성 ID',interactive=False)
        read_history_page,history_output_values=build_generation_history_view(execute_tile_gateway,server_base_address,'이력 목록만 초기화합니다. 결과·참조 사본·로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',lambda record:restore_tile_inputs(record,server_base_address),[tile_value,prompt_value,generation_tag_value,width_value,step_value,seed_value,base_value,style_value,reference_style_value,*reference_image_controls,status_value],record_folder_route='/tile-map-generator',allow_individual_delete=True)
        def start_tile(*input_values):
            record_value=execute_tile_gateway('generate',build_tile_request(*input_values));status_label_value='대기열에 추가했습니다. 생성 이력에서 작업 순서와 상태를 확인하세요.' if record_value['status']=='queued' else '생성을 시작했습니다. 새 요청은 확인 후 대기열에 추가할 수 있습니다.';return record_value['id'],status_label_value,gr.update(interactive=True)
        bind_gpu_generation_confirmation(start_value,start_tile,[tile_value,prompt_value,generation_tag_value,width_value,step_value,seed_value,base_value,style_value,reference_style_value,*reference_image_controls],[identifier_value,status_value,start_value])
        blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
        execution_output_values=[identifier_value,status_value,start_value]
        execution_refresh_value.click(refresh_tile_execution,identifier_value,execution_output_values,queue=False)
        blocks_value.load(refresh_tile_execution,identifier_value,execution_output_values)
        if hasattr(gr,'Timer'):gr.Timer(3).tick(refresh_tile_execution,identifier_value,execution_output_values,queue=False)

    return blocks_value
from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()
MANAGEMENT_SHARED_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management.css').read_text()+MANAGEMENT_DENSITY_STYLES

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/tile-map-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_tile_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=MANAGEMENT_SHARED_STYLES)
