"""표준 Gradio 목록과 페이지 이동으로 제작 예제를 선택한다."""
import gradio as gr

EXAMPLE_PICKER_PAGE_SIZE = 10


def paginate_example_records(current_example_records, current_page_number):
    """범위를 보정하고 현재 페이지의 선택지와 탐색 상태를 반환한다."""
    if not current_example_records:
        raise ValueError('예제 목록이 비어 있습니다.')
    current_page_count = (len(current_example_records) + EXAMPLE_PICKER_PAGE_SIZE - 1) // EXAMPLE_PICKER_PAGE_SIZE
    current_page_number = max(1, min(int(current_page_number), current_page_count))
    current_page_records = current_example_records[(current_page_number - 1) * EXAMPLE_PICKER_PAGE_SIZE:current_page_number * EXAMPLE_PICKER_PAGE_SIZE]
    current_page_choices = [(current_example_record['label'], current_example_record['id']) for current_example_record in current_page_records]
    return (gr.update(choices=current_page_choices, value=current_page_choices[0][1]), current_page_number,
            f'전체 {len(current_example_records)}개 · {current_page_number}/{current_page_count}페이지 · 페이지당 {EXAMPLE_PICKER_PAGE_SIZE}개',
            gr.update(interactive=current_page_number > 1), gr.update(interactive=current_page_number < current_page_count))


def build_paginated_example_picker(current_example_records):
    """페이지 이동은 선택·미리보기만 바꾸며 입력 폼이나 작업을 변경하지 않는다."""
    current_initial_page = paginate_example_records(current_example_records, 1)
    current_page_state = gr.State(1)
    current_example_selector = gr.Radio(choices=current_initial_page[0]['choices'], value=current_initial_page[0]['value'], label='현재 페이지 예제 선택')
    current_page_summary = gr.Markdown(current_initial_page[2])
    with gr.Row():
        current_previous_button = gr.Button('이전 예제 페이지', interactive=False)
        current_next_button = gr.Button('다음 예제 페이지', interactive=current_initial_page[4]['interactive'])
    gr.Markdown('페이지를 이동하면 첫 예제를 미리 봅니다. 첫·마지막 페이지에서는 해당 방향 버튼이 비활성화됩니다. 입력 적용은 아래 불러오기 버튼으로 실행하세요.')
    current_page_outputs = [current_example_selector, current_page_state, current_page_summary, current_previous_button, current_next_button]
    current_previous_button.click(lambda current_page_number: paginate_example_records(current_example_records, current_page_number - 1), current_page_state, current_page_outputs, queue=False)
    current_next_button.click(lambda current_page_number: paginate_example_records(current_example_records, current_page_number + 1), current_page_state, current_page_outputs, queue=False)
    return current_example_selector
