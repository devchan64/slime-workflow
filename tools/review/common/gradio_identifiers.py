"""관리도구의 복사 가능한 한 줄 생성 ID 표시."""
from tools.review.common.gradio_logs import create_copyable_log_textbox


def build_generation_identifier(label_text_value='생성 ID', element_identifier_value=None):
    return create_copyable_log_textbox(
        label=label_text_value, interactive=False, lines=1, max_lines=1,
        elem_id=element_identifier_value, elem_classes=['management-generation-identifier'],
    )
