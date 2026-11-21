"""바닥 타일 단일 이미지 생성의 Gradio 클라이언트."""
import argparse
from pathlib import Path
import sys
import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path: sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.management.common.generation_status_display import describe_generation_status
from tools.management.common.generation_status_lookup import read_existing_generation_status
from tools.management.common.management_client import execute_remote_management_command as execute_management_command
from tools.management.common.gradio_history import build_generation_history_view
from tools.management.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.management.common.gradio_seed import build_generation_seed, select_generation_seed_value, QWEN_SEED_GUIDANCE
from tools.management.common.gradio_button_guidance import build_button_guidance
from tools.management.domains.tile.floor_generation import combine_floor_prompt, compose_floor_base_prompt


def execute_floor_gateway(command_name_value,payload_record_value):
    return execute_management_command('floor-tile',command_name_value,payload_record_value)


def check_floor_prompt_readiness(current_prompt_text, current_catalog_record, current_margins_enabled):
    if not isinstance(current_prompt_text, str) or not current_prompt_text.strip():
        return False
    return len(combine_floor_prompt(current_prompt_text, current_catalog_record, current_margins_enabled).split()) < 100


def build_floor_interface(server_base_address):
    catalog_record_value = execute_floor_gateway('catalog',{})
    with gr.Blocks(title='맵 타일 생성기',elem_classes=['management-generator-root']) as interface_block_value:
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
        current_prompt_ready = gr.State(False)
        def refresh_floor_prompts(user_prompt_value,add_margins_value):
            current_catalog_record = execute_floor_gateway('catalog',{})
            current_base_prompt = compose_floor_base_prompt(current_catalog_record,add_margins_value)
            return gr.update(value=current_base_prompt,label=f'기본 프롬프트 · 고정 · {len(current_base_prompt.split())}단어'), format_floor_preview(user_prompt_value,current_catalog_record,add_margins_value), check_floor_prompt_readiness(user_prompt_value,current_catalog_record,add_margins_value)
        prompt_output_controls = [base_prompt_control,prompt_preview_control,current_prompt_ready]
        user_prompt_control.change(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        add_margins_control.change(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        interface_block_value.load(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls)
        gr.Timer(3).tick(refresh_floor_prompts,[user_prompt_control,add_margins_control],prompt_output_controls,queue=False)
        output_size_control = gr.Dropdown([512],value=512,label='생성 크기 · 512 고정',interactive=False)
        inference_step_control = gr.Radio([4],value=4,label='생성 스텝 · 4 고정',interactive=False)
        generation_seed_control = build_generation_seed(251204, random_initial_enabled=True)
        automatic_seed_control = gr.Checkbox(value=True, label='생성마다 무작위 시드', info='끄면 표시된 시드를 사용합니다. 이력을 불러오면 자동으로 꺼집니다.')
        gr.Markdown(QWEN_SEED_GUIDANCE)
        generation_start_button = gr.Button('대기열에 추가',variant='primary',interactive=False)
        build_button_guidance(generation_start_button, '바닥 표면을 입력하고 기본 문구를 포함한 최종 프롬프트를 100단어 미만으로 맞추세요.')
        generation_status_control = gr.Markdown('바닥 표면과 최종 프롬프트를 확인하세요.')
        with gr.Accordion('생성 과정 · 고정 설정 안내',open=False):
            gr.Markdown('사용자 프롬프트 → 고정 기본 프롬프트 순서로 Qwen 2511에 전달합니다. 512×512 · 4스텝 단일 생성이며 결과 원본은 result.png입니다. 이전 생성 이력은 조회만 가능하며 재개할 수 없습니다. 현재 설정으로 새로 생성하세요.')
        current_identifier_state = gr.State('')
        def start_floor_generation(user_prompt_value,generation_tag_value,output_size_value,inference_step_value,generation_seed_value,add_margins_value,automatic_seed_enabled):
            generation_seed_value = select_generation_seed_value(generation_seed_value, automatic_seed_enabled)
            generation_result_record = execute_floor_gateway('generate',{'action':'generate','user_prompt':user_prompt_value,'tag':generation_tag_value,'width':int(output_size_value),'height':int(output_size_value),'steps':int(inference_step_value),'seed':int(generation_seed_value),'add_margins':add_margins_value})
            return generation_result_record['id'], '생성 요청: '+generation_result_record['id']+' · '+generation_result_record['status']+f' · 사용 시드: {generation_seed_value}', generation_seed_value
        bind_gpu_generation_confirmation(generation_start_button,start_floor_generation,[user_prompt_control,generation_tag_control,output_size_control,inference_step_control,generation_seed_control,add_margins_control,automatic_seed_control],[current_identifier_state,generation_status_control,generation_seed_control], generation_readiness_callback=lambda current_ready_value: current_ready_value, generation_readiness_inputs=[current_prompt_ready])
        def restore_floor_inputs(history_record_value):
            saved_request_record = history_record_value['request']
            return [saved_request_record['user_prompt'],saved_request_record.get('tag',''),512,4,saved_request_record['seed'],saved_request_record.get('add_margins',False),False]
        read_history_page,history_output_values = build_generation_history_view(execute_floor_gateway,server_base_address,'초기화하면 바닥 타일 생성 기록과 결과 파일을 삭제합니다. 실행 중에는 사용할 수 없습니다.',restore_floor_inputs,[user_prompt_control,generation_tag_control,output_size_control,inference_step_control,generation_seed_control,add_margins_control,automatic_seed_control],record_folder_route='/floor-tile-generator',allow_individual_delete=True)
        interface_block_value.load(lambda:read_history_page(1),outputs=history_output_values)
        current_identifier_state.change(lambda:read_history_page(1),outputs=history_output_values,queue=False)
    return interface_block_value

if __name__=='__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--root-path',default='/management/frame/floor-tile-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_floor_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path)
