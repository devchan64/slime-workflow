"""건물 구조 가이드를 검색하고 선택하는 카드 갤러리."""
import gradio as gr
from PIL import Image

from tools.review.common.gradio_history_cards import CardGallery, build_card_gallery_pagination
from tools.review.domains.image.building_prompt import (
    BUILDING_LAYOUT_PRESET_NAMES,
    BUILDING_STRUCTURE_RECORDS,
    describe_building_structure_label,
    load_building_layout_preset,
)

BUILDING_GUIDE_PAGE_SIZE = CardGallery.DEFAULT_PAGE_SIZE
BUILDING_GUIDE_PAGE_SIZES = (4, 8, 16, 32)


def search_building_guide_catalog(current_search_text):
    if not isinstance(current_search_text, str):
        raise ValueError('검색어는 문자열이어야 합니다.')
    current_search_terms = current_search_text.casefold().split()
    current_matching_names = []
    for current_preset_name in BUILDING_LAYOUT_PRESET_NAMES:
        current_structure_record = BUILDING_STRUCTURE_RECORDS[current_preset_name]
        current_search_value = ' '.join((current_preset_name, describe_building_structure_label(current_preset_name),
            str(current_structure_record['width'])+'x'+str(current_structure_record['depth']),
            str(current_structure_record['floors'])+'층', current_structure_record['roof'], current_structure_record['entrance'])).casefold()
        if all(current_search_term in current_search_value for current_search_term in current_search_terms):
            current_matching_names.append(current_preset_name)
    return current_matching_names


def render_building_guide_page(current_search_text, current_page_number, current_page_size=BUILDING_GUIDE_PAGE_SIZE):
    current_matching_names = search_building_guide_catalog(current_search_text)
    current_page_size = current_page_size if current_page_size in BUILDING_GUIDE_PAGE_SIZES else BUILDING_GUIDE_PAGE_SIZE
    current_page_count = max(1, (len(current_matching_names) + current_page_size - 1) // current_page_size)
    current_page_number = max(1, min(int(current_page_number or 1), current_page_count))
    current_page_start = (current_page_number - 1) * current_page_size
    current_page_names = current_matching_names[current_page_start:current_page_start + current_page_size]
    current_gallery_values = []
    for current_preset_name in current_page_names:
        current_thumbnail_image = load_building_layout_preset(current_preset_name)
        current_thumbnail_image.thumbnail((320, 320), Image.Resampling.LANCZOS)
        current_gallery_values.append((current_thumbnail_image, f'{describe_building_structure_label(current_preset_name)}\nID: {current_preset_name}'))
    current_status_text = (f'총 {len(current_matching_names)}건 · {current_page_start+1}–{min(current_page_start+current_page_size,len(current_matching_names))}건 표시 · {current_page_number} / {current_page_count}페이지'+(' · 번호 입력 후 Enter' if current_page_count > 1 else '')
                           if current_matching_names else '검색 결과가 없습니다. 검색어를 바꿔주세요.')
    return (current_gallery_values, gr.update(value=current_page_number, maximum=current_page_count, interactive=current_page_count > 1), current_page_names, current_status_text,
            gr.update(interactive=current_page_number > 1),
            gr.update(interactive=current_page_number < current_page_count),
            None, '카드를 선택하면 건물 구조를 확인할 수 있습니다.', gr.update(interactive=False))


def select_building_guide_card(current_search_text, current_page_number, current_page_size, displayed_guide_names, current_selection_event: gr.SelectData):
    current_matching_names = search_building_guide_catalog(current_search_text)
    if current_page_size not in BUILDING_GUIDE_PAGE_SIZES:
        raise gr.Error('페이지 크기가 변경되었습니다. 카드를 다시 선택하세요.')
    current_page_start = (int(current_page_number) - 1) * current_page_size
    current_page_names = current_matching_names[current_page_start:current_page_start + current_page_size]
    if current_page_names != displayed_guide_names:
        raise gr.Error('검색 결과가 변경되었습니다. 카드를 다시 선택하세요.')
    current_selected_index = current_selection_event.index
    if type(current_selected_index) is not int or not 0 <= current_selected_index < len(current_page_names):
        raise gr.Error('건물 가이드 카드를 다시 선택하세요.')
    current_selected_name = current_page_names[current_selected_index]
    current_selected_value = current_selection_event.value
    current_selected_caption = current_selected_value.get('caption') if isinstance(current_selected_value, dict) else None
    if not isinstance(current_selected_caption, str) or f'ID: {current_selected_name}' not in current_selected_caption.splitlines():
        raise gr.Error('검색 결과가 변경되었습니다. 카드를 다시 선택하세요.')
    current_selected_description = f'선택: {describe_building_structure_label(current_selected_name)}\n\nID: {current_selected_name}'
    return current_selected_name, current_selected_description, gr.update(interactive=True)


def apply_selected_building_guide(current_selected_name):
    if not current_selected_name:
        raise gr.Error('건물 가이드 카드를 먼저 선택하세요.')
    return load_building_layout_preset(current_selected_name)


def build_building_guide_gallery():
    initial_page_values = render_building_guide_page('', 1)
    with gr.Group():
        gr.Markdown('### 건물 배치 가이드\n카드를 선택해 구조를 확인하고 적용하면 첫 번째 참조 이미지를 교체합니다.')
        current_search_control = gr.Textbox(label='건물 가이드 검색', placeholder='규격, 층수, 지붕, 입구 또는 ID 검색', lines=1)
        current_page_ids = gr.State(initial_page_values[2])
        current_selected_id = gr.State(None)
        current_gallery_control = CardGallery(value=initial_page_values[0], label='건물 가이드 카드', columns=4, rows=None, height='max-content')
        (_, current_page_size, current_page_notice, current_previous_button, current_page_control,
         current_next_button) = build_card_gallery_pagination(initial_page_values[3], initial_page_count=initial_page_values[1]['maximum'])
        current_description_text = gr.Markdown('카드를 선택하면 건물 구조를 확인할 수 있습니다.')
        current_apply_button = gr.Button('선택한 가이드를 첫 참조에 적용', variant='secondary', interactive=False)
    current_page_outputs = [current_gallery_control, current_page_control, current_page_ids, current_page_notice, current_previous_button, current_next_button,
                            current_selected_id, current_description_text, current_apply_button]
    current_search_control.input(lambda current_search_text, current_size_value: render_building_guide_page(current_search_text, 1, current_size_value), [current_search_control, current_page_size], current_page_outputs, queue=False)
    current_page_size.input(lambda current_search_text, current_size_value: render_building_guide_page(current_search_text, 1, current_size_value), [current_search_control, current_page_size], current_page_outputs, queue=False)
    current_previous_button.click(lambda current_search_text, current_page_number, current_size_value: render_building_guide_page(current_search_text, (current_page_number or 1) - 1, current_size_value), [current_search_control, current_page_control, current_page_size], current_page_outputs, queue=False)
    current_next_button.click(lambda current_search_text, current_page_number, current_size_value: render_building_guide_page(current_search_text, (current_page_number or 1) + 1, current_size_value), [current_search_control, current_page_control, current_page_size], current_page_outputs, queue=False)
    current_page_control.submit(render_building_guide_page, [current_search_control, current_page_control, current_page_size], current_page_outputs, queue=False)
    current_gallery_control.select(select_building_guide_card, [current_search_control, current_page_control, current_page_size, current_page_ids],
                                   [current_selected_id, current_description_text, current_apply_button], queue=False)
    return current_selected_id, current_apply_button
