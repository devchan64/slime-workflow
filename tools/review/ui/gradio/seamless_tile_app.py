"""3×3 연결 보정 생성기의 공용 게이트웨이 GUI."""
import argparse
import html
import gradio as gr
from qwen_2511_app import (
    WORKFLOW_ROOT_DIRECTORY,
    build_generation_history_view, build_execution_logs,
    bind_gpu_generation_confirmation,
    build_reference_request,
    execute_management_command, result_preview_html,
)
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.domains.image.seamless_generation import validate_seamless_request
from tools.review.domains.image.seamless_pattern import build_pattern_request


def describe_seamless_prompt(user_prompt_text):
    try:
        _, prompt_source_record = build_pattern_request(user_prompt_text)
        return '\n\n'.join(f"{(1,3,5)[current_stage_index]}단계 · 사용자 {len(user_prompt_text.split()) if current_stage_index == 0 else 0}단어 · 고정 {len(prompt_source_record[current_prompt_key].split())}단어 · 최종 {len(current_prompt_text.split())}단어\n\n{current_prompt_text}" for current_stage_index,(current_prompt_key,current_prompt_text) in enumerate(zip(('grid_prompt','horizontal_prompt','vertical_prompt'),prompt_source_record['stage_prompts'])))
    except ValueError as current_prompt_error:
        return str(current_prompt_error)



def render_seamless_previews(generation_status_record):
    completed_preview_values = []
    from tools.review.domains.image.seamless_directional import DIRECTIONAL_PREVIEW_LABELS
    preview_stage_labels = DIRECTIONAL_PREVIEW_LABELS
    if generation_status_record.get('pipeline',{}).get('total') != 5:
        preview_stage_labels = tuple((current_file_name, '저장된 결과 · '+current_file_name) for current_file_name in generation_status_record.get('previews',{}))
    for preview_file_name, preview_label_text in preview_stage_labels:
        preview_image_url = generation_status_record.get('previews',{}).get(preview_file_name)
        if preview_image_url:
            completed_preview_values.append('<h3>'+html.escape(preview_label_text)+'</h3>'+result_preview_html(preview_image_url))
    preview_html_value = completed_preview_values[-1] if completed_preview_values else '<p>현재 단계를 처리하고 있습니다. 완료 후 결과가 표시됩니다.</p>'
    if len(completed_preview_values)>1:
        preview_html_value += '<details><summary>이전 단계 결과 비교</summary>'+''.join(completed_preview_values[:-1])+'</details>'
    return preview_html_value

def build_seamless_interface(server_base_address):
    def execute_seamless_command(command_name_value, command_payload_value):
        return execute_management_command('seamless-tile', command_name_value, command_payload_value)

    def restore_seamless_inputs(current_history_record):
        current_request_record = current_history_record['request']
        return (current_request_record['seamless_tile']['user_prompt'],current_request_record.get('tag',''),40,current_request_record['seed'])

    with gr.Blocks(title='Qwen2.1 심리스 패턴 생성기') as interface_blocks_value:
        gr.Markdown('## Qwen2.1 심리스 패턴 생성기\n패턴 생성 → 가로 3등분·3열 배열 → 좌우 연결 → 세로 3등분·3행 배열 → 상하 연결')
        gr.Markdown('### 1. 패턴 입력\n각 단계 결과를 확인한 뒤 다음 단계로 진행합니다. 가로는 좌·중·우, 세로는 상·중·하로 나눕니다.')
        with gr.Row():
            user_prompt_control = gr.Textbox(label='패턴 프롬프트', placeholder='예: 잔디와 들꽃', lines=2, scale=2, min_width=240)
            generation_tag_control = gr.Textbox(label='생성 이력 태그 · 선택 사항', lines=2, scale=1, min_width=180)
        with gr.Accordion('생성 설정 · 실제 프롬프트 확인', open=False):
            gr.Markdown('Qwen Image 2.1 · 1단계 768×768 · 연결 보정 768×768. 마스크 없이 원본 배열의 경계를 연결합니다. 최종 산출물은 중앙 256×256 타일입니다.')
            with gr.Row():
                generation_step_control = gr.Number(value=40, label='생성 스텝 · 고정', interactive=False, precision=0)
                generation_seed_control = build_generation_seed(10107)
            prompt_preview_control = gr.Markdown(describe_seamless_prompt(''))
        user_prompt_control.change(describe_seamless_prompt, user_prompt_control, prompt_preview_control, queue=False)
        generation_start_button = gr.Button('새 패턴 · 1단계 실행', variant='primary')
        with gr.Accordion('이전 작업 이어서 진행', open=False):
            gr.Markdown('생성 이력의 ID를 복사해 입력하세요. 완료한 단계를 유지하고 이어갑니다.')
            with gr.Row():
                saved_identifier_input = gr.Textbox(label='이전 작업 ID', lines=1, max_lines=1, scale=3, min_width=240)
                load_stage_button = gr.Button('작업 불러오기', scale=1, min_width=120)
        gr.Markdown('### 2. 현재 단계 검수')
        generation_identifier_control = build_generation_identifier()
        generation_status_control = gr.Markdown('패턴을 새로 생성하거나 이전 작업을 불러오세요.')
        gr.Markdown('예상 남은 시간·완료 시각: 계산 중. 단계별 추정 근거를 수집하고 있습니다.')
        generation_preview_control = gr.HTML('<p>단계가 완료되면 이곳에 결과가 표시됩니다.</p>')
        gr.Markdown('### 3. 확인 후 다음 단계\n각 단계 완료 후 검수 대기하며, 한 단계씩 진행합니다. 실행 중 일시정지는 현재 단계를 저장한 뒤 적용됩니다. 반복 검수 후 채택하며 정식 에셋에는 자동 등록하지 않습니다.')
        with gr.Row():
            next_stage_button = gr.Button('결과 확인 · 다음 단계 / 재개', variant='primary', interactive=False)
            pause_stage_button = gr.Button('현재 단계 후 일시정지', interactive=False)
            refresh_stage_button = gr.Button('상태 새로고침')
        gr.Markdown('다음 단계는 검수 대기·실패·중지 상태에서 사용할 수 있습니다. 작업이 없으면 먼저 생성하거나 불러오세요.')
        execution_log_control, refresh_log_control, _ = build_execution_logs()
        history_page_callback, history_output_controls = build_generation_history_view(
            execute_seamless_command, server_base_address,
            '현재 생성기의 이력·입력·결과·로그를 삭제합니다. 실행 중에는 초기화할 수 없습니다.',
            restore_input_callback=restore_seamless_inputs,
            restore_output_components=[user_prompt_control,generation_tag_control,generation_step_control,generation_seed_control],
            result_renderer_callback=lambda selected_job_identifier, current_status_record, server_address_value: render_seamless_previews(current_status_record),
            record_folder_route='/seamless-tile-generator', allow_individual_delete=True)

        def start_seamless_generation(user_prompt_text, generation_tag_text, generation_step_count, generation_seed_value):
            try:
                request_record_value = build_reference_request(user_prompt_text,generation_tag_text,[],768,768,generation_step_count,generation_seed_value)
                validate_seamless_request(request_record_value)
                generation_record_value = execute_seamless_command('generate', request_record_value)
            except (ValueError,OSError) as generation_request_error:
                raise gr.Error(str(generation_request_error)) from generation_request_error
            return generation_record_value['id'], '작업을 대기열에 등록했습니다.'

        bind_gpu_generation_confirmation(generation_start_button,start_seamless_generation,[user_prompt_control,generation_tag_control,generation_step_control,generation_seed_control],[generation_identifier_control,generation_status_control])

        def refresh_seamless_status(generation_identifier_text, refresh_log_enabled):
            if not generation_identifier_text:
                return gr.skip(), gr.skip(), gr.skip(), gr.update(interactive=False), gr.update(interactive=False)
            generation_status_record = execute_seamless_command('status', {'id':generation_identifier_text})
            preview_html_value = render_seamless_previews(generation_status_record)
            return '상태: '+generation_status_record['status']+' · '+generation_status_record.get('pipeline',{}).get('stage','대기 중'), generation_status_record.get('log','') if refresh_log_enabled else gr.skip(), preview_html_value, gr.update(interactive=generation_status_record['status'] in ('paused','failed','cancelled')), gr.update(interactive=generation_status_record['status'] in ('running','queued'))

        def continue_seamless_stage(generation_identifier_text):
            execute_seamless_command('resume', {'id':generation_identifier_text})
            return '다음 미완료 단계를 대기열에 등록했습니다.'

        def pause_seamless_stage(generation_identifier_text):
            return execute_seamless_command('pause', {'id':generation_identifier_text})['message']

        def load_seamless_stage(generation_identifier_text):
            execute_seamless_command('status', {'id':generation_identifier_text.strip()})
            return generation_identifier_text.strip()

        bind_gpu_generation_confirmation(next_stage_button,continue_seamless_stage,generation_identifier_control,generation_status_control)
        pause_stage_button.click(pause_seamless_stage,generation_identifier_control,generation_status_control,queue=False)
        load_stage_button.click(load_seamless_stage,saved_identifier_input,generation_identifier_control,queue=False)
        history_output_controls[0].change(lambda selected_job_identifier: selected_job_identifier or gr.skip(),history_output_controls[0],generation_identifier_control,queue=False)
        generation_identifier_control.change(refresh_seamless_status,[generation_identifier_control,refresh_log_control],[generation_status_control,execution_log_control,generation_preview_control,next_stage_button,pause_stage_button],queue=False)
        interface_blocks_value.load(lambda:history_page_callback(1), outputs=history_output_controls)
        refresh_stage_button.click(refresh_seamless_status,[generation_identifier_control,refresh_log_control],[generation_status_control,execution_log_control,generation_preview_control,next_stage_button,pause_stage_button],queue=False)
        gr.Timer(2).tick(refresh_seamless_status,[generation_identifier_control,refresh_log_control],[generation_status_control,execution_log_control,generation_preview_control,next_stage_button,pause_stage_button],show_progress='hidden')
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--root-path',default='/management/frame/seamless-tile-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_seamless_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,allowed_paths=[])
