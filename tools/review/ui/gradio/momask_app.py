"""공용 게이트웨이를 사용하는 MoMask Gradio 클라이언트."""
import argparse
import inspect
import json
import os
from pathlib import Path
import sys
import threading
import time

import gradio as gr
import yaml

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_frame_player import build_browser_frame_player
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.management_client import execute_remote_management_command as execute_management_command
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.domains.momask.momask_generation import render_position_retarget_policy

MOTION_ACTION_LABELS = [('대기','standing'),('걷기','walking'),('휴식','resting'),('커스텀','custom')]
MOTION_DIRECTION_LABELS = [('전방 좌측','down_left'),('전방 우측','down_right'),('후방 좌측','up_left'),('후방 우측','up_right')]

def create_copyable_textbox(**textbox_keyword_values):
    copy_option_name='show_copy_button' if 'show_copy_button' in inspect.signature(gr.Textbox).parameters else 'buttons'
    textbox_keyword_values[copy_option_name]=True if copy_option_name=='show_copy_button' else ['copy']
    return gr.Textbox(**textbox_keyword_values)

def execute_motion_command(operation_command_name, command_payload_value):
    return execute_management_command('momask', operation_command_name, command_payload_value)

def read_motion_settings(selected_action_name):
    selected_action_name='standing' if selected_action_name=='custom' else selected_action_name
    action_config_record=json.loads((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/standing-loops-v1.json').read_text())['actions'][selected_action_name]
    camera_config_record=yaml.safe_load((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/camera-angles.yaml').read_text())
    prompt_content_value=action_config_record['prompt']
    current_summary_rows=[('프롬프트',f'{len(prompt_content_value.split())}단어'),('원본 모션',f"{action_config_record['source_frames']}프레임"),('내려다보기','약 17°')]
    current_camera_rows=[(current_direction_label,f"{camera_config_record[selected_action_name][current_direction_name]}°") for current_direction_label,current_direction_name in MOTION_DIRECTION_LABELS]
    current_summary_text='| 설정 | 값 |\n| --- | --- |\n'+'\n'.join(f'| {current_field_label} | {current_field_value} |' for current_field_label,current_field_value in current_summary_rows)
    current_camera_text='| 방향 | 수평 방위각 · 정면 0° 기준 |\n| --- | --- |\n'+'\n'.join(f'| {current_direction_label} | {current_angle_value} |' for current_direction_label,current_angle_value in current_camera_rows)
    return prompt_content_value,current_summary_text+'\n\n'+current_camera_text


def create_motion_history_records(server_base_address):
    return execute_motion_command('history',{})


def execute_motion_history_command(operation_command_name,command_payload_value,server_base_address):
    if operation_command_name=='history':
        return create_motion_history_records(server_base_address)
    return execute_motion_command(operation_command_name,command_payload_value)

def start_motion_generation(selected_action_name, selected_direction_names, selected_face_enabled, generation_tag_value, custom_prompt_text=None):
    generation_record_value=execute_motion_command('generate',{'action':selected_action_name,'directions':selected_direction_names,'face':selected_face_enabled,'tag':generation_tag_value.strip(),**({'prompt':custom_prompt_text} if selected_action_name=='custom' else {})})
    return generation_record_value['id']

def read_saved_motion_inputs(selected_history_identifier):
    if not selected_history_identifier:
        raise gr.Error('입력값을 조회하거나 불러올 생성이력을 먼저 선택하세요.')
    saved_status_record = execute_motion_command('status', {'id': selected_history_identifier})
    return {'id': selected_history_identifier, 'request': saved_status_record['request'],
            'prompt': saved_status_record['prompt'], 'prompt_word_count': saved_status_record['prompt_word_count'],
            'prompt_status': '생성 당시 원문' if saved_status_record['prompt'] is not None else '프롬프트 저장 전 중단 또는 생성 준비 중'}


def restore_saved_motion_inputs(selected_history_identifier):
    saved_input_record = read_saved_motion_inputs(selected_history_identifier)
    saved_request_record = saved_input_record['request']
    if set(saved_request_record) - {'action', 'directions', 'face', 'tag', 'prompt'} or not {'action', 'directions', 'face'} <= set(saved_request_record):
        raise gr.Error('저장된 입력 필드가 현재 계약과 다릅니다. 입력값 조회로 원문을 확인하세요.')
    selected_action_name = saved_request_record['action']
    selected_direction_names = saved_request_record['directions']
    selected_face_enabled = saved_request_record['face']
    if selected_action_name not in [value for _, value in MOTION_ACTION_LABELS] or not isinstance(selected_direction_names, list) or not selected_direction_names or any(not isinstance(current_direction_name, str) for current_direction_name in selected_direction_names) or len(set(selected_direction_names)) != len(selected_direction_names) or set(selected_direction_names) - {value for _, value in MOTION_DIRECTION_LABELS} or type(selected_face_enabled) is not bool:
        raise gr.Error('현재 지원하지 않는 포즈·방향·얼굴 옵션입니다. 입력값 조회로 원문을 확인하세요.')
    current_prompt_text, current_settings_text = read_motion_settings(selected_action_name)
    if selected_action_name=='custom':
        current_prompt_text=saved_request_record['prompt']
    restore_status_text = f'{selected_history_identifier}의 포즈·방향·얼굴 옵션을 새 모션 생성 입력란에 불러왔습니다. 생성은 시작하지 않았습니다.'
    if saved_input_record['prompt'] is None or saved_input_record['prompt'].strip() != current_prompt_text.strip():
        restore_status_text += ' 고정 스크립트는 현재 설정을 사용합니다. 과거 원문과 다르거나 기록이 없어 동일 결과 재생성을 보장하지 않습니다.'
    return selected_action_name, selected_direction_names, selected_face_enabled, saved_request_record.get('tag',''), gr.update(value=current_prompt_text,interactive=selected_action_name=='custom'), current_settings_text, restore_status_text

def restore_motion_history_record(current_history_record):
    return restore_saved_motion_inputs(current_history_record['id'])

def create_motion_player(generation_job_identifier, generation_result_record, server_base_address):
    current_frame_count=generation_result_record.get('frames',0)
    current_direction_names=generation_result_record.get('directions',[])
    if type(current_frame_count) is not int or current_frame_count<1 or not current_direction_names:
        raise ValueError('모션 결과에 프레임 수와 방향이 필요합니다.')
    current_result_root=server_base_address+'/momask-generator/jobs/'+generation_job_identifier+'/result/'
    current_panel_labels=['HumanML3D 22관절']
    if generation_result_record.get('anny_frames'):current_panel_labels.append('ANNY 리그')
    if generation_result_record.get('openpose_map_frames'):current_panel_labels.append('OpenPose COCO18')
    current_direction_frames={}
    for current_direction_name in current_direction_names:
        current_frame_records=[]
        for current_frame_number in range(1,current_frame_count+1):
            current_frame_suffix=f'{current_frame_number:04d}.png'
            current_frame_paths=[current_result_root+('openpose/' if generation_result_record.get('anny_frames') else '')+current_direction_name+'/openpose-'+current_frame_suffix]
            if generation_result_record.get('anny_frames'):current_frame_paths.append(current_result_root+'anny/'+current_direction_name+'/frames/anny-'+current_frame_suffix)
            if generation_result_record.get('openpose_map_frames'):current_frame_paths.append(current_result_root+'openpose-map/'+current_direction_name+'/openpose-map-'+current_frame_suffix)
            current_frame_records.append(current_frame_paths)
        current_direction_frames[current_direction_name]=current_frame_records
    return json.dumps({'frames':current_direction_frames,'directUrls':True,'panels':current_panel_labels},ensure_ascii=False)

def render_motion_history_result(generation_job_identifier,generation_status_record,server_base_address):
    if generation_status_record.get('status')!='completed':
        return json.dumps({'frames':{},'message':'선택한 이력은 '+str(generation_status_record.get('status','unknown'))+' 상태입니다. 실행 로그를 확인하세요.'},ensure_ascii=False)
    return create_motion_player(generation_job_identifier,generation_status_record.get('result',{}),server_base_address)

def build_momask_interface(server_base_address):
    with gr.Blocks(title='MoMask 모션 생성기') as interface_blocks_value:
        gr.Markdown('## MoMask 모션 생성기\n포즈와 방향을 설정해 모션을 생성하고, 아래 이력 카드에서 결과 재생·입력 재사용·중지·재개를 처리합니다.')
        with gr.Column(elem_id='motion-workspace'):
            gr.Markdown('### 새 모션 생성')
            with gr.Row():
                action_select_value=gr.Dropdown(MOTION_ACTION_LABELS,value='standing',label='포즈')
                direction_select_value=gr.CheckboxGroup(MOTION_DIRECTION_LABELS,value=[value for _,value in MOTION_DIRECTION_LABELS],label='생성 방향',elem_id='motion-direction-selection')
            with gr.Row():
                face_checkbox_value=gr.Checkbox(value=True,label='얼굴 포인트 ON · 가려진 점 제외')
                generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 돌온재 걷기 후보',max_lines=1)
            settings_initial_values=read_motion_settings('standing')
            prompt_text_value=gr.Textbox(value=settings_initial_values[0],label='고정 스크립트',interactive=False,lines=4)
            gr.Markdown('커스텀을 선택하면 현재 문장을 편집할 수 있습니다. 자연어 모션 지시이며 코드가 아닙니다. 커스텀은 대기 기준 120프레임·카메라 설정을 사용합니다.')
            settings_text_value=gr.Markdown(settings_initial_values[1])
            with gr.Accordion('위치 채널 기반 공통 리타깃', open=False,elem_id='motion-retarget-policy'):
                gr.Markdown(render_position_retarget_policy().removeprefix('<p>').removesuffix('</p>'))
            with gr.Row(elem_id='motion-command-actions'):
                generate_button_value=gr.Button('모션 생성 시작',variant='primary',elem_id='motion-generate-button')
                cancel_button_value=gr.Button('현재 생성 취소',elem_id='motion-cancel-button',interactive=False)
                status_refresh_button_value=gr.Button('상태 새로고침',elem_id='motion-status-refresh-button')
            current_identifier_value=create_copyable_textbox(label='현재 생성 ID',interactive=False)
            status_text_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
            gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요. 예상 시간은 측정 자료가 없어 계산 중입니다.')
        def update_motion_script(selected_action_name,current_prompt_text):
            configured_prompt_text,current_settings_text=read_motion_settings(selected_action_name)
            return gr.update(value=current_prompt_text if selected_action_name=='custom' else configured_prompt_text,interactive=selected_action_name=='custom',label='커스텀 스크립트' if selected_action_name=='custom' else '고정 스크립트'),current_settings_text
        action_select_value.change(update_motion_script,[action_select_value,prompt_text_value],[prompt_text_value,settings_text_value],queue=False)
        prompt_word_count_view=gr.Markdown(f'모델 입력 · 최종 {len(settings_initial_values[0].split())}단어')
        prompt_text_value.change(lambda current_prompt_text:f'모델 입력 · 최종 {len(current_prompt_text.split())}단어',[prompt_text_value],prompt_word_count_view,queue=False)
        def start_motion_with_status(*input_values):
            generation_identifier_value=start_motion_generation(*input_values)
            return generation_identifier_value,'작업을 접수했습니다. 아래 생성 이력에서 상태와 로그를 확인하세요.'
        bind_gpu_generation_confirmation(generate_button_value,start_motion_with_status,[action_select_value,direction_select_value,face_checkbox_value,generation_tag_value,prompt_text_value],[current_identifier_value,status_text_value])
        def refresh_motion_status(generation_job_identifier):
            generation_running_value=execute_motion_command('history',{})['running']
            if not generation_job_identifier:
                return ('다른 작업 생성 중 · 아래 생성 이력에서 작업을 선택하세요.' if generation_running_value else '생성 가능 · 설정을 확인하세요.'),gr.update(interactive=not generation_running_value),gr.update(interactive=False)
            try:
                generation_status_record=execute_motion_command('status',{'id':generation_job_identifier})
            except (ValueError,FileNotFoundError):
                return '현재 생성 ID의 상태를 불러오지 못했습니다. 생성 이력에서 해당 작업을 선택하세요.',gr.update(interactive=not generation_running_value),gr.update(interactive=False)
            return '상태: '+generation_status_record['status']+' · '+generation_status_record.get('message',''),gr.update(interactive=not generation_running_value),gr.update(interactive=generation_status_record['status'] in ('running','queued'))
        def cancel_current_motion(generation_job_identifier):
            if not generation_job_identifier:
                raise gr.Error('취소할 현재 생성 작업이 없습니다. 생성 이력에서 작업을 선택하세요.')
            execute_motion_command('cancel',{'id':generation_job_identifier})
            return '생성 중지 요청을 접수했습니다. 완료 상태는 새로고침 또는 생성 이력에서 확인하세요.'
        status_refresh_button_value.click(refresh_motion_status,current_identifier_value,[status_text_value,generate_button_value,cancel_button_value],queue=False)
        cancel_button_value.click(cancel_current_motion,current_identifier_value,status_text_value,queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_motion_status,current_identifier_value,[status_text_value,generate_button_value,cancel_button_value],show_progress='hidden')
        read_history_page,history_output_values=build_generation_history_view(
            lambda command_name_value,payload_value:execute_motion_history_command(command_name_value,payload_value,server_base_address),
            server_base_address,
            '이력 목록만 초기화합니다. 결과 모션과 로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',
            restore_input_callback=restore_motion_history_record,
            restore_output_components=[action_select_value,direction_select_value,face_checkbox_value,generation_tag_value,prompt_text_value,settings_text_value,status_text_value],
            result_renderer_callback=render_motion_history_result,
            result_component_factory=build_browser_frame_player,
            record_folder_route='/momask-generator',
            allow_individual_delete=True,
        )
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
    return interface_blocks_value


if __name__=='__main__':
    argument_parser_value=argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--root-path',default='/momask-generator/')
    parsed_argument_values=argument_parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==parsed_argument_values.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    build_momask_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,allowed_paths=[])
