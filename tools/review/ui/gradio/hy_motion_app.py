"""MoMask 구성과 공용 이력·재생기를 사용하는 HY-Motion GUI 클라이언트."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from generators.hy_motion.contracts import load_generation_defaults, validate_generation_request, read_encoder_system_prompt, build_encoder_input_preview, load_motion_presets
from generators.hy_motion.contracts import MAXIMUM_DURATION_SECONDS
from tools.review.common.management_client import execute_remote_management_command as execute_management_command
from tools.review.common.gradio_frame_player import build_browser_frame_player
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_identifiers import build_generation_identifier

MOTION_DIRECTION_LABELS = [('전방 좌측', 'down_left'), ('전방 우측', 'down_right'), ('후방 좌측', 'up_left'), ('후방 우측', 'up_right')]


def execute_motion_command(operation_command_name, command_payload_value):
    return execute_management_command('hy-motion', operation_command_name, command_payload_value)


def start_motion_generation(current_prompt_text, current_duration_value, current_seed_value, current_direction_names, current_tag_value):
    current_request_record = validate_generation_request({'prompt': current_prompt_text, 'duration_seconds': current_duration_value, 'seed': current_seed_value, 'directions': current_direction_names, 'tag': current_tag_value})
    current_response_record = execute_motion_command('generate', current_request_record)
    return current_response_record['id'], '작업 접수 완료 · 생성 이력에서 상태·로그·중지·재개를 확인하세요.'


def restore_motion_inputs(current_history_record):
    current_request_record = current_history_record['request']
    if current_request_record.get('action') == 'prepare':
        raise gr.Error('모델 준비 작업에는 복원할 모션 입력이 없습니다.')
    current_request_record = validate_generation_request(current_request_record)
    return tuple(current_request_record[current_field_name] for current_field_name in ('prompt', 'duration_seconds', 'seed', 'directions', 'tag'))


def render_motion_result(generation_job_identifier, current_status_record, server_base_address):
    current_result_record = current_status_record.get('result')
    if current_status_record['status'] != 'completed' or not current_result_record or current_result_record.get('kind') != 'motion':
        return json.dumps({'frames': {}, 'message': '모션 완료 결과를 선택하세요. 준비·실패·실행 상태는 로그에서 확인할 수 있습니다.'}, ensure_ascii=False)
    current_result_url = server_base_address + '/hy-motion-generator/jobs/' + generation_job_identifier + '/result/'
    current_download_records = [{'label': '원본 모션 NPZ', 'url': current_result_url + 'motion.npz'}, {'label': '출처·실행 설정', 'url': current_result_url + 'provenance.json'}]
    current_download_records.extend({'label': current_gif_record['label'], 'url': current_result_url + current_gif_record['path']} for current_gif_record in current_result_record.get('gifs', []))
    return json.dumps({'frames': {current_direction_name: [[current_result_url + current_direction_name + f'/frame-{current_frame_index:04d}.png'] for current_frame_index in range(1, current_result_record['frames'] + 1)] for current_direction_name in current_result_record['directions']}, 'directUrls': True, 'panels': ['HY-Motion 원본 관절 · 제자리 보정 없음'], 'sourceFrames': {current_direction_name: current_result_record['source_indices'] for current_direction_name in current_result_record['directions']}, 'downloads': current_download_records}, ensure_ascii=False)


def describe_prompt_words(current_prompt_text):
    current_word_count = len(current_prompt_text.split())
    current_system_count = len(read_encoder_system_prompt().split())
    current_encoder_count = len(build_encoder_input_preview(current_prompt_text).split())
    return f'동작 프롬프트·CLIP 입력 {current_word_count}단어 / 29단어 이하 · 고정 시스템 {current_system_count}단어 · Qwen 최종 입력 {current_encoder_count}단어(템플릿 포함). 방향은 카메라 설정으로만 사용합니다.'


def apply_motion_preset(current_preset_name):
    current_preset_records = load_motion_presets()
    if current_preset_name not in current_preset_records:
        raise ValueError('지원하지 않는 모션 프리셋입니다.')
    current_preset_record = current_preset_records[current_preset_name]
    return current_preset_record['prompt'], current_preset_record['duration_seconds']


def build_hymotion_interface(server_base_address):
    current_default_values = load_generation_defaults()
    current_preset_records = load_motion_presets()
    with gr.Blocks(title='HY-Motion 모션 생성기') as current_interface_blocks:
        gr.Markdown('## HY-Motion 모션 생성기\n영문 동작을 입력해 원본 모션을 만들고, 방향별 미리보기를 비교합니다. 제자리·방향 고정·루프 보정은 적용하지 않습니다.')
        with gr.Accordion('고정 설정 · 모델 준비', open=True):
            gr.Markdown('HY-Motion 1.0 Lite · 50스텝 · CFG 5 · 샘플 1개 · 원본 30 FPS / 미리보기 8 FPS\n\nQwen 가중치 CPU 메모리 오프로드·레이어별 CUDA 연산 → 인코더 해제 → 모션 GPU 생성. 8GB 장비 실행은 실측 결과로 확인합니다. 프롬프트 재작성·길이 자동 추정은 사용하지 않습니다.')
            current_model_status = gr.Markdown('모델 준비 상태 확인 중…')
            with gr.Row():
                current_prepare_button = gr.Button('모델 준비 · 최초 다운로드')
                current_refresh_button = gr.Button('준비 상태 새로고침')
        current_preset_selector = gr.Dropdown(choices=[(current_preset_record['label'], current_preset_name) for current_preset_name, current_preset_record in current_preset_records.items()], value=None, label='동작 프리셋 · 선택하면 프롬프트와 길이만 변경')
        with gr.Row():
            current_prompt_input = gr.Textbox(value=current_default_values['prompt'], label='동작 프롬프트 · 영어', lines=4)
            current_direction_input = gr.CheckboxGroup(MOTION_DIRECTION_LABELS, value=current_default_values['directions'], label='미리보기 방향 · 전체/개별 선택')
        current_word_summary = gr.Markdown(describe_prompt_words(current_default_values['prompt']))
        current_prompt_input.change(describe_prompt_words, current_prompt_input, current_word_summary, queue=False)
        with gr.Accordion('Qwen 인코더 최종 입력 · 고정 시스템 문구 포함', open=False):
            current_encoder_preview = gr.Textbox(value=build_encoder_input_preview(current_default_values['prompt']), interactive=False, lines=6, label='실제 모델 입력 · 실행 시 tokenizer 결과와 대조')
        current_prompt_input.change(build_encoder_input_preview, current_prompt_input, current_encoder_preview, queue=False)
        with gr.Row():
            current_duration_input = gr.Number(value=current_default_values['duration_seconds'], minimum=1, maximum=MAXIMUM_DURATION_SECONDS, step=.1, label='모션 길이(초)')
            current_seed_input = build_generation_seed(current_default_values['seed'])
            current_tag_input = gr.Textbox(label='생성 이력 태그 · 선택', max_lines=1)
        current_generate_button = gr.Button('모션 생성 시작', variant='primary', interactive=False)
        current_preset_selector.input(apply_motion_preset, current_preset_selector, [current_prompt_input, current_duration_input], queue=False)
        current_identifier_view = build_generation_identifier('접수한 생성 ID')
        current_status_view = gr.Markdown('모델 준비 상태를 확인한 뒤 생성할 수 있습니다.')
        current_eta_view = gr.Markdown('예상 남은 시간: 계산 중 · 예상 완료 시각: 계산 중\n\n추정 근거: 동일 조건 완료 표본 없음. GPU 대기·준비·추론 시간을 아직 추정할 수 없습니다.')

        def refresh_generation_readiness(current_prompt_text, current_duration_value, current_seed_value, current_direction_names, current_tag_value):
            current_model_record = execute_motion_command('model-status', {})
            try:
                validate_generation_request({'prompt': current_prompt_text, 'duration_seconds': current_duration_value, 'seed': current_seed_value, 'directions': current_direction_names, 'tag': current_tag_value})
                current_input_message = '입력 확인 완료' if current_model_record['ready'] else '모델 준비 버튼을 실행한 뒤 완료를 기다리세요.'
                current_can_generate = current_model_record['ready']
            except ValueError as current_input_error:
                current_input_message = str(current_input_error)
                current_can_generate = False
            return current_model_record['message'] + '\n\n' + current_input_message, gr.update(interactive=current_can_generate)

        def start_model_preparation():
            current_prepare_record = execute_motion_command('prepare', {})
            return current_prepare_record['id'], '모델 준비 작업 접수 완료 · 생성 이력에서 로그를 확인하세요.'

        current_input_components = [current_prompt_input, current_duration_input, current_seed_input, current_direction_input, current_tag_input]
        bind_gpu_generation_confirmation(current_generate_button, start_motion_generation, current_input_components, [current_identifier_view, current_status_view])
        bind_gpu_generation_confirmation(current_prepare_button, start_model_preparation, [], [current_identifier_view, current_status_view])
        current_refresh_button.click(refresh_generation_readiness, current_input_components, [current_model_status, current_generate_button], queue=False)
        for current_input_component in current_input_components:
            current_input_component.change(refresh_generation_readiness, current_input_components, [current_model_status, current_generate_button], queue=False)
        current_interface_blocks.load(refresh_generation_readiness, current_input_components, [current_model_status, current_generate_button])

        def refresh_current_progress(generation_job_identifier):
            if not generation_job_identifier:
                return gr.skip(), gr.skip()
            current_status_record = execute_motion_command('status', {'id': generation_job_identifier})
            current_status_text = current_status_record['status'] + ' · ' + current_status_record.get('message', current_status_record.get('error', ''))
            current_eta_record = current_status_record['eta']
            current_remaining_text = '계산 중' if current_eta_record['remaining'] is None else str(current_eta_record['remaining']) + '초'
            current_eta_text = '작업 종료 · 예상 시간 갱신 종료' if current_status_record['status'] not in ('running', 'queued') else f'예상 남은 시간: {current_remaining_text} · 예상 완료 시각: {current_eta_record["completion"] or "계산 중"}\n\n추정 근거: {current_eta_record["basis"]}'
            return current_status_text, current_eta_text

        gr.Timer(2).tick(refresh_current_progress, current_identifier_view, [current_status_view, current_eta_view], show_progress='hidden')
        current_read_history, current_history_outputs = build_generation_history_view(execute_motion_command, server_base_address, '목록만 초기화하며 모션·로그 원본은 보존합니다. 실행 중에는 초기화할 수 없습니다.', restore_input_callback=restore_motion_inputs, restore_output_components=current_input_components, result_renderer_callback=render_motion_result, result_component_factory=build_browser_frame_player, record_folder_route='/hy-motion-generator')
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--port', type=int, required=True)
    current_argument_parser.add_argument('--review-port', type=int, required=True)
    current_argument_parser.add_argument('--owner-pid', type=int, required=True)
    current_argument_parser.add_argument('--root-path', default='/management/frame/hy-motion-generator/')
    current_argument_values = current_argument_parser.parse_args()

    def monitor_parent_process():
        while os.getppid() == current_argument_values.owner_pid:
            time.sleep(1)
        os._exit(0)

    threading.Thread(target=monitor_parent_process, daemon=True).start()
    build_hymotion_interface(f'http://127.0.0.1:{current_argument_values.review_port}').queue().launch(server_name='127.0.0.1', server_port=current_argument_values.port, root_path=current_argument_values.root_path, allowed_paths=[])
