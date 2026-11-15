"""공용 게이트웨이로 프롬프트 번역을 요청하는 화면."""
import gradio as gr
from pathlib import Path
from tools.review.common.management_client import execute_remote_management_command


def submit_translation_request(translation_source_text, translation_target_language):
    try:
        translation_response_record = execute_remote_management_command('prompt-translation', 'translation-submit', {'text': translation_source_text, 'target_language': translation_target_language})
        return translation_response_record['id'], 'GPU 대기열에 등록했습니다.', '', translation_source_text
    except Exception as translation_request_error:
        return '', '요청 실패: ' + str(translation_request_error), '', ''


def refresh_translation_status(translation_job_identifier):
    if not translation_job_identifier:
        return '번역 작업 ID를 입력하세요.', '', ''
    try:
        translation_response_record = execute_remote_management_command('prompt-translation', 'translation-status', {'id': translation_job_identifier})
        translation_state_record = translation_response_record['status']
        translation_result_record = translation_response_record.get('result') or {}
        translation_state_text = translation_state_record['status']
        if translation_state_record.get('queue_position'):
            translation_state_text += ' · 대기 순서 ' + str(translation_state_record['queue_position'])
        if translation_state_record.get('error'):
            translation_state_text += ' · ' + translation_state_record['error']
        return translation_state_text, translation_result_record.get('text', ''), translation_response_record['request']['text']
    except Exception as translation_request_error:
        return '조회 실패: ' + str(translation_request_error), '', ''


def cancel_translation_request(translation_job_identifier):
    try:
        execute_remote_management_command('prompt-translation', 'translation-cancel', {'id': translation_job_identifier})
        return '중지를 요청했습니다. 상태를 새로고침하세요.'
    except Exception as translation_request_error:
        return '중지 실패: ' + str(translation_request_error)


def refresh_translation_history():
    try:
        translation_history_record = execute_remote_management_command('prompt-translation', 'translation-history', {})
        return [[current_record['id'], current_record['status']['status'], current_record['request']['target_language']] for current_record in translation_history_record['records']]
    except Exception as translation_request_error:
        raise gr.Error('이력 조회 실패: ' + str(translation_request_error)) from translation_request_error


def build_translation_interface():
    with gr.Blocks(title='프롬프트 번역') as translation_interface_blocks:
        with gr.Accordion('변경 기록', open=False):
            gr.Markdown((Path(__file__).resolve().parents[4] / 'generators/prompt_translation/CHANGELOG.md').read_text(encoding='utf-8'))
        gr.Markdown('## 프롬프트 번역\n한국어 원문을 영어 또는 중국어 간체로 번역합니다. 결과를 확인하고 직접 수정한 뒤 필요한 생성기에 복사하세요. 번역은 생성을 실행하지 않습니다.\n\nTranslateGemma 4B · ROCm BF16 · [Gemma 이용약관](https://ai.google.dev/gemma/terms) · 모델과 실행 환경 준비 필요')
        translation_source_control = gr.Textbox(label='한국어 원문', lines=5)
        translation_target_control = gr.Dropdown(choices=[('영어', 'en'), ('중국어 간체', 'zh-CN')], value='en', label='목표 언어')
        translation_submit_control = gr.Button('번역 대기열에 추가', variant='primary')
        translation_job_control = gr.Textbox(label='번역 작업 ID')
        translation_status_control = gr.Markdown('원문과 목표 언어를 선택하세요.')
        with gr.Row():
            translation_refresh_control = gr.Button('상태·결과 새로고침')
            translation_cancel_control = gr.Button('번역 중지')
        translation_original_control = gr.Textbox(label='요청 당시 원문', lines=4, interactive=False)
        translation_result_control = gr.Textbox(label='번역 결과 · 수정 가능', lines=5)
        gr.Markdown('결과는 요청 당시 원문을 기준으로 합니다. 현재 원문이 바뀌었는지 확인하세요. 실행 시간은 관측 이력이 없어 계산 중입니다.')
        with gr.Accordion('번역 이력', open=False):
            translation_history_control = gr.Dataframe(headers=['작업 ID', '상태', '목표 언어'], interactive=False)
            gr.Button('이력 새로고침').click(refresh_translation_history, outputs=translation_history_control)
        translation_submit_control.click(submit_translation_request, [translation_source_control, translation_target_control], [translation_job_control, translation_status_control, translation_result_control, translation_original_control])
        translation_refresh_control.click(refresh_translation_status, translation_job_control, [translation_status_control, translation_result_control, translation_original_control])
        translation_cancel_control.click(cancel_translation_request, translation_job_control, translation_status_control)
    return translation_interface_blocks
