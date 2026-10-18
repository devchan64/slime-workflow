"""관리 UI 콜백 오류를 추적 ID로 서버 로그와 연결한다."""
import functools
import logging
import uuid
import gradio as gr

MANAGEMENT_ERROR_LOGGER = logging.getLogger('management.ui.error')


def trace_management_callback(current_operation_name):
    def decorate_management_callback(current_callback_function):
        @functools.wraps(current_callback_function)
        def execute_traced_callback(*current_argument_values, **current_keyword_values):
            try:
                return current_callback_function(*current_argument_values, **current_keyword_values)
            except Exception as current_error_value:
                current_trace_identifier = uuid.uuid4().hex[:12]
                MANAGEMENT_ERROR_LOGGER.exception(
                    'area=management-ui stage=callback-error operation=%s trace_id=%s',
                    current_operation_name, current_trace_identifier)
                # 입력 원문·경로·인증정보가 예외 문자열에 포함될 수 있어 상세는 서버 로그에 보존한다.
                raise gr.Error(
                    f'{current_operation_name} 실패 · {type(current_error_value).__name__}\n'
                    f'추적 ID: {current_trace_identifier}\n'
                    '서버 로그 .tmp/manager-current/gradio.log에서 추적 ID를 검색하세요. '
                    '메뉴 분류·검색 조건을 다시 선택해 보세요.',
                    title='관리도구 오류 · 원인 추적', duration=None,
                ) from current_error_value
        return execute_traced_callback
    return decorate_management_callback
