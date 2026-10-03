"""3×3 연결 보정 생성기의 공용 게이트웨이 GUI."""
import argparse
import html
import gradio as gr
from qwen_2511_app import (
    WORKFLOW_ROOT_DIRECTORY, LOG_PANEL_STYLES, MANAGEMENT_SHARED_STYLES,
    HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view, build_execution_logs,
    bind_gpu_generation_confirmation,
    build_reference_request,
    execute_management_command, result_preview_html,
)
from tools.review.domains.image.seamless_generation import validate_seamless_request
from tools.review.domains.image.seamless_pattern import build_pattern_request


def describe_seamless_prompt(user_prompt_text):
    try:
        _, prompt_source_record = build_pattern_request(user_prompt_text)
        return '\n\n'.join(f"{current_stage_index+1}단계 · 사용자 {len(user_prompt_text.split()) if current_stage_index == 0 else 0}단어 · 고정 {len(prompt_source_record[current_prompt_key].split())}단어 · 최종 {len(current_prompt_text.split())}단어\n\n{current_prompt_text}" for current_stage_index,(current_prompt_key,current_prompt_text) in enumerate(zip(('grid_prompt','repair_prompt'),prompt_source_record['stage_prompts'])))
    except ValueError as current_prompt_error:
        return str(current_prompt_error)


def build_seamless_interface(server_base_address):
    def execute_seamless_command(command_name_value, command_payload_value):
        return execute_management_command('seamless-tile', command_name_value, command_payload_value)

    def restore_seamless_inputs(current_history_record):
        current_request_record = current_history_record['request']
        return (current_request_record['seamless_tile']['user_prompt'],current_request_record.get('tag',''),40,current_request_record['seed'])

    with gr.Blocks(title='Qwen2.1 심리스 타일 생성기') as interface_blocks_value:
        gr.Markdown('## Qwen2.1 심리스 타일 생성기\n패턴 설명 → 3×3 패턴 생성 → 중앙 추출 → 별도 마스크 경계 보정 → 256 타일·반복 검수')
        with gr.Row():
            with gr.Column():
                user_prompt_control = gr.Textbox(label='패턴 프롬프트', placeholder='예: 잔디밭', lines=2)
                generation_tag_control = gr.Textbox(label='생성 이력 태그 · 선택 사항', lines=1)
                gr.Markdown('Qwen Image 2.1 · 1단계 768×768 · 2단계 512×512 · 최종 256×256. 원본과 별도 흑백 마스크를 참조합니다. 편집 폭은 가로·세로 16px이며 마스크 내부만 합성합니다.')
                with gr.Row():
                    generation_step_control = gr.Number(value=40, label='생성 스텝 · 고정', interactive=False, precision=0)
                    generation_seed_control = gr.Number(value=10107, precision=0, label='Seed')
                prompt_preview_control = gr.Markdown(describe_seamless_prompt(''))
                user_prompt_control.change(describe_seamless_prompt, user_prompt_control, prompt_preview_control, queue=False)
                gr.Markdown('예상 남은 시간·완료 시각: 계산 중. 이 생성기의 실행 이력이 아직 없어 추정 근거를 수집합니다.')
                generation_start_button = gr.Button('단계별 생성 시작', variant='primary')
                generation_status_control = gr.Markdown('패턴 프롬프트를 입력하세요.')
                generation_identifier_control = gr.Textbox(label='생성 ID', interactive=False, lines=1)
            with gr.Column():
                gr.Markdown('### 결과와 반복 검수\nAI 편집만으로 주기 경계를 보장하지 않습니다. 반복 미리보기에서 경계를 확인한 뒤 채택하세요. 정식 에셋에는 자동 등록하지 않습니다.')
                generation_preview_control = gr.HTML(result_preview_html(None))
        execution_log_control, refresh_log_control, _ = build_execution_logs()
        history_page_callback, history_output_controls = build_generation_history_view(
            execute_seamless_command, server_base_address,
            '현재 생성기의 이력·입력·결과·로그를 삭제합니다. 실행 중에는 초기화할 수 없습니다.',
            restore_input_callback=restore_seamless_inputs,
            restore_output_components=[user_prompt_control,generation_tag_control,generation_step_control,generation_seed_control],
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
                return gr.skip(), gr.skip(), gr.skip()
            generation_status_record = execute_seamless_command('status', {'id':generation_identifier_text})
            preview_html_value = result_preview_html(generation_status_record.get('image'))
            for preview_file_name, preview_label_text in (('grid-input.png','1단계 · 3×3 패턴'),('center-tile.png','중앙 타일'),('repair-input.png','2단계 입력 · 원본'),('repair-mask.png','2단계 입력 · 편집 마스크'),('repair-composite.png','마스크 내부 합성'),('grid-edited.png','2단계 · 채우기'),('tiled-preview.png','최종 반복 검수')):
                preview_image_url = generation_status_record.get('previews',{}).get(preview_file_name)
                if preview_image_url:
                    preview_html_value += '<h3>'+html.escape(preview_label_text)+'</h3>'+result_preview_html(preview_image_url)
            return '상태: '+generation_status_record['status']+' · '+generation_status_record.get('pipeline',{}).get('stage','대기 중'), generation_status_record.get('log','') if refresh_log_enabled else gr.skip(), preview_html_value

        interface_blocks_value.load(lambda:history_page_callback(1), outputs=history_output_controls)
        gr.Button('상태 새로고침').click(refresh_seamless_status,[generation_identifier_control,refresh_log_control],[generation_status_control,execution_log_control,generation_preview_control],queue=False)
        gr.Timer(2).tick(refresh_seamless_status,[generation_identifier_control,refresh_log_control],[generation_status_control,execution_log_control,generation_preview_control],show_progress='hidden')
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port',type=int,required=True)
    argument_parser_value.add_argument('--review-port',type=int,required=True)
    argument_parser_value.add_argument('--owner-pid',type=int,required=True)
    argument_parser_value.add_argument('--root-path',default='/management/frame/seamless-tile-generator/')
    parsed_argument_values = argument_parser_value.parse_args()
    build_seamless_interface(f'http://127.0.0.1:{parsed_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=parsed_argument_values.port,root_path=parsed_argument_values.root_path,theme=gr.themes.Soft(),js=HISTORY_CARD_SELECTION_SCRIPT,css=LOG_PANEL_STYLES+MANAGEMENT_SHARED_STYLES,allowed_paths=[])
