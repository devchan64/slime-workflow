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
from tools.review.domains.tile.tile_generation import combine_tile_prompt

# 지붕 예시는 나무 판자가 배열된 표면을 지정한다.
ROOFTOP_TILE_PROMPT_EXAMPLE = '나무 판자가 배열된 표면'

WALL_TILE_KOREAN_EXAMPLE = '커다른 붉은 블록으로 이루어진 벽.'
SMALL_WINDOW_WALL_KOREAN_EXAMPLE = '이미지 1은 밖에서 보는 벽면이다. 실내가 보이지 않는 작은 창문은 상단에 추가한다.'
# 문 예시 출처: 2026-09-27_19-58-40-45f636bf
CLOSED_GATE_WALL_KOREAN_EXAMPLE = '벽면의 음각으로 닫힌 짙은색의 아치형 대문을 추가한다.'
GROUND_TILE_KOREAN_EXAMPLE = '진흙과 잔디'
BRICK_GROUND_PROMPT_EXAMPLE = '벽돌 바닥'

def format_applied_prompt_words(catalog_record_value,user_prompt_value,use_base_value,use_style_value,reference_usage_enabled=False,*reference_image_values):
    reference_images_present=reference_usage_enabled and any(image_value is not None for image_value in reference_image_values)
    prompt_section_values=[('기본',catalog_record_value['base_prompt'],use_base_value and not reference_images_present),('표면정보',user_prompt_value or '',True),('화풍',catalog_record_value['style_prompt'],use_style_value and not reference_images_present)]
    applied_word_counts=[(label,len(text.split()) if enabled else 0) for label,text,enabled in prompt_section_values]
    active_prompt_values=[text if enabled else '' for _,text,enabled in prompt_section_values]
    total_word_count=len(combine_tile_prompt(*active_prompt_values,reference_images_present=reference_images_present).split()) if any(text.strip() for text in active_prompt_values) else 0
    return '**적용 프롬프트 총 '+str(total_word_count)+'단어** · '+ ' + '.join(label+' '+str(count) for label,count in applied_word_counts)+'\n\n'+('⚠️ 100단어 미만으로 줄여 주세요.' if total_word_count>=100 else '100단어 미만 · 실제 모델 입력 기준입니다. 참조 이미지 사용 시 자동 접두어를 붙이지 않습니다.')


def update_reference_upload_visibility(reference_usage_enabled):
    return gr.update(visible=reference_usage_enabled)

def update_reference_prompt_controls(reference_usage_enabled,*reference_image_values):
    reference_images_present=reference_usage_enabled and any(image_value is not None for image_value in reference_image_values)
    control_update_values={'interactive':not reference_images_present,'info':'참조 이미지가 있으면 사용할 수 없습니다. 첨부 이미지 사용을 끄거나 모든 참조를 제거하면 다시 선택할 수 있습니다.' if reference_images_present else '참조 없이 생성할 때만 적용할 수 있습니다.'}
    if reference_images_present:control_update_values['value']=False
    return gr.update(**control_update_values),gr.update(**control_update_values)

def execute_tile_gateway(command_name_value,payload_value):return execute_management_command('tile-map',command_name_value,payload_value)
def generate_random_seed_value():return secrets.randbelow(4294967296)
def clear_user_prompt_value():return ''
def append_rooftop_tile_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if ROOFTOP_TILE_PROMPT_EXAMPLE in current_prompt_text:return current_prompt_text
    return ROOFTOP_TILE_PROMPT_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+ROOFTOP_TILE_PROMPT_EXAMPLE

def append_wall_tile_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if WALL_TILE_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return WALL_TILE_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+WALL_TILE_KOREAN_EXAMPLE
def append_small_window_wall_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if SMALL_WINDOW_WALL_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return SMALL_WINDOW_WALL_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+SMALL_WINDOW_WALL_KOREAN_EXAMPLE
def append_closed_gate_wall_example(current_prompt_value):
    current_prompt_text=(current_prompt_value or '').strip()
    if CLOSED_GATE_WALL_KOREAN_EXAMPLE in current_prompt_text:return current_prompt_text
    return CLOSED_GATE_WALL_KOREAN_EXAMPLE if not current_prompt_text else current_prompt_text+'\n'+CLOSED_GATE_WALL_KOREAN_EXAMPLE
def append_tile_prompt_example(current_prompt_value,selected_example_text):
    current_prompt_text=(current_prompt_value or '').strip()
    if selected_example_text in current_prompt_text:return current_prompt_text
    return selected_example_text if not current_prompt_text else current_prompt_text+'\n'+selected_example_text

def append_ground_tile_example(current_prompt_value):
    return append_tile_prompt_example(current_prompt_value,GROUND_TILE_KOREAN_EXAMPLE)

def append_brick_ground_example(current_prompt_value):
    return append_tile_prompt_example(current_prompt_value,BRICK_GROUND_PROMPT_EXAMPLE)
def build_tile_request(user_prompt_value,generation_tag_value,width_value,step_value,seed_value,use_base_value,use_style_value,reference_usage_enabled=False,*reference_image_values):
    encoded_reference_values=[]
    for current_reference_image in (reference_image_values if reference_usage_enabled else ()):
        if current_reference_image is None:continue
        image_output_buffer=io.BytesIO();current_reference_image.save(image_output_buffer,format='PNG')
        encoded_reference_values.append(base64.b64encode(image_output_buffer.getvalue()).decode())
    return {'action':'generate','user_prompt':user_prompt_value.strip(),'tag':generation_tag_value.strip(),'width':int(width_value),'height':int(width_value),'steps':int(step_value),'seed':int(seed_value),'use_base_prompt':use_base_value and not bool(encoded_reference_values),'use_style_prompt':use_style_value and not bool(encoded_reference_values),'images':encoded_reference_values}
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
    return [request_record_value['user_prompt'],request_record_value.get('tag',''),request_record_value['width'],request_record_value['steps'],request_record_value['seed'],request_record_value.get('use_base_prompt',True) and not bool(restored_image_values),request_record_value.get('use_style_prompt',True) and not bool(restored_image_values),bool(restored_image_values),*restored_image_values,*([None]*(3-len(restored_image_values))),'입력값과 참조 사본을 불러왔습니다. 고정 프롬프트는 현재 설정을 사용하며 자동 생성하지 않습니다.']

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
    with gr.Blocks(title='타일 에셋 생성기',js=HISTORY_CARD_SELECTION_SCRIPT,elem_classes=['management-generator-root']) as blocks_value:
        gr.Markdown('## 타일 에셋 생성기\n참조 이미지가 없을 때만 기본·화풍 프롬프트를 사용할 수 있습니다. 참조 이미지가 있으면 표면정보 지시만 사용합니다.')
        gr.Markdown('원본과 보더 크롭을 함께 저장합니다. 보더는 텍스처 가로·세로의 **1%를 각각 올림**하며 크롭 후 크기를 변경하지 않습니다.')
        with gr.Row():
            with gr.Column():
                prompt_value=gr.Textbox(label='표면정보 프롬프트',info='표면의 재질·색상·무늬 등 표면정보를 입력하세요.',lines=5)
                with gr.Row():
                    clear_prompt_button_value=gr.Button('표면정보 프롬프트 초기화',size='sm',scale=1)
                gr.Markdown('> **주의:** 프롬프트에 `타일`을 입력하면 분리된 타일 형태로 생성될 수 있습니다. 연속된 바닥이나 지면을 원하면 원하는 표면·재질·구성을 직접 설명하세요.')
                generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 이슬온 시장 외벽 후보',max_lines=1)
                base_value=gr.Checkbox(value=True,label='기본 프롬프트 적용');style_value=gr.Checkbox(value=True,label='화풍 프롬프트 적용')
                reference_usage_control=gr.Checkbox(value=False,label='첨부 이미지 사용',info='켜면 첨부 영역이 펼쳐집니다. 끄면 이미지를 보관하되 생성에 사용하지 않습니다.')
                with gr.Group(visible=False,elem_id='tile-reference-images',elem_classes=['reference-upload-panel']) as reference_upload_group:
                    gr.Markdown('### 참조 이미지\n최대 3장 · 이미지를 끌어놓거나 아래 버튼으로 추가하세요.')
                    with gr.Row(elem_classes=['tile-reference-upload-grid']):
                        reference_image_controls=[gr.Image(type='pil',sources=['upload','clipboard'],label=f'참조 이미지 {index+1}',height=230,scale=1,min_width=180,elem_classes=['reference-upload-card'],placeholder='이미지 끌어놓기') for index in range(3)]
                initial_base_prompt=catalog_record_value['base_prompt']
                with gr.Accordion('기본 프롬프트 · 고정',open=False):
                    base_prompt_display=gr.Textbox(value=initial_base_prompt,label=f'기본 프롬프트 · {len(initial_base_prompt.split())}단어',interactive=False,lines=4)
                with gr.Accordion('화풍 프롬프트 · 고정',open=False):
                    gr.Textbox(value=catalog_record_value['style_prompt'],label=f"화풍 프롬프트 · {len(catalog_record_value['style_prompt'].split())}단어",interactive=False,lines=3)
                clear_prompt_button_value.click(clear_user_prompt_value,outputs=prompt_value,queue=False)
                width_value=gr.Dropdown([512,768,1024],value=1024,label='정사각형 해상도');step_value=gr.Radio([4,30],value=4,label='생성 스텝')
                with gr.Group(elem_classes=['seed-control-group']):
                    with gr.Row():
                        seed_value=gr.Number(value=10107,precision=0,label='Seed',scale=4,min_width=0)
                        randomize_seed_value=gr.Button('무작위 생성',scale=1,min_width=120)
                randomize_seed_value.click(generate_random_seed_value,outputs=seed_value,queue=False)
                applied_prompt_summary=gr.Markdown(format_applied_prompt_words(catalog_record_value,'',True,True))
                def refresh_applied_prompt_words(surface_prompt_value,base_prompt_enabled,style_prompt_enabled,reference_usage_enabled,*reference_image_values):
                    return format_applied_prompt_words(catalog_record_value,surface_prompt_value,base_prompt_enabled,style_prompt_enabled,reference_usage_enabled,*reference_image_values)
                prompt_count_inputs=[prompt_value,base_value,style_value,reference_usage_control,*reference_image_controls]
                reference_usage_control.change(update_reference_upload_visibility,inputs=reference_usage_control,outputs=reference_upload_group,queue=False)
                for reference_image_control in [reference_usage_control,*reference_image_controls]:
                    reference_image_control.change(update_reference_prompt_controls,inputs=[reference_usage_control,*reference_image_controls],outputs=[base_value,style_value],queue=False)
                for prompt_count_component in prompt_count_inputs:
                    prompt_count_component.change(refresh_applied_prompt_words,inputs=prompt_count_inputs,outputs=applied_prompt_summary,queue=False)
                start_value=gr.Button('타일 생성 시작',variant='primary');status_value=gr.Markdown('생성 가능 · 최종 프롬프트는 100단어 미만이어야 합니다.')
                execution_refresh_value=gr.Button('진행 상태 새로고침')
                gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요.')
                identifier_value=gr.Textbox(label='실행 중 생성 ID',interactive=False)
        read_history_page,history_output_values=build_generation_history_view(execute_tile_gateway,server_base_address,'이력 목록만 초기화합니다. 결과·참조 사본·로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',lambda record:restore_tile_inputs(record,server_base_address),[prompt_value,generation_tag_value,width_value,step_value,seed_value,base_value,style_value,reference_usage_control,*reference_image_controls,status_value],record_folder_route='/tile-map-generator',allow_individual_delete=True)
        def start_tile(*input_values):
            record_value=execute_tile_gateway('generate',build_tile_request(*input_values));status_label_value='대기열에 추가했습니다. 생성 이력에서 작업 순서와 상태를 확인하세요.' if record_value['status']=='queued' else '생성을 시작했습니다. 새 요청은 확인 후 대기열에 추가할 수 있습니다.';return record_value['id'],status_label_value,gr.update(interactive=True)
        bind_gpu_generation_confirmation(start_value,start_tile,[prompt_value,generation_tag_value,width_value,step_value,seed_value,base_value,style_value,reference_usage_control,*reference_image_controls],[identifier_value,status_value,start_value])
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
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_tile_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=MANAGEMENT_SHARED_STYLES+(Path(__file__).parent/'tile-map-layout.css').read_text())
