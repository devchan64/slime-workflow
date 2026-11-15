"""공용 게이트웨이로 프롬프트 번역을 요청하는 화면."""
import gradio as gr
from pathlib import Path
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_model_download import build_model_readiness_controls


def parse_translation_glossary(translation_glossary_text):
    translation_glossary_values = []
    for translation_line_text in (translation_glossary_text or '').splitlines():
        if not translation_line_text.strip():
            continue
        if translation_line_text.count('=>') != 1:
            raise ValueError('각 줄에 원문 => 번역어 형식으로 입력하세요.')
        translation_source_value, translation_target_value = translation_line_text.split('=>')
        translation_glossary_values.append({'source': translation_source_value.strip(), 'target': translation_target_value.strip()})
    return translation_glossary_values


def submit_translation_request(translation_source_text, translation_target_language, translation_glossary_text=''):
    try:
        translation_response_record = execute_remote_management_command('prompt-translation', 'translation-submit', {'text': translation_source_text, 'target_language': translation_target_language, 'glossary': parse_translation_glossary(translation_glossary_text)})
        return translation_response_record['id'], 'GPU 대기열에 등록했습니다.', '', translation_source_text, []
    except Exception as translation_request_error:
        return '', '요청 실패: ' + str(translation_request_error), '', '', []


def refresh_translation_status(translation_job_identifier):
    if not translation_job_identifier:
        return '번역 작업 ID를 입력하세요.', '', '', []
    try:
        translation_response_record = execute_remote_management_command('prompt-translation', 'translation-status', {'id': translation_job_identifier})
        translation_state_record = translation_response_record['status']
        translation_result_record = translation_response_record.get('result') or {}
        translation_state_text = translation_state_record['status']
        if translation_state_record.get('queue_position'):
            translation_state_text += ' · 대기 순서 ' + str(translation_state_record['queue_position'])
        if translation_state_record.get('error'):
            translation_state_text += ' · ' + translation_state_record['error']
        translation_term_rows = [[current_term['source'], current_term['target'], '일치' if current_term['status']=='matched' else '불일치 · 확인 필요', current_term.get('source_ref','')] for current_term in translation_result_record.get('term_checks', [])]
        if translation_result_record:
            if 'quality_checks' not in translation_result_record:
                translation_term_rows.append(['배치·조건', '이전 작업', '검사되지 않음', ''])
            for translation_quality_record in translation_result_record.get('quality_checks', []):
                translation_quality_label = {'matched': '표현 발견 · 문맥 확인', 'reversed': '행·열 역전', 'review': '확인 필요'}[translation_quality_record['status']]
                translation_term_rows.append([translation_quality_record['source'], translation_quality_record['target'], translation_quality_label, translation_quality_record['source_ref']])
        return translation_state_text, translation_result_record.get('text', ''), translation_response_record['request']['text'], translation_term_rows
    except Exception as translation_request_error:
        return '조회 실패: ' + str(translation_request_error), '', '', []


def search_translation_rag(translation_source_text):
    try:
        return execute_remote_management_command('prompt-translation', 'translation-rag', {'text':translation_source_text})
    except Exception as translation_search_error:
        raise gr.Error('작가 AI 색인 조회 실패: ' + str(translation_search_error)) from translation_search_error


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
        def execute_translation_model_command(translation_command_name, translation_payload_record):
            return execute_remote_management_command('prompt-translation', translation_command_name, translation_payload_record)
        build_model_readiness_controls(translation_interface_blocks, execute_translation_model_command, show_management_always=True)
        translation_source_control = gr.Textbox(label='한국어 원문', lines=5)
        translation_target_control = gr.Dropdown(choices=[('영어', 'en'), ('중국어 간체', 'zh-CN')], value='en', label='목표 언어')
        with gr.Accordion('확인할 용어 · 선택 사항', open=False):
            translation_glossary_control = gr.Textbox(label='원문 => 번역어', lines=3, placeholder='이슬온 => Iseulon', info='한 줄에 하나씩 확인한 표기를 입력합니다. 승인 용어와 함께 번역 결과를 비교하며 자동 치환하지 않습니다.')
        with gr.Accordion('작가 AI 문서에서 용어 후보 찾기', open=False):
            gr.Markdown('현재 색인에서 원문 단어가 일치하는 문서 근거를 찾습니다. 검색 결과는 승인된 번역어가 아니며 자동 적용하지 않습니다.')
            translation_rag_button = gr.Button('작가 AI 색인 검색')
            translation_rag_output = gr.JSON(label='후보 문서와 출처')
            translation_rag_button.click(search_translation_rag, translation_source_control, translation_rag_output, queue=False)
        translation_submit_control = gr.Button('번역 대기열에 추가', variant='primary')
        translation_job_control = gr.Textbox(label='번역 작업 ID')
        translation_status_control = gr.Markdown('원문과 목표 언어를 선택하세요.')
        with gr.Row():
            translation_refresh_control = gr.Button('상태·결과 새로고침')
            translation_cancel_control = gr.Button('번역 중지')
        translation_original_control = gr.Textbox(label='요청 당시 원문', lines=4, interactive=False)
        translation_result_control = gr.Textbox(label='번역 결과 · 수정 가능', lines=5)
        translation_check_control = gr.Dataframe(headers=['원문 항목', '번역 확인', '검사 결과', '근거'], interactive=False, label='용어·배치·조건 점검 · 일부 표현만 검사하며 문맥 확인이 필요합니다')
        gr.Markdown('결과는 요청 당시 원문을 기준으로 합니다. 현재 원문이 바뀌었는지 확인하세요. 실행 시간은 관측 이력이 없어 계산 중입니다.')
        with gr.Accordion('번역 이력', open=False):
            translation_history_control = gr.Dataframe(headers=['작업 ID', '상태', '목표 언어'], interactive=False)
            gr.Button('이력 새로고침').click(refresh_translation_history, outputs=translation_history_control)
        translation_submit_control.click(submit_translation_request, [translation_source_control, translation_target_control, translation_glossary_control], [translation_job_control, translation_status_control, translation_result_control, translation_original_control, translation_check_control])
        translation_refresh_control.click(refresh_translation_status, translation_job_control, [translation_status_control, translation_result_control, translation_original_control, translation_check_control])
        translation_cancel_control.click(cancel_translation_request, translation_job_control, translation_status_control)
    return translation_interface_blocks
