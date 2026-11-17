"""공용 게이트웨이를 사용하는 격리 Hermes 코딩 작업 화면."""
import uuid

import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from tools.review.common.management_client import execute_remote_management_command


def submit_hermes_work_request(hermes_prompt_text, hermes_request_identifier, hermes_verification_text=''):
    try:
        hermes_request_record = {'prompt':hermes_prompt_text, 'request_id':hermes_request_identifier}
        hermes_verification_modules = [hermes_module_name.strip() for hermes_module_name in (hermes_verification_text or '').splitlines() if hermes_module_name.strip()]
        if hermes_verification_modules:
            hermes_request_record['verification_modules'] = hermes_verification_modules
        hermes_response_record = execute_remote_management_command('hermes-agent', 'hermes-submit', hermes_request_record)
        return hermes_response_record['id'], '기존 접수 확인' if hermes_response_record.get('duplicate') else 'GPU 대기열에 등록했습니다.'
    except Exception as hermes_request_error:
        raise gr.Error('접수 확인 실패: ' + str(hermes_request_error) + ' · 같은 접수 식별자로 다시 확인하세요.') from hermes_request_error


def refresh_hermes_work_status(hermes_job_identifier):
    try:
        hermes_job_record = execute_remote_management_command('hermes-agent', 'hermes-detail', {'id':hermes_job_identifier})
        hermes_status_record = hermes_job_record['status']
        hermes_status_text = hermes_status_record.get('status', 'unknown')
        if hermes_status_record.get('queue_position'):
            hermes_status_text += ' · 대기 순서 ' + str(hermes_status_record['queue_position'])
        if hermes_status_record.get('error'):
            hermes_status_text += ' · ' + str(hermes_status_record['error'])
        if hermes_status_record.get('message'):
            hermes_status_text += ' · ' + str(hermes_status_record['message'])
        if hermes_job_record['diff_truncated']:
            hermes_status_text += ' · diff 일부만 표시'
        return hermes_status_text, hermes_job_record['diff'], hermes_job_record['log'], hermes_job_record.get('result')
    except Exception as hermes_request_error:
        raise gr.Error('조회 실패: ' + str(hermes_request_error)) from hermes_request_error


def cancel_hermes_work_request(hermes_job_identifier):
    try:
        execute_remote_management_command('hermes-agent', 'hermes-cancel', {'id':hermes_job_identifier})
        return '중지를 요청했습니다. 실제 종료 여부는 상태를 새로고침해 확인하세요.'
    except Exception as hermes_request_error:
        raise gr.Error('중지 실패: ' + str(hermes_request_error)) from hermes_request_error


def refresh_hermes_work_history():
    try:
        hermes_history_record = execute_remote_management_command('hermes-agent', 'hermes-history', {})
        hermes_history_rows = [[hermes_job_record['id'], hermes_job_record['status'].get('status', 'unknown'), hermes_job_record['request']['prompt'][:120]] for hermes_job_record in hermes_history_record['records']]
        return hermes_history_rows, f'작업 이력 {len(hermes_history_rows)}개'
    except Exception as hermes_request_error:
        return [], '이력 조회 실패: ' + str(hermes_request_error) + ' · 관리 게이트웨이 실행 상태와 버전을 확인하세요.'


def build_hermes_agent_interface():
    with gr.Blocks(title='Hermes 코딩 에이전트') as hermes_interface_blocks:
        build_generator_changelog(hermes_interface_blocks, 'hermes-agent')
        gr.Markdown('## Hermes 코딩 에이전트\n현재 관리도구 파일의 격리 사본에서만 작업하며 결과는 검토용 diff로 제공합니다. 네트워크는 차단되고 GPU는 공용 대기열에서 배타적으로 사용합니다. 실행 시간은 관측 이력이 부족해 계산 중입니다. 모델 준비는 [모델 관리](/management/frame/model-management/)에서 확인하세요.')
        hermes_prompt_control = gr.Textbox(label='작업 지시', lines=6, max_lines=20)
        hermes_verification_control = gr.Textbox(label='완료 후 검증 모듈 · 선택', lines=2, placeholder='tools.review.tests.test_hermes_service', info='공용 회귀 실행기에 등록된 모듈을 한 줄에 하나씩 최대 5개 입력합니다. Hermes 종료 후 격리 환경에서 별도로 검사합니다.')
        hermes_prompt_count = gr.Markdown('원문 0단어 · 최종 입력 0단어')
        hermes_prompt_control.change(lambda hermes_text_value: f'원문 {len((hermes_text_value or "").split())}단어 · 최종 입력 {len((hermes_text_value or "").split())}단어', hermes_prompt_control, hermes_prompt_count, queue=False)
        hermes_request_control = gr.Textbox(label='접수 식별자', value=lambda: uuid.uuid4().hex, interactive=False, info='요청 실패나 응답 유실 시 같은 식별자로 다시 접수하면 중복 실행하지 않습니다.')
        with gr.Row():
            hermes_submit_control = gr.Button('작업 대기열에 추가', variant='primary', interactive=False)
            hermes_new_request_button = gr.Button('새 접수 식별자')
        hermes_job_control = gr.Textbox(label='작업 ID', interactive=True)
        hermes_status_control = gr.Markdown('작업 지시를 입력하세요.')
        hermes_new_request_button.click(lambda: (uuid.uuid4().hex, '', '새 접수 식별자를 만들었습니다.'), outputs=[hermes_request_control, hermes_job_control, hermes_status_control], queue=False)
        bind_gpu_generation_confirmation(hermes_submit_control, submit_hermes_work_request, [hermes_prompt_control, hermes_request_control, hermes_verification_control], [hermes_job_control, hermes_status_control], generation_readiness_callback=lambda hermes_prompt_value: bool((hermes_prompt_value or '').strip()), generation_readiness_inputs=[hermes_prompt_control])
        with gr.Row():
            hermes_refresh_button = gr.Button('상태·결과 새로고침')
            hermes_cancel_button = gr.Button('작업 중지 요청')
        hermes_diff_control = gr.Code(label='검토용 변경 diff', language=None, interactive=False, buttons=['copy', 'download'])
        hermes_result_control = gr.JSON(label='실행 결과')
        hermes_log_control = gr.Textbox(label='작업 로그', lines=8, interactive=False)
        hermes_refresh_button.click(refresh_hermes_work_status, hermes_job_control, [hermes_status_control, hermes_diff_control, hermes_log_control, hermes_result_control], queue=False)
        hermes_cancel_button.click(cancel_hermes_work_request, hermes_job_control, hermes_status_control, queue=False)
        with gr.Accordion('작업 이력', open=True):
            hermes_history_button = gr.Button('이력 새로고침')
            hermes_history_status = gr.Markdown('이력을 확인하고 있습니다.')
            hermes_history_table = gr.Dataframe(headers=['작업 ID', '상태', '지시'], datatype=['str', 'str', 'str'], interactive=False)
            hermes_history_button.click(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
        hermes_interface_blocks.load(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
    return hermes_interface_blocks
