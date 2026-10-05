"""애니메이션 분리 작업의 Gradio 클라이언트. 추론은 공용 게이트웨이가 실행한다."""
import argparse
import html
import json
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_history import build_generation_history_view, HISTORY_CARD_SELECTION_SCRIPT, format_generation_status
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.domains.image.animation_separation import load_separation_defaults


def execute_separation_gateway(current_command_name, current_payload_record):
    return execute_remote_management_command('animation-separation', current_command_name, current_payload_record)


def build_separation_request(current_source_identifier, current_start_frame, current_end_frame, current_output_size, current_seed_value, current_prompt_text, current_outfit_prompt, current_sample_identifier):
    for current_number_value in (current_start_frame, current_end_frame, current_output_size, current_seed_value):
        if isinstance(current_number_value, bool) or not isinstance(current_number_value, (int, float)) or int(current_number_value) != current_number_value:
            raise ValueError('프레임·크기·시드는 정수여야 합니다.')
    return {'action': 'generate', 'source_id': current_source_identifier, 'start_frame': int(current_start_frame), 'end_frame': int(current_end_frame), 'width': int(current_output_size), 'height': int(current_output_size), 'seed': int(current_seed_value), 'steps': 40, 'prompt': current_prompt_text, 'outfit_prompt': current_outfit_prompt, 'sample_id': current_sample_identifier.strip()}


def describe_separation_prompt(current_prompt_text):
    current_word_count = len(current_prompt_text.split())
    return f'프롬프트 {current_word_count}단어 · 최종 입력 {current_word_count}단어 · 추가 문구 없음 · 1~99단어'


def build_separation_preview(current_server_address, current_job_identifier):
    # 재생·프레임 이동은 iframe 안에서 처리한다. 프레임마다 Python을 호출하지 않는다.
    if not current_job_identifier:
        return '<p>완료된 생성 ID를 조회하면 동기 재생을 표시합니다.</p>'
    import re
    from tools.review.domains.image.animation_separation import SEPARATION_JOB_PATTERN
    if not re.fullmatch(SEPARATION_JOB_PATTERN, current_job_identifier):
        raise ValueError('생성 ID 형식 오류')
    current_result_base = current_server_address + '/animation-separation/jobs/' + current_job_identifier + '/'
    current_preview_document = (Path(__file__).parents[1] / 'character_animation/separation-preview.html').read_text().replace('__RESULT_BASE__', json.dumps(current_result_base))
    return '<iframe title="원본과 분리 후보 동기 재생" style="width:100%;height:760px;border:0" srcdoc="' + html.escape(current_preview_document, quote=True) + '"></iframe>'


def build_separation_interface(current_server_address):
    with gr.Blocks(title='캐릭터 복장 분리 생성기') as interface_blocks_value:
        gr.Markdown('## 캐릭터 복장 분리 생성기\n같은 원본에서 신체 베이스와 사람을 제거한 복장을 각각 생성합니다. 두 결과는 별도 파일로 저장합니다. 먼저 한 프레임을 확인한 후 범위 생성을 실행하세요.')
        with gr.Tabs():
            with gr.Tab("생성 설정"):
                current_source_control = gr.Dropdown([], label='원본 애니메이션', interactive=True)
                current_source_refresh = gr.Button('등록 원본 새로고침')
                current_source_records = gr.State([])
                current_source_summary = gr.Markdown('원본을 불러오는 중입니다.')
                with gr.Row():
                    current_start_control = gr.Number(value=1, precision=0, minimum=1, label='시작 프레임 · 샘플 프레임')
                    current_end_control = gr.Number(value=1, precision=0, minimum=1, label='끝 프레임')
                current_size_control = gr.Dropdown([512, 768], value=768, label='출력 크기 · 정사각형')
                current_seed_control = build_generation_seed()
                gr.Markdown('고정: Qwen Image 2.1 · 40스텝 · 프레임당 원본 참조 1장 · 베이스와 복장 각 1회 생성. 원본은 덮어쓰지 않습니다.')
                current_prompt_control = gr.Textbox(value=load_separation_defaults()['prompt'], lines=6, label='1. 신체 베이스 프롬프트')
                current_word_summary = gr.Markdown(describe_separation_prompt(load_separation_defaults()['prompt']))
                current_prompt_control.change(describe_separation_prompt, current_prompt_control, current_word_summary, queue=False)
                current_outfit_control = gr.Textbox(value=load_separation_defaults()['outfit_prompt'], lines=5, label='2. 사람 제거·복장 프롬프트')
                current_outfit_summary = gr.Markdown(describe_separation_prompt(load_separation_defaults()['outfit_prompt']))
                current_outfit_control.change(describe_separation_prompt, current_outfit_control, current_outfit_summary, queue=False)
                current_sample_button = gr.Button('1프레임 샘플 생성', variant='primary')
                current_sample_identifier = gr.Textbox(lines=1, max_lines=1, label='검수한 샘플 ID', info='완료된 1프레임 샘플을 확인한 뒤 ID를 입력하세요. 설정 변경 시 새 샘플이 필요합니다.')
                current_batch_button = gr.Button('검수한 설정으로 범위 생성')
                gr.Markdown('범위 생성 조건: 동일 원본·프롬프트·크기·시드의 완료 샘플. 최대 64프레임.')
            with gr.Tab("결과 검수"):
                current_job_control = gr.Textbox(lines=1, max_lines=1, label='조회할 생성 ID')
                current_status_output = gr.Markdown('예상 남은 시간·완료 시각: 추정 자료 수집 중입니다. 프레임별 진행은 상태에서 표시합니다.')
                with gr.Row():
                    current_refresh_button = gr.Button('상태·결과 조회')
                    current_cancel_button = gr.Button('선택 작업 중지')
                    current_resume_button = gr.Button('선택 작업 재개')
                current_preview_output = gr.HTML(build_separation_preview(current_server_address, ''))
                current_download_output = gr.Markdown('신규 베이스·복장은 RGBA 후보입니다. 포즈·위치·비율·배경 잔상과 흰 의복 경계를 검수하세요.')
        current_log_output, current_log_refresh, _ = build_execution_logs()
        def load_catalog_controls():
            current_catalog_record = execute_separation_gateway('catalog', {})
            current_sources_list = current_catalog_record['sources']
            return gr.update(choices=[(current_source_record['label'], current_source_record['id']) for current_source_record in current_sources_list]), current_sources_list, f'등록 원본 {len(current_sources_list)}개 · 선택하면 프레임 범위를 표시합니다.'
        def select_source_range(current_source_identifier, current_sources_list):
            if not current_source_identifier:
                return gr.skip(), gr.skip(), '원본 애니메이션을 선택하세요.'
            current_source_record = next(current_source_record for current_source_record in current_sources_list if current_source_record['id'] == current_source_identifier)
            return 1, current_source_record['frames'], f"{current_source_record['frames']}프레임 · 원본 앵커는 기록으로 보존하며 AI 결과의 앵커 일치를 보장하지 않습니다."
        current_source_refresh.click(load_catalog_controls, outputs=[current_source_control, current_source_records, current_source_summary], queue=False)
        current_source_control.change(select_source_range, [current_source_control, current_source_records], [current_start_control, current_end_control, current_source_summary], queue=False)
        def start_separation_job(*current_argument_values):
            try:
                current_request_record = build_separation_request(*current_argument_values)
                current_job_record = execute_separation_gateway('generate', current_request_record)
            except (ValueError, RuntimeError) as current_error_value:
                raise gr.Error(str(current_error_value)) from current_error_value
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다. 결과 검수 탭에서 상태·결과 조회로 확인하세요.'
        def start_sample_job(current_source_identifier, current_start_frame, current_output_size, current_seed_value, current_prompt_text, current_outfit_prompt):
            return start_separation_job(current_source_identifier, current_start_frame, current_start_frame, current_output_size, current_seed_value, current_prompt_text, current_outfit_prompt, '')
        bind_gpu_generation_confirmation(current_sample_button, start_sample_job, [current_source_control, current_start_control, current_size_control, current_seed_control, current_prompt_control, current_outfit_control], [current_job_control, current_status_output])
        bind_gpu_generation_confirmation(current_batch_button, start_separation_job, [current_source_control, current_start_control, current_end_control, current_size_control, current_seed_control, current_prompt_control, current_outfit_control, current_sample_identifier], [current_job_control, current_status_output])
        def read_current_result(current_job_identifier, current_refresh_logs):
            if not current_job_identifier:
                raise gr.Error('생성 ID를 입력하세요.')
            current_status_record = execute_separation_gateway('status', {'id': current_job_identifier})
            current_frame_progress = current_status_record.get('separation', {})
            current_stage_label = {'base': '신체 베이스 생성', 'outfit': '복장 생성', 'completed': '완료'}.get(current_frame_progress.get('stage'), '대기')
            current_download_url = current_status_record.get('download')
            return ('상태: ' + format_generation_status(current_status_record) + f" · 완료 프레임 {current_frame_progress.get('completed', 0)}/{current_frame_progress.get('total', '?')} · 단계 {current_stage_label}" + ('' if current_status_record.get('status') == 'completed' else ' · 예상 남은 시간·완료 시각: 추정 자료 수집 중'), current_status_record.get('log', '') if current_refresh_logs else gr.skip(), build_separation_preview(current_server_address, current_job_identifier) if current_download_url else gr.skip(), f'[후보 시트·원본·메타데이터 ZIP 다운로드]({current_server_address}{current_download_url})' if current_download_url else gr.skip())
        current_refresh_button.click(read_current_result, [current_job_control, current_log_refresh], [current_status_output, current_log_output, current_preview_output, current_download_output], queue=False)
        current_cancel_button.click(lambda current_job_identifier: str(execute_separation_gateway('cancel', {'id': current_job_identifier})), current_job_control, current_status_output)
        bind_gpu_generation_confirmation(current_resume_button, lambda current_job_identifier: str(execute_separation_gateway('resume', {'id': current_job_identifier})), current_job_control, current_status_output)
        def render_history_preview(current_job_identifier, current_status_record, current_server_address):
            return build_separation_preview(current_server_address, current_job_identifier) if current_status_record.get('download') else '<p>완료 후 분리 결과를 표시합니다.</p>'
        read_history_page, history_output_values = build_generation_history_view(execute_separation_gateway, current_server_address, '이 생성기의 후보·입력·로그를 삭제합니다. 실행 중에는 초기화할 수 없습니다.', result_renderer_callback=render_history_preview, record_folder_route='/animation-separation', allow_individual_delete=True)
        interface_blocks_value.load(load_catalog_controls, outputs=[current_source_control, current_source_records, current_source_summary])
        interface_blocks_value.load(lambda: read_history_page(1), outputs=history_output_values)
    return interface_blocks_value


if __name__ == '__main__':
    argument_parser_value = argparse.ArgumentParser()
    argument_parser_value.add_argument('--port', type=int, required=True)
    argument_parser_value.add_argument('--review-port', type=int, required=True)
    argument_parser_value.add_argument('--owner-pid', type=int, required=True)
    argument_parser_value.add_argument('--root-path', default='/management/frame/animation-separation/')
    current_arguments_value = argument_parser_value.parse_args()
    shared_styles_directory = Path(__file__).parents[1] / 'shared'
    shared_styles_text = (shared_styles_directory / 'management.css').read_text() + (shared_styles_directory / 'management-density.css').read_text()
    build_separation_interface(f'http://127.0.0.1:{current_arguments_value.review_port}').queue().launch(server_name='127.0.0.1', server_port=current_arguments_value.port, root_path=current_arguments_value.root_path, theme=gr.themes.Soft(), css=shared_styles_text, js=HISTORY_CARD_SELECTION_SCRIPT, allowed_paths=[])
