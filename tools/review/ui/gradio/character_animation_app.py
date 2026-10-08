"""공용 게이트웨이를 사용하는 캐릭터 애니메이션 Gradio 클라이언트."""
import argparse
import base64
import io
from PIL import Image
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_frame_player import build_browser_frame_player
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.management_client import execute_remote_management_command as execute_management_command

from tools.review.domains.character_animation.character_animation_assets import compose_direction_prompts

DIRECTION_LABEL_VALUES=[('전방 좌측','down_left'),('전방 우측','down_right'),('후방 좌측','up_left'),('후방 우측','up_right')]

def execute_animation_gateway(command_name_value, payload_value):
    return execute_management_command('character-animation',command_name_value,payload_value)

def read_animation_catalog():
    return execute_animation_gateway('catalog',{})

def format_unavailable_asset_notice(catalog_record_value):
    unavailable_asset_records = catalog_record_value.get('unavailable_assets',[])
    if not unavailable_asset_records:
        return ''
    notice_lines = ['### 일부 등록 자산을 사용할 수 없습니다', '파일이 교체·삭제된 자산은 선택지에서 제외했습니다. 자산을 복구하거나 설정을 갱신하면 다음 새로고침부터 다시 표시됩니다.']
    for asset_record_value in unavailable_asset_records:
        asset_kind_label = '모션' if asset_record_value['kind']=='motion' else '캐릭터'
        notice_lines.append(f"- **{asset_kind_label} · {asset_record_value['label']}**: {asset_record_value['reason']}")
    return '\n\n'.join(notice_lines)

def select_motion_prompt_values(catalog_record_value, selected_motion_name):
    selected_motion_record=next(record for record in catalog_record_value['motions'] if record['id']==selected_motion_name)
    return selected_motion_record['prompts']

def describe_motion_prompt_words(catalog_record_value, selected_motion_name, *direction_prompt_values):
    selected_prompt_values=select_motion_prompt_values(catalog_record_value,selected_motion_name)
    auxiliary_prompt_values={direction_name_value:prompt_text_value for (_,direction_name_value),prompt_text_value in zip(DIRECTION_LABEL_VALUES,direction_prompt_values)}
    final_prompt_records=compose_direction_prompts(selected_prompt_values,auxiliary_prompt_values)
    summary_line_values=[f"기본 {len(selected_prompt_values['base'].split())}단어 · 전방 공통 보조 {len(selected_prompt_values['auxiliary'].split())}단어 · 후방 공통 보조 {len(selected_prompt_values['auxiliary_rear'].split())}단어"]
    for direction_label_text,direction_name_value in DIRECTION_LABEL_VALUES:
        extra_prompt_words=len(auxiliary_prompt_values.get(direction_name_value,'').split())
        summary_line_values.append(f"{direction_label_text}: 추가 보조 {extra_prompt_words}단어 · 최종 {final_prompt_records[direction_name_value]['words']}단어")
    return '  \n'.join(summary_line_values)

def build_animation_request(motion_name_value,current_reference_image,source_name_value,selected_direction_name,start_frame_value,end_frame_value,resolution_value,step_value,target_fps_value,speed_value,generation_tag_value,*direction_prompt_values):
    if current_reference_image is None:
        raise ValueError('캐릭터 참조 이미지를 불러오거나 붙여넣으세요.')
    if selected_direction_name not in dict((value,label) for label,value in DIRECTION_LABEL_VALUES):
        raise ValueError('생성 방향을 하나 선택하세요.')
    current_image_buffer=io.BytesIO()
    current_reference_image.save(current_image_buffer,format='PNG')
    return {'motion':motion_name_value,'character_image':base64.b64encode(current_image_buffer.getvalue()).decode(),'source':source_name_value,'directions':[selected_direction_name],'start_frame':start_frame_value,'end_frame':end_frame_value,'resolution':resolution_value,'steps':step_value,'target_fps':target_fps_value,'speed':speed_value,'tag':generation_tag_value.strip(),'direction_auxiliary_prompts':{direction: text for (_,direction),text in zip(DIRECTION_LABEL_VALUES,direction_prompt_values or ['']*4)}}

def restore_animation_inputs(current_history_record):
    current_request_record=current_history_record.get('request',{})
    current_reference_image=None
    if current_request_record.get('character_image'):
        from tools.review.domains.character_animation.character_animation_assets import decode_character_reference
        with Image.open(io.BytesIO(decode_character_reference(current_request_record['character_image']))) as current_image_value:
            current_reference_image=current_image_value.copy()
    return current_request_record.get('motion'),current_reference_image,current_request_record.get('source','anny'),(current_request_record.get('directions') or ['down_left'])[0],current_request_record.get('start_frame',1),current_request_record.get('end_frame'),current_request_record.get('resolution',512),current_request_record.get('steps',4),8,(current_request_record.get('speed',2) if current_request_record.get('target_fps') == 8 and current_request_record.get('speed',2) in (1,2,4) else 2),current_request_record.get('tag',''),*[current_request_record.get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES],'선택한 이력의 입력값을 불러왔습니다. 이전 FPS·미지원 배속 이력은 신규 생성 기준 8 FPS·2배로 설정합니다. 첫 번째 방향을 선택합니다. 참조 이미지가 비어 있으면 다시 첨부하세요.'

def calculate_preview_frame_numbers(selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio):
    if type(target_frame_rate) is not int or target_frame_rate != 8:
        raise ValueError('타겟 FPS는 8만 지원합니다.')
    if type(generation_speed_ratio) not in (int,float) or generation_speed_ratio not in (1,2,4):
        raise ValueError('생성 배속은 1·2·4 중 하나여야 합니다.')
    selected_range_frame_count=selected_end_frame-selected_start_frame+1
    selected_frame_count=math.ceil(selected_range_frame_count/generation_speed_ratio)
    return [selected_start_frame+math.floor(frame_index_value*generation_speed_ratio) for frame_index_value in range(selected_frame_count)]


def clamp_selected_frame_range(selected_start_frame,selected_end_frame,maximum_frame_number):
    normalized_start_frame=selected_start_frame if type(selected_start_frame) is int else 1
    normalized_end_frame=selected_end_frame if type(selected_end_frame) is int else maximum_frame_number
    normalized_start_frame=max(1,min(normalized_start_frame,maximum_frame_number))
    normalized_end_frame=max(normalized_start_frame,min(normalized_end_frame,maximum_frame_number))
    return normalized_start_frame,normalized_end_frame

def create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio,server_base_address):
    if type(selected_start_frame) is not int or type(selected_end_frame) is not int or selected_start_frame > selected_end_frame:
        return '<div>시작 프레임과 종료 프레임을 확인하세요.</div>'
    selected_frame_numbers=calculate_preview_frame_numbers(selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio)
    frame_url_values=[f'{server_base_address}/character-animation/asset/{selected_motion_name}/{selected_source_kind}/{selected_direction_name}/{frame_number}' for frame_number in selected_frame_numbers]
    return json.dumps({'frames':{selected_direction_name:frame_url_values},'sourceFrames':{selected_direction_name:selected_frame_numbers},'fps':target_frame_rate,'directUrls':True,'deferLoading':True},ensure_ascii=False)

def create_animation_player(generation_job_identifier,generation_status_record,server_base_address):
    result_record_value=generation_status_record.get('result') or {}
    frame_values=result_record_value.get('frames',{})
    player_payload_value={'id':generation_job_identifier,'frames':frame_values,'fps':result_record_value.get('fps',4),'base':server_base_address}
    return json.dumps(player_payload_value,ensure_ascii=False)

def build_character_animation_interface(server_base_address):
    catalog_record_value=read_animation_catalog()
    motion_choice_values=[(record['label'],record['id']) for record in catalog_record_value['motions']]
    motion_catalog_records={record['id']:record for record in catalog_record_value['motions']}
    motion_frame_count_values={motion_identifier_value:motion_record_value['frames'] for motion_identifier_value,motion_record_value in motion_catalog_records.items()}
    def restore_registered_animation_inputs(current_history_record):
        current_status_record=execute_animation_gateway('status',{'id':current_history_record['id']})
        restored_input_values=list(restore_animation_inputs(current_status_record))
        if restored_input_values[0] not in motion_frame_count_values:
            raise gr.Error('폐기된 모션의 입력은 복원할 수 없습니다. 등록된 모션을 선택하세요.')
        selected_frame_count=motion_frame_count_values[restored_input_values[0]]
        restored_start_frame,restored_end_frame=clamp_selected_frame_range(restored_input_values[4],restored_input_values[5],selected_frame_count)
        restored_input_values[4]=gr.update(value=restored_start_frame,maximum=selected_frame_count)
        restored_input_values[5]=gr.update(value=restored_end_frame,maximum=selected_frame_count)
        return restored_input_values

    with gr.Blocks(title='캐릭터 애니메이션 생성기') as interface_blocks_value:
        gr.Markdown('## 캐릭터 애니메이션 생성기\n등록된 모션과 첨부한 캐릭터 참조 한 장으로 선택 방향의 프레임을 생성합니다.')
        unavailable_asset_notice = format_unavailable_asset_notice({**catalog_record_value,'unavailable_assets':[current_asset_record for current_asset_record in catalog_record_value.get('unavailable_assets',[]) if current_asset_record['kind']=='motion']})
        if unavailable_asset_notice:
            gr.Markdown(unavailable_asset_notice)
        if not motion_choice_values:
            missing_asset_kind_values = []
            if not motion_choice_values:missing_asset_kind_values.append('모션')
            gr.Markdown('> ⚠️ 사용할 수 있는 '+ '·'.join(missing_asset_kind_values) +' 자산이 없어 새 생성을 시작할 수 없습니다. 위 안내를 확인한 뒤 자산 또는 등록 설정을 갱신하세요.')
            return interface_blocks_value
        with gr.Column(elem_classes=['character-animation-workspace']):
            with gr.Column():
                gr.Markdown('### 생성 설정')
                with gr.Row():
                    motion_select_value=gr.Dropdown(motion_choice_values,value=motion_choice_values[0][1],label='모션')
                _,current_reference_controls=build_reference_image_inputs(reference_slot_count=1,reference_image_mode='RGBA',reference_slot_labels=['캐릭터 참조'])
                character_select_value=current_reference_controls[0]
                gr.Markdown('선택한 방향의 캐릭터 이미지 한 장을 첨부하세요. PNG · 최대 4096px·8MB. 원본을 보관하고 생성 시 비율을 유지해 512×512 흰 배경에 맞춥니다.')
                with gr.Row():
                    source_select_value=gr.Radio([('ANNY','anny'),('OpenPose','openpose')],value='anny',label='포즈 입력')
                    direction_select_value=gr.Radio(DIRECTION_LABEL_VALUES,value='down_left',label='생성 방향')
                initial_motion_frame_count=motion_frame_count_values[motion_choice_values[0][1]]
                with gr.Row():
                    start_frame_value=gr.Slider(value=1,minimum=1,maximum=initial_motion_frame_count,step=1,label='시작 프레임',elem_classes=['management-frame-slider'])
                    end_frame_value=gr.Slider(value=initial_motion_frame_count,minimum=1,maximum=initial_motion_frame_count,step=1,label='종료 프레임',elem_classes=['management-frame-slider'])
                with gr.Row():
                    resolution_select_value=gr.Dropdown([512,768,1024,1280],value=512,label='해상도')
                    step_select_value=gr.Radio([4,30],value=4,label='생성 스텝')
                with gr.Row():
                    target_fps_select_value=gr.Dropdown([8],value=8,label='타겟 FPS',info='재생은 8 FPS 고정입니다. 생성 배속 2는 원본 1·3·5… 프레임을 선택합니다.')
                    speed_select_value=gr.Dropdown([1,2,4],value=2,label='생성 배속')
                generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 돌온재 걷기 후보',max_lines=1)
                prompt_text_value=gr.Textbox(value=select_motion_prompt_values(catalog_record_value,motion_choice_values[0][1])['base'],label='선택 모션의 고정 기본 프롬프트',interactive=False,lines=4)
                reset_base_prompt_button=gr.Button('기본 프롬프트 초기화',size='sm')
                with gr.Accordion('방향별 보조 프롬프트 · 선택 사항',open=False):
                    gr.Markdown('비워 두면 추가 지시 없이 생성합니다. 입력한 내용은 해당 방향의 고정 프롬프트 뒤에 추가됩니다.')
                    direction_prompt_components=[]
                    for direction_label_text,direction_name_value in DIRECTION_LABEL_VALUES:
                        direction_prompt_components.append(gr.Textbox(value=motion_catalog_records[motion_choice_values[0][1]].get('direction_auxiliary_prompts',{}).get(direction_name_value,''),label=direction_label_text+' 보조 프롬프트',lines=2))
                    reset_auxiliary_prompt_button=gr.Button('보조 프롬프트 초기화',size='sm')
                    gr.Markdown('초기화하면 선택한 모션의 기본 보조 문구로 복원합니다. 기본 문구가 없으면 빈 값으로 복원합니다.')
                prompt_word_count_value=gr.Markdown(describe_motion_prompt_words(catalog_record_value,motion_choice_values[0][1],*[motion_catalog_records[motion_choice_values[0][1]].get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES]))
                def reset_base_prompt_value(selected_motion_name):
                    return select_motion_prompt_values(read_animation_catalog(),selected_motion_name)['base']
                def reset_auxiliary_prompt_values(selected_motion_name):
                    current_catalog_record=read_animation_catalog()
                    selected_motion_record=next(record for record in current_catalog_record['motions'] if record['id']==selected_motion_name)
                    return [selected_motion_record.get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES]
                reset_base_prompt_button.click(reset_base_prompt_value,inputs=motion_select_value,outputs=prompt_text_value,queue=False)
                reset_auxiliary_prompt_button.click(reset_auxiliary_prompt_values,inputs=motion_select_value,outputs=direction_prompt_components,queue=False)
            with gr.Accordion('입력 포즈 미리보기',open=False):
                preview_direction_value=gr.Dropdown(DIRECTION_LABEL_VALUES,value='down_left',label='미리보기 방향')
                generation_identifier_value=gr.State('')
                initial_motion_record=motion_catalog_records[motion_choice_values[0][1]]
                motion_preview_html_value=build_browser_frame_player('motion-preview-player',create_motion_preview_player(motion_choice_values[0][1],'anny','down_left',1,initial_motion_frame_count,initial_motion_record['fps'],8,2,server_base_address),current_player_visible=True,defer_image_loading=True)
            generation_pending_value=gr.State(False)
            generation_button_value=gr.Button('애니메이션 생성 시작',variant='primary',elem_id='character-generation-start')
            status_text_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
        logs_text_value,log_refresh_enabled,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(execute_animation_gateway,server_base_address,'이력 목록만 초기화합니다. 생성 프레임과 로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',restore_input_callback=restore_registered_animation_inputs,restore_output_components=[motion_select_value,character_select_value,source_select_value,direction_select_value,start_frame_value,end_frame_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value,generation_tag_value,*direction_prompt_components,status_text_value],result_renderer_callback=create_animation_player,result_component_factory=build_browser_frame_player,record_folder_route='/character-animation',allow_individual_delete=True)
        with gr.Accordion('VNCCS PoseStudio QI2.1 알파 기록',open=False):
            gr.Markdown('검증 완료된 256px·4프레임 파일럿을 재추론 없이 공용 이력으로 가져옵니다. 결과는 **프로덕션 스프라이트 채택 불가** 판정이며, 저메모리 3D 조건 실행 기준선으로만 보관합니다.')
            alpha_record_button_value=gr.Button('알파 파일럿을 생성 이력에 기록')
            alpha_record_status_value=gr.Markdown()
        def record_alpha_pilot_history():
            try:
                alpha_record_value=execute_animation_gateway('record-alpha-vnccs',{})
                reused_notice='기존 기록을 다시 사용했습니다.' if alpha_record_value.get('reused') else '알파 파일럿을 생성 이력에 기록했습니다.'
                return [f'{reused_notice} ID: `{alpha_record_value["id"]}`',*read_history_page(1)]
            except Exception as alpha_record_error:
                return ['알파 기록 실패: '+str(alpha_record_error),*read_history_page(1)]
        alpha_record_button_value.click(record_alpha_pilot_history,outputs=[alpha_record_status_value,*history_output_values],queue=False)
        def start_animation(*selection_values):
            yield gr.skip(),'생성 요청을 접수하고 있습니다.',gr.update(interactive=False,value='요청 접수 중…'),True
            try:
                request_payload_value=build_animation_request(*selection_values)
                generation_record_value=execute_animation_gateway('generate',request_payload_value)
                yield generation_record_value['id'],'작업을 접수했습니다. 추가 생성은 확인 후 대기열에 등록됩니다.',gr.update(interactive=True,value='대기열에 추가'),False
            except Exception as generation_request_error:
                yield gr.skip(),'생성 요청 실패: '+str(generation_request_error),gr.update(interactive=True,value='애니메이션 생성 시작'),False
        bind_gpu_generation_confirmation(generation_button_value,start_animation,[motion_select_value,character_select_value,source_select_value,direction_select_value,start_frame_value,end_frame_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value,generation_tag_value,*direction_prompt_components],[generation_identifier_value,status_text_value,generation_button_value,generation_pending_value])
        def change_motion_range(selected_motion_name,selected_source_kind,selected_direction_name,selected_target_frame_rate,selected_speed_ratio,current_start_frame,current_end_frame):
            selected_motion_record=motion_catalog_records[selected_motion_name]
            selected_frame_count=selected_motion_record['frames']
            restored_start_frame,restored_end_frame=1,selected_frame_count
            return gr.update(value=restored_start_frame,maximum=selected_frame_count),gr.update(value=restored_end_frame,maximum=selected_frame_count),create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,restored_start_frame,restored_end_frame,selected_motion_record['fps'],selected_target_frame_rate,selected_speed_ratio,server_base_address)
        def refresh_motion_preview(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,selected_target_frame_rate,selected_speed_ratio):
            return create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,motion_catalog_records[selected_motion_name]['fps'],selected_target_frame_rate,selected_speed_ratio,server_base_address)
        preview_component_values=[motion_select_value,source_select_value,preview_direction_value,start_frame_value,end_frame_value,target_fps_select_value,speed_select_value]
        motion_select_value.input(change_motion_range,[motion_select_value,source_select_value,preview_direction_value,target_fps_select_value,speed_select_value,start_frame_value,end_frame_value],[start_frame_value,end_frame_value,motion_preview_html_value],queue=False)
        motion_select_value.input(lambda motion: [motion_catalog_records[motion].get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES],motion_select_value,direction_prompt_components,queue=False)
        motion_select_value.change(lambda selected_motion_name: select_motion_prompt_values(catalog_record_value,selected_motion_name)['base'],motion_select_value,prompt_text_value,queue=False)
        for prompt_input_component in [motion_select_value,*direction_prompt_components]:
            prompt_input_component.change(lambda selected_motion_name,*direction_prompt_values: describe_motion_prompt_words(catalog_record_value,selected_motion_name,*direction_prompt_values),[motion_select_value,*direction_prompt_components],prompt_word_count_value,queue=False)
        for preview_input_value in (source_select_value,preview_direction_value,start_frame_value,end_frame_value,target_fps_select_value,speed_select_value):
            preview_input_value.change(refresh_motion_preview,preview_component_values,motion_preview_html_value,queue=False)
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
        def refresh_status(identifier,refresh_logs,request_pending):
            if request_pending:return gr.skip(),gr.skip(),gr.skip()
            if not identifier:return '생성 가능 · 설정을 확인하세요.',gr.skip(),gr.update(interactive=True,value='애니메이션 생성 시작')
            status_record_value=execute_animation_gateway('status',{'id':identifier})
            return '상태: '+status_record_value['status'],gr.update(value=status_record_value['log']) if refresh_logs else gr.skip(),gr.update(interactive=True,value='대기열에 추가' if status_record_value['status'] in ('running','queued') else '애니메이션 생성 시작')
        refresh_button_value=gr.Button('상태 새로고침')
        refresh_button_value.click(refresh_status,[generation_identifier_value,log_refresh_enabled,generation_pending_value],[status_text_value,logs_text_value,generation_button_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[generation_identifier_value,log_refresh_enabled,generation_pending_value],[status_text_value,logs_text_value,generation_button_value],show_progress='hidden')
    return interface_blocks_value


if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/character-animation/');arguments_value=parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    build_character_animation_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,allowed_paths=[])
