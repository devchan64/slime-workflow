"""공용 게이트웨이를 사용하는 MoMask Gradio 클라이언트."""
import argparse
import html
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
from tools.review.common.gradio_history import build_history_reset_controls, bind_history_reset_action, format_history_choice_label
from tools.review.common.management_gateway import execute_management_command
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.domains.momask.momask_jobs import check_generation_running
from tools.review.domains.momask.momask_generation import render_position_retarget_policy

MOTION_ACTION_LABELS = [('대기','standing'),('스트레칭','stretch'),('걷기','walking')]
MOTION_DIRECTION_LABELS = [('전방 좌측','down_left'),('전방 우측','down_right'),('후방 좌측','up_left'),('후방 우측','up_right')]

def create_copyable_textbox(**textbox_keyword_values):
    copy_option_name='show_copy_button' if 'show_copy_button' in inspect.signature(gr.Textbox).parameters else 'buttons'
    textbox_keyword_values[copy_option_name]=True if copy_option_name=='show_copy_button' else ['copy']
    return gr.Textbox(**textbox_keyword_values)

def execute_motion_command(operation_command_name, command_payload_value):
    return execute_management_command('momask', operation_command_name, command_payload_value)

def read_motion_settings(selected_action_name):
    action_config_record=json.loads((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/standing-loops-v1.json').read_text())['actions'][selected_action_name]
    camera_config_record=yaml.safe_load((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/camera-angles.yaml').read_text())
    prompt_content_value=action_config_record['prompt']
    return prompt_content_value, f"{len(prompt_content_value.split())}단어 · 원본 {action_config_record['source_frames']}프레임 · 수평 {camera_config_record[selected_action_name]}° · 내려다보기 약 17°"

def list_motion_history(history_page_number=1, selected_history_identifier=None):
    history_record_values=execute_motion_command('history',{})
    selected_page_number=max(1,min(int(history_page_number or 1),max(1,(len(history_record_values)+7)//8)))
    history_page_records=history_record_values[(selected_page_number-1)*8:selected_page_number*8]
    history_choice_values=[]
    for record_value in history_page_records:
        history_record_value={'id':record_value['id'],'created_at':record_value.get('created_at'),'status':{'status':record_value['status']},'request':{'action':dict((value,label) for label,value in MOTION_ACTION_LABELS).get(record_value['action'],record_value['action']),'directions':len(record_value.get('directions',[]))}}
        history_choice_values.append((format_history_choice_label(history_record_value),record_value['id']))
    retained_history_identifier=selected_history_identifier if selected_history_identifier in [value for _,value in history_choice_values] else None
    return gr.update(choices=history_choice_values,value=retained_history_identifier), f"{selected_page_number} / {max(1,(len(history_record_values)+7)//8)} 페이지 · 총 {len(history_record_values)}건"

def start_motion_generation(selected_action_name, selected_direction_names, selected_face_enabled):
    generation_record_value=execute_motion_command('generate',{'action':selected_action_name,'directions':selected_direction_names,'face':selected_face_enabled})
    return generation_record_value['id']

def create_motion_player(generation_job_identifier, generation_result_record, server_base_address):
    player_payload_value={'id':generation_job_identifier,'result':generation_result_record,'base':server_base_address}
    player_source_text=(Path(__file__).parent/'motion-player.html').read_text().replace('__PLAYER_PAYLOAD__',json.dumps(player_payload_value).replace('<','\\u003c'))
    return '<iframe title="모션 동기 재생" style="width:100%;height:460px;border:0" sandbox="allow-scripts" srcdoc="'+html.escape(player_source_text,quote=True)+'"></iframe>'

def build_momask_interface(server_base_address):
    with gr.Blocks(title='MoMask 모션 생성기') as interface_blocks_value:
        gr.Markdown('## MoMask 모션 생성기')
        with gr.Row(elem_id='motion-workspace'):
            with gr.Column(scale=1,min_width=340,elem_id='motion-controls'):
                with gr.Tab('새 모션 생성'):
                    action_select_value=gr.Dropdown(MOTION_ACTION_LABELS,value='standing',label='포즈')
                    direction_select_value=gr.CheckboxGroup(MOTION_DIRECTION_LABELS,value=[value for _,value in MOTION_DIRECTION_LABELS],label='생성 방향')
                    face_checkbox_value=gr.Checkbox(value=True,label='얼굴 포인트 ON · 가려진 점 제외')
                    settings_initial_values=read_motion_settings('standing')
                    prompt_text_value=gr.Textbox(value=settings_initial_values[0],label='고정 스크립트',interactive=False,lines=4)
                    settings_text_value=gr.Markdown(settings_initial_values[1])
                    gr.HTML(render_position_retarget_policy())
                    with gr.Row():
                        generate_button_value=gr.Button('모션 생성 시작',variant='primary')
                        cancel_button_value=gr.Button('생성 취소')
                        status_refresh_button_value=gr.Button('상태 새로고침')
                    status_text_value=gr.Markdown('작업 상태 조회 중')
                    gr.Markdown('예상 시간: 측정 자료가 없어 계산할 수 없습니다. 실행 로그에서 단계를 확인하세요.')
                with gr.Tab('생성이력 · 결과 조회'):
                    gr.Markdown('이력을 선택한 뒤 **결과 조회**를 누르세요.')
                    history_table_value=gr.Radio(choices=[],label='조회할 생성 결과',interactive=True,elem_id='motion-history-selection')
                    history_selected_value=gr.Markdown('조회할 생성이력을 선택하세요.')
                    history_resume_button=gr.Button('생성 재개',interactive=False)
                    history_resume_help=gr.Markdown('취소되거나 실패한 작업을 선택하면 이어서 생성할 수 있습니다. 리그 생성이 완료된 작업만 지원합니다.')
                    history_result_button=gr.Button('선택한 결과 조회',variant='primary',interactive=False)
                    with gr.Row():
                        history_page_value=gr.Number(value=1,precision=0,minimum=1,label='페이지',scale=1,min_width=100)
                        history_refresh_value=gr.Button('이력 새로고침')
                        history_count_value=gr.Markdown()
                    reset_control_values=build_history_reset_controls('이력 목록만 초기화합니다. 결과 파일은 보존됩니다.')
            with gr.Column(scale=2,min_width=480,elem_id='motion-preview'):
                gr.Markdown('### 결과 재생')
                viewed_identifier_value=create_copyable_textbox(label='조회한 결과 이력 ID · 오른쪽 아이콘으로 복사',interactive=False,elem_id='viewed-motion-identifier')
                player_html_value=gr.HTML('<div class="motion-empty-state">아직 선택된 결과가 없습니다.<br>왼쪽 <b>생성이력 · 결과 조회</b>에서 이력을 선택하고 조회하세요.</div>')
                with gr.Accordion('생성 ID로 직접 조회',open=False):
                    identifier_text_value=create_copyable_textbox(label='생성 ID',interactive=True)
                    result_button_value=gr.Button('ID로 결과 조회')
                with gr.Accordion('결과 상세 · OpenPose 맵 생성',open=False):
                    map_button_value=gr.Button('OpenPose 맵 생성 · 설정의 얼굴 포인트 옵션 적용')
                    record_path_value=create_copyable_textbox(label='기록 폴더',interactive=False)
                    input_record_value=gr.JSON(label='저장된 입력 · 결과 정보')
        logs_text_value,log_refresh_enabled,log_panel_element=build_execution_logs()
        action_select_value.change(read_motion_settings,action_select_value,[prompt_text_value,settings_text_value],queue=False)
        generate_button_value.click(start_motion_generation,[action_select_value,direction_select_value,face_checkbox_value],identifier_text_value)
        cancel_button_value.click(lambda identifier: execute_motion_command('cancel',{'id':identifier}),identifier_text_value,input_record_value)
        history_refresh_value.click(list_motion_history,[history_page_value,history_table_value],[history_table_value,history_count_value],queue=False)
        history_page_value.change(list_motion_history,[history_page_value,history_table_value],[history_table_value,history_count_value],queue=False)
        bind_history_reset_action(reset_control_values,execute_motion_command,lambda:[*list_motion_history(1),1],[history_table_value,history_count_value,history_page_value])
        def show_motion_result(generation_job_identifier):
            if not generation_job_identifier:raise gr.Error('생성이력 행을 선택하거나 생성 ID를 입력하세요.')
            generation_status_record=execute_motion_command('status',{'id':generation_job_identifier})
            if generation_status_record['status']!='completed':
                return '<p>선택한 이력은 '+html.escape(generation_status_record['status'])+' 상태입니다. 실행 로그를 확인하세요.</p>',str(WORKFLOW_ROOT_DIRECTORY/'.tmp/momask-generator/jobs'/generation_job_identifier),generation_status_record,generation_job_identifier
            generation_job_path=WORKFLOW_ROOT_DIRECTORY/'.tmp/momask-generator/jobs'/generation_job_identifier
            return create_motion_player(generation_job_identifier,generation_status_record['result'],server_base_address),str(generation_job_path),{'request':json.loads((generation_job_path/'request.json').read_text()),'result':generation_status_record['result']},generation_job_identifier
        result_button_value.click(show_motion_result,identifier_text_value,[player_html_value,record_path_value,input_record_value,viewed_identifier_value])
        identifier_text_value.submit(show_motion_result,identifier_text_value,[player_html_value,record_path_value,input_record_value,viewed_identifier_value])
        def select_history_result(selected_history_identifier):
            resume_enabled_value=False
            resume_help_text='취소되거나 실패한 작업을 선택하면 이어서 생성할 수 있습니다. 리그 생성이 완료된 작업만 지원합니다.'
            if selected_history_identifier:
                selected_status_record=execute_motion_command('status',{'id':selected_history_identifier})
                if selected_status_record['status'] in ('cancelled','failed'):
                    from tools.review.domains.momask.momask_jobs import resolve_generation_directory
                    selected_job_directory=resolve_generation_directory(selected_history_identifier)
                    required_resume_paths=('result/anny/mannequin.blend','result/anny/render_asset.py','result/anny/run_stage.py','result/anny/baseline-model.json','motion-run/motion/motion.npz','motion-run/prompt.txt')
                    if not all((selected_job_directory/path_value).is_file() for path_value in required_resume_paths):
                        resume_help_text='리그 생성 전에 중단되어 재개할 수 없습니다. 새 모션 생성 탭에서 다시 생성하세요.'
                    elif check_generation_running():
                        resume_help_text='다른 작업이 생성 중입니다. 종료 후 재개할 수 있습니다.'
                    else:
                        resume_enabled_value=True
                        resume_help_text='취소되거나 실패한 작업을 이어서 생성합니다. 완료된 프레임과 기존 로그는 유지됩니다.'
                else:
                    resume_help_text='취소되거나 실패한 작업만 재개할 수 있습니다.'
            return ('선택한 이력: `'+selected_history_identifier+'`') if selected_history_identifier else '조회할 생성이력을 선택하세요.', gr.update(interactive=bool(selected_history_identifier)), gr.update(interactive=resume_enabled_value), resume_help_text
        history_table_value.change(select_history_result,history_table_value,[history_selected_value,history_result_button,history_resume_button,history_resume_help],queue=False)
        history_table_value.input(lambda selected_identifier: selected_identifier or '',history_table_value,identifier_text_value,queue=False)
        history_resume_button.click(lambda selected_identifier: execute_motion_command('resume',{'id':selected_identifier})['id'],history_table_value,identifier_text_value)
        history_result_button.click(show_motion_result,history_table_value,[player_html_value,record_path_value,input_record_value,viewed_identifier_value],scroll_to_output=True)

        map_button_value.click(lambda identifier,face:execute_motion_command('openpose-map',{'id':identifier,'face':face}),[identifier_text_value,face_checkbox_value],input_record_value).then(show_motion_result,identifier_text_value,[player_html_value,record_path_value,input_record_value,viewed_identifier_value])
        def refresh_motion_status(generation_job_identifier,log_refresh_checked):
            generation_running_value=check_generation_running()
            if not generation_job_identifier:
                return '다른 작업 생성 중' if generation_running_value else '생성 가능 · 설정 후 생성 시작을 누르세요.','생성이력을 선택하거나 새 모션을 생성하면 로그가 표시됩니다.',gr.update(interactive=not generation_running_value),gr.update(interactive=False)
            try:
                generation_status_record=execute_motion_command('status',{'id':generation_job_identifier})
            except (ValueError,FileNotFoundError):
                return '유효한 생성 ID를 입력하거나 이력 행을 선택하세요.','선택한 작업의 로그를 불러올 수 없습니다. ID와 기록 폴더를 확인하세요.',gr.update(interactive=not generation_running_value),gr.update(interactive=False)
            return '상태: '+generation_status_record['status'],gr.update(value=generation_status_record['log'] or '작업이 접수되었습니다. 첫 실행 로그를 기다리고 있습니다.',label='실행 로그 · '+generation_job_identifier) if log_refresh_checked else gr.skip(),gr.update(interactive=not generation_running_value),gr.update(interactive=generation_status_record['status']=='running')
        status_refresh_button_value.click(refresh_motion_status,[identifier_text_value,log_refresh_enabled],[status_text_value,logs_text_value,generate_button_value,cancel_button_value],queue=False)
        status_output_components=[status_text_value,logs_text_value,generate_button_value,cancel_button_value]
        def read_selected_log(generation_job_identifier):
            return refresh_motion_status(generation_job_identifier,True)
        identifier_text_value.change(read_selected_log,identifier_text_value,status_output_components,queue=False)
        log_refresh_enabled.change(refresh_motion_status,[identifier_text_value,log_refresh_enabled],status_output_components,queue=False)
        if hasattr(log_panel_element,'expand'):
            log_panel_element.expand(read_selected_log,identifier_text_value,status_output_components,queue=False)
        if hasattr(gr,'Timer'):
            gr.Timer(2).tick(refresh_motion_status,[identifier_text_value,log_refresh_enabled],status_output_components,show_progress='hidden')
        else:
            interface_blocks_value.load(refresh_motion_status,[identifier_text_value,log_refresh_enabled],status_output_components,every=2,show_progress='hidden')
        def restore_running_motion():
            return next((record_value['id'] for record_value in execute_motion_command('history',{}) if record_value['status']=='running'),'')
        interface_blocks_value.load(restore_running_motion,outputs=identifier_text_value)
        interface_blocks_value.load(list_motion_history,[history_page_value,history_table_value],[history_table_value,history_count_value])
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
    build_momask_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,theme=gr.themes.Soft(),css=(Path(__file__).parent/'management-layout.css').read_text()+LOG_PANEL_STYLES,allowed_paths=[])
