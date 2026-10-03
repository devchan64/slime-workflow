"""바닥 타일 단일 이미지 생성의 Gradio 클라이언트."""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path: sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.management_client import execute_remote_management_command as execute_management_command
from tools.review.common.gradio_history import HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
MANAGEMENT_SHARED_STYLES = ''.join((Path(__file__).parents[1]/'shared'/style_file_name).read_text() for style_file_name in ('management.css','management-density.css'))
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.domains.tile.floor_generation import combine_floor_prompt, compose_floor_base_prompt


def execute_floor_gateway(command_name_value,payload_record_value):
    return execute_management_command('floor-tile',command_name_value,payload_record_value)


def build_floor_interface(server_base_address):
    catalog_record_value = execute_floor_gateway('catalog',{})
    with gr.Blocks(title='맵 타일 생성기',js=HISTORY_CARD_SELECTION_SCRIPT,elem_classes=['management-generator-root']) as interface_block_value:
        gr.Markdown('## 맵 타일 생성기\nQwen 2511로 512×512 맵 타일을 4스텝으로 한 번 생성합니다. 사용자 프롬프트를 고정 기본 프롬프트 앞에 배치합니다.')
        with gr.Row(equal_height=True):
            user_prompt_control = gr.Textbox(value=catalog_record_value['default_user_prompt'],label='사용자 프롬프트 · 바닥 표면',lines=3,scale=1,min_width=240)
            generation_tag_control = gr.Textbox(label='생성 이력 태그 · 선택 사항',lines=3,scale=1,min_width=240)
        prompt_reset_button = gr.ClearButton([user_prompt_control],value='프롬프트 초기화',variant='secondary',size='sm')
        add_margins_control = gr.Checkbox(value=catalog_record_value['default_add_margins'],label='여백 추가',info='ON: Blank margins. 추가 · OFF: 여백 문구 제외')
        initial_base_prompt = compose_floor_base_prompt(catalog_record_value)
        with gr.Row(equal_height=True):
            base_prompt_control = gr.Textbox(value=initial_base_prompt,label=f"기본 프롬프트 · 고정 · {len(initial_base_prompt.split())}단어",interactive=False,lines=3,scale=1,min_width=240)
        def format_floor_preview(user_prompt_value, current_catalog_record, add_margins_value=None):
            if not user_prompt_value.strip(): return '바닥 표면을 입력하세요. 생성하려면 사용자 프롬프트가 필요합니다.'
            combined_prompt_value = combine_floor_prompt(user_prompt_value,current_catalog_record,add_margins_value)
            return f'**사용자 {len(user_prompt_value.split())}단어 · 최종 {len(combined_prompt_value.split())}단어**\n\n{combined_prompt_value}'
        prompt_preview_control = gr.Markdown(format_floor_preview(catalog_record_value['default_user_prompt'],catalog_record_value))
        def refresh_floor_prompts(user_prompt_value,add_margins_value):
            current_catalog_record = execute_floor_gateway('catalog',{})
            current_base_prompt = compose_floor_base_prompt(current_catalog_record,add_margins_value)
            return gr.update(value=current_base_prompt,label=f'기본 프롬프트 · 고정 · {len(current_base_prompt.split())}단어'), format_floor_preview(user_prompt_value,current_catalog_record,add_margins_value)
        prompt_output_controls = [base_prompt_control,prompt_preview_control]
        user_prompt_control.change(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        add_margins_control.change(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        interface_block_value.load(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls)
        gr.Timer(3).tick(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        output_size_control = gr.Dropdown([512],value=512,label='생성 크기 · 512 고정',interactive=False)
        inference_step_control = gr.Radio([4],value=4,label='생성 스텝 · 4 고정',interactive=False)
        generation_seed_control = build_generation_seed(251204)
        generation_start_button = gr.Button('맵 타일 생성 시작',variant='primary')
        generation_status_control = gr.Markdown('생성 가능 · 100단어 미만의 프롬프트를 입력하세요.')
        with gr.Accordion('생성 과정 · 고정 설정 안내',open=False):
            gr.Markdown('사용자 프롬프트 → 고정 기본 프롬프트 순서로 Qwen 2511에 전달합니다. 512×512 · 4스텝 단일 생성이며 결과 원본은 result.png입니다. 이전 생성 이력은 조회만 가능하며 재개할 수 없습니다. 현재 설정으로 새로 생성하세요.')
        current_identifier_state = gr.State('')
        def start_floor_generation(user_prompt_value,generation_tag_value,output_size_value,inference_step_value,generation_seed_value,add_margins_value):
            generation_result_record = execute_floor_gateway('generate',{'action':'generate','user_prompt':user_prompt_value,'tag':generation_tag_value,'width':int(output_size_value),'height':int(output_size_value),'steps':int(inference_step_value),'seed':int(generation_seed_value),'add_margins':add_margins_value})
            return generation_result_record['id'], '생성 요청: '+generation_result_record['id']+' · '+generation_result_record['status']
        bind_gpu_generation_confirmation(generation_start_button,start_floor_generation,[user_prompt_control,generation_tag_control,output_size_control,inference_step_control,generation_seed_control,add_margins_control],[current_identifier_state,generation_status_control])
        def refresh_floor_progress(current_generation_identifier):
            active_job_record = execute_floor_gateway('active',{})
            selected_job_identifier = active_job_record.get('id') or current_generation_identifier
            if not selected_job_identifier: return '', '생성 가능 · 작업이 없습니다.'
            current_status_record = execute_floor_gateway('status',{'id':selected_job_identifier})
            current_status_name = current_status_record['status']
            if current_status_name == 'queued': return selected_job_identifier, 'GPU 대기열 대기 · 예상 남은 시간·완료 시각 계산 중 (실행 시작 후 추정)'
            if current_status_name != 'running': return selected_job_identifier, '상태: '+current_status_name+' · '+current_status_record.get('error','결과는 생성 이력에서 확인하세요.')
            estimate_record_value = current_status_record.get('estimate',{})
            remaining_seconds_value = estimate_record_value.get('remaining_seconds')
            if remaining_seconds_value is None: return selected_job_identifier, current_status_record.get('stage','생성 중')+' · 예상 남은 시간·완료 시각 계산 중 (동일 설정 완료 이력 부족)'
            expected_finish_value = datetime.now(ZoneInfo('Asia/Seoul'))+timedelta(seconds=remaining_seconds_value)
            return selected_job_identifier, f"{current_status_record.get('stage','생성 중')} · 예상 {remaining_seconds_value:.0f}초 남음 · 완료 {expected_finish_value:%H:%M:%S} KST · 근거: 동일 설정 완료 {estimate_record_value['samples']}건 평균"
        interface_block_value.load(refresh_floor_progress,current_identifier_state,[current_identifier_state,generation_status_control])
        gr.Timer(3).tick(refresh_floor_progress,current_identifier_state,[current_identifier_state,generation_status_control],queue=False)
        def restore_floor_inputs(history_record_value):
            saved_request_record = history_record_value['request']
            return [saved_request_record['user_prompt'],saved_request_record.get('tag',''),512,4,saved_request_record['seed'],saved_request_record.get('add_margins',False)]
        read_history_page,history_output_values = build_generation_history_view(execute_floor_gateway,server_base_address,'초기화하면 바닥 타일 생성 기록과 결과 파일을 삭제합니다. 실행 중에는 사용할 수 없습니다.',restore_floor_inputs,[user_prompt_control,generation_tag_control,output_size_control,inference_step_control,generation_seed_control,add_margins_control],record_folder_route='/floor-tile-generator',allow_individual_delete=True)
        interface_block_value.load(lambda:read_history_page(1),outputs=history_output_values)
    return interface_block_value

if __name__=='__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--root-path',default='/management/frame/floor-tile-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_floor_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,css=MANAGEMENT_SHARED_STYLES)
