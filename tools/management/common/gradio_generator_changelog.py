"""공통 생성기 변경 기록을 Gradio 페이지로 표시한다."""
import gradio as gr

from tools.management.common.generator_changelog import (
    GENERATOR_CHANGELOG_PATHS, read_generator_changelog, paginate_changelog, read_changelog_page,
)


def changelog_page(current_generator_identifier, current_page_index=0):
    page = read_changelog_page(current_generator_identifier, current_page_index)
    index, count = page["index"], page["count"]
    label = f'{page["date"] or "날짜 없음"} · {index + 1} / {count}'
    return page["content"], label, index, gr.update(interactive=index > 0), gr.update(interactive=index < count - 1)


def build_generator_changelog(current_interface_blocks, current_generator_identifier):
    current_initial = changelog_page(current_generator_identifier)
    with gr.Accordion('변경 기록', open=False):
        current_page_label = gr.Markdown(current_initial[1])
        current_page_state = gr.State(0)
        with gr.Row():
            current_previous_button = gr.Button('이전 페이지', interactive=False)
            current_next_button = gr.Button('다음 페이지', interactive=current_initial[4]['interactive'])
            current_refresh_button = gr.Button('변경 기록 새로고침')
        current_changelog_display = gr.Markdown(current_initial[0], sanitize_html=True)
        current_outputs = [current_changelog_display, current_page_label, current_page_state,
                           current_previous_button, current_next_button]
        current_previous_button.click(lambda index: changelog_page(current_generator_identifier, index - 1),
                                      current_page_state, current_outputs, queue=False)
        current_next_button.click(lambda index: changelog_page(current_generator_identifier, index + 1),
                                  current_page_state, current_outputs, queue=False)
        current_refresh_button.click(lambda: changelog_page(current_generator_identifier),
                                     None, current_outputs, queue=False)
        current_interface_blocks.load(lambda: changelog_page(current_generator_identifier),
                                      None, current_outputs, queue=False)
