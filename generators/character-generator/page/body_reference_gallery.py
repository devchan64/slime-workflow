"""신체 비율 기준 검색과 공용 카드 선택 화면."""
import importlib

import gradio as gr
from PIL import Image

from tools.review.common.gradio_history_cards import CardGallery
from tools.review.common.gradio_reference_images import REFERENCE_IMAGE_CARD_HEIGHT

BODY_REFERENCE_PAGE_SIZE = 8
BODY_REFERENCE_MODULE = importlib.import_module('generators.character-generator.body_references')


def search_body_reference_catalog(current_search_text):
    if not isinstance(current_search_text, str):
        raise ValueError('검색어는 문자열이어야 합니다.')
    current_search_terms = current_search_text.casefold().split()
    current_reference_records = BODY_REFERENCE_MODULE.load_body_reference_catalog()
    return [current_record for current_record in current_reference_records
            if all(current_term in ' '.join(current_record[current_field] for current_field in ('id', 'label', 'version', 'source', 'role')).casefold() for current_term in current_search_terms)]


def render_body_reference_page(current_search_text, current_page_number):
    current_matching_records = search_body_reference_catalog(current_search_text)
    current_page_count = max(1, (len(current_matching_records) + BODY_REFERENCE_PAGE_SIZE - 1) // BODY_REFERENCE_PAGE_SIZE)
    current_page_number = max(1, min(int(current_page_number or 1), current_page_count))
    current_page_start = (current_page_number - 1) * BODY_REFERENCE_PAGE_SIZE
    current_page_records = current_matching_records[current_page_start:current_page_start + BODY_REFERENCE_PAGE_SIZE]
    current_gallery_values = []
    for current_record in current_page_records:
        current_thumbnail_image = BODY_REFERENCE_MODULE.load_body_reference_image(current_record['id'])
        current_thumbnail_image.thumbnail((320, 320), Image.Resampling.LANCZOS)
        current_gallery_values.append((current_thumbnail_image, f"{current_record['label']}\nID: {current_record['id']}\n버전: {current_record['version']}\n{current_record['role']}"))
    current_status_text = f'검색 결과 {len(current_matching_records)}개 · {current_page_number} / {current_page_count}페이지' if current_matching_records else '검색 결과가 없습니다. 검색어를 바꿔주세요.'
    return (current_gallery_values, current_page_number, [current_record['id'] for current_record in current_page_records], current_status_text,
            gr.update(visible=current_page_count > 1, interactive=current_page_number > 1),
            gr.update(visible=current_page_count > 1, interactive=current_page_number < current_page_count),
            None, None, '카드를 선택하면 원본과 용도를 확인할 수 있습니다.', gr.update(interactive=False))


def select_body_reference_card(current_search_text, current_page_number, displayed_reference_ids, current_selection_event: gr.SelectData):
    current_matching_records = search_body_reference_catalog(current_search_text)
    current_page_start = (int(current_page_number) - 1) * BODY_REFERENCE_PAGE_SIZE
    current_page_records = current_matching_records[current_page_start:current_page_start + BODY_REFERENCE_PAGE_SIZE]
    if [current_record['id'] for current_record in current_page_records] != displayed_reference_ids:
        raise gr.Error('검색 결과가 변경되었습니다. 카드를 다시 선택하세요.')
    current_selected_index = current_selection_event.index
    if type(current_selected_index) is not int or not 0 <= current_selected_index < len(current_page_records):
        raise gr.Error('신체 비율 참조 카드를 다시 선택하세요.')
    current_selected_record = current_page_records[current_selected_index]
    current_description = f"선택: {current_selected_record['label']}\n\n{current_selected_record['role']}\n\n버전 {current_selected_record['version']} · SHA-256 {current_selected_record['sha256']}"
    return current_selected_record['id'], BODY_REFERENCE_MODULE.load_body_reference_image(current_selected_record['id']), current_description, gr.update(interactive=True)


def build_body_reference_gallery():
    initial_page_values = render_body_reference_page('', 1)
    with gr.Group():
        gr.Markdown('### 신체 비율 참조 기준\n카드 선택은 미리보기만 바꿉니다. 적용하면 첫 번째 참조를 교체합니다. 2×2 이미지는 신체 비율만 참고하며 재질·눈색·기본복은 복제하지 않습니다.')
        current_search_control = gr.Textbox(label='신체 비율 참조 검색', placeholder='이름, 용도, 출처 또는 ID 검색', lines=1)
        current_page_control = gr.State(1)
        current_page_ids = gr.State(initial_page_values[2])
        current_selected_id = gr.State(None)
        current_gallery_control = CardGallery(value=initial_page_values[0], label='신체 비율 참조 카드', columns=4, rows=2)
        current_page_notice = gr.Markdown(initial_page_values[3])
        with gr.Row():
            current_previous_button = gr.Button('← 이전', visible=False, interactive=False)
            current_next_button = gr.Button('다음 →', visible=False, interactive=False)
        with gr.Row():
            current_preview_image = gr.Image(type='pil', format='png', interactive=False, label='신체 비율 기준 미리보기', height=REFERENCE_IMAGE_CARD_HEIGHT)
            with gr.Column():
                current_description_text = gr.Markdown('카드를 선택하면 원본과 용도를 확인할 수 있습니다.')
                current_apply_button = gr.Button('선택 기준을 첫 참조에 적용', variant='secondary', interactive=False)
    current_page_outputs = [current_gallery_control, current_page_control, current_page_ids, current_page_notice, current_previous_button, current_next_button,
                            current_selected_id, current_preview_image, current_description_text, current_apply_button]
    current_search_control.input(lambda current_search_text: render_body_reference_page(current_search_text, 1), current_search_control, current_page_outputs, queue=False)
    current_previous_button.click(lambda current_search_text, current_page_number: render_body_reference_page(current_search_text, current_page_number - 1), [current_search_control, current_page_control], current_page_outputs, queue=False)
    current_next_button.click(lambda current_search_text, current_page_number: render_body_reference_page(current_search_text, current_page_number + 1), [current_search_control, current_page_control], current_page_outputs, queue=False)
    current_gallery_control.select(select_body_reference_card, [current_search_control, current_page_control, current_page_ids],
                                   [current_selected_id, current_preview_image, current_description_text, current_apply_button], queue=False)
    return current_selected_id, current_apply_button
