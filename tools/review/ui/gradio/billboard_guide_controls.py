"""빌보드 가이드 선택·문구 합성 공용 Gradio 영역."""
import gradio as gr
from tools.review.common.gradio_reference_images import REFERENCE_IMAGE_CARD_HEIGHT
from tools.review.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES, BUILDING_STRUCTURE_RECORDS, describe_building_structure_label, load_building_layout_preset, load_building_base_prompt

BUILDING_PROFILE_PREFIX = 'building:'
BUILDING_HEIGHT_OPTIONS = (('1층 · 80px', 80), ('2층 · 160px', 160), ('3층 · 240px', 240))
BUILDING_EXPANDED_ENTRANCE_PROMPT = 'Door: two tiles wide, 80% of floor height.'
BUILDING_NARROW_ENTRANCE_PROMPT = 'Door: one tile wide, 80% of floor height.'
BUILDING_LAYOUT_ZONE_PROMPT = 'Place optional elements inside the purple footprint zone.'
BUILDING_FLOOR_PROMPTS = {80: 'One floor, as tall as one tile is wide.', 160: 'Two floors, each as tall as one tile is wide.', 240: 'Three floors, each as tall as one tile is wide.'}
from tools.review.domains.image.billboard_guide_prompt import (
    BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT,
    load_billboard_guide_image, compose_billboard_guide_prompt,
)


def parse_building_guide_profile(selected_profile_name):
    current_building_name = selected_profile_name.removeprefix(BUILDING_PROFILE_PREFIX)
    if current_building_name not in BUILDING_STRUCTURE_RECORDS:
        raise ValueError('폐기되었거나 등록되지 않은 건물 가이드입니다.')
    return current_building_name, BUILDING_STRUCTURE_RECORDS[current_building_name]['floors']*80


def compose_building_guide_subject(selected_profile_name, selected_subject_text):
    current_building_name, current_height_pixels = parse_building_guide_profile(selected_profile_name)
    current_subject_text = selected_subject_text.strip()
    current_entrance_prompt = BUILDING_NARROW_ENTRANCE_PROMPT if BUILDING_STRUCTURE_RECORDS[current_building_name]['doorWidth'] == 1 else BUILDING_EXPANDED_ENTRANCE_PROMPT
    current_subject_text += (' ' if current_subject_text.endswith(('.', '!', '?')) else '. ') + current_entrance_prompt + ' ' + BUILDING_FLOOR_PROMPTS[current_height_pixels] + (' ' + BUILDING_LAYOUT_ZONE_PROMPT if '-zone-' in current_building_name else '')
    return current_subject_text


def validate_guide_subject_input(selected_profile_name, selected_subject_text):
    if not isinstance(selected_subject_text, str) or not selected_subject_text.strip():
        raise ValueError('대상과 재질을 입력한 뒤 적용하세요.')
    if selected_profile_name.startswith(BUILDING_PROFILE_PREFIX):
        selected_prompt_text = (compose_building_guide_subject(selected_profile_name, selected_subject_text) + ' ' + load_building_base_prompt()).strip()
        if len(selected_prompt_text.split()) >= 100:
            raise ValueError('최종 문구가 100단어 이상입니다. 대상 설명을 줄이세요.')
        return selected_prompt_text
    return compose_billboard_guide_prompt(selected_profile_name, selected_subject_text)


def preview_billboard_guide_inputs(selected_profile_name, selected_subject_text):
    if selected_profile_name.startswith(BUILDING_PROFILE_PREFIX):
        current_building_name, selected_height_value = parse_building_guide_profile(selected_profile_name)
        selected_guide_image = load_building_layout_preset(current_building_name, selected_height_value)
    else:
        selected_guide_image = load_billboard_guide_image(selected_profile_name)
    try:
        selected_prompt_text = validate_guide_subject_input(selected_profile_name, selected_subject_text)
    except ValueError as current_input_error:
        return selected_guide_image, '', str(current_input_error), gr.update(interactive=False)
    selected_subject_count = len(selected_subject_text.split())
    selected_final_count = len(selected_prompt_text.split())
    return (selected_guide_image, selected_prompt_text,
            f'대상 {selected_subject_count}단어 · 가이드 조건 {selected_final_count - selected_subject_count}단어 · 최종 {selected_final_count}단어 / 최대 99단어', gr.update(interactive=True))


GUIDE_CATEGORY_NAMES = ('전체', '빌보드', '건물')
GUIDE_SEARCH_PAGE_SIZE = 10


def list_guide_profile_choices(selected_category_name):
    if selected_category_name not in GUIDE_CATEGORY_NAMES:
        raise ValueError('지원하지 않는 가이드 분류입니다.')
    current_all_choices = ([(current_profile_name.replace('2x2-lake-boulders', '2×2 · 둥근 호숫돌 군집').replace('4x4-rooted-stump', '4×4 · 중앙 그루터기와 방사형 뿌리').replace('1x1-grass-cover', '1×1 · 낮은 초지 피복').replace('1x1-rooted-grass', '1×1 · 뿌리 분포 풀 군락').replace('2x1-weathered-rock', '2×1 · 자연 풍화 암반').replace('1x3-fallen-log', '1×3 · 낮은 도복목').replace('-tall', ' · 높은형').replace('-medium', ' · 중간 벽면형').replace('-low-2x', ' · 바닥형 높이 2배').replace('-low-4x', ' · 바닥형 높이 4배').replace('-low', ' · 낮은 판형'), current_profile_name) for current_profile_name in BILLBOARD_LAYOUT_PROFILES]
                    + [('건물 · ' + describe_building_structure_label(current_name), BUILDING_PROFILE_PREFIX + current_name) for current_name in BUILDING_LAYOUT_PRESET_NAMES])
    if selected_category_name == '전체':
        return current_all_choices
    current_building_selected = selected_category_name == '건물'
    return [current_choice_value for current_choice_value in current_all_choices if current_choice_value[1].startswith(BUILDING_PROFILE_PREFIX) == current_building_selected]


def search_guide_profile_page(selected_category_name, current_search_text, current_page_number):
    if not isinstance(current_search_text, str):
        raise ValueError('검색어는 문자열이어야 합니다.')
    current_search_terms = current_search_text.casefold().replace('×', 'x').split()
    current_profile_choices = [current_choice_value for current_choice_value in list_guide_profile_choices(selected_category_name)
        if all(current_search_term in (current_choice_value[0] + ' ' + current_choice_value[1]).casefold().replace('×', 'x') for current_search_term in current_search_terms)]
    current_page_count = max(1, (len(current_profile_choices) + GUIDE_SEARCH_PAGE_SIZE - 1) // GUIDE_SEARCH_PAGE_SIZE)
    current_page_number = max(1, min(int(current_page_number or 1), current_page_count))
    current_page_start = (current_page_number - 1) * GUIDE_SEARCH_PAGE_SIZE
    return current_profile_choices[current_page_start:current_page_start + GUIDE_SEARCH_PAGE_SIZE], current_page_number, current_page_count, len(current_profile_choices)


def render_guide_search_page(selected_category_name, current_search_text, current_page_number):
    current_page_choices, current_page_number, current_page_count, current_result_count = search_guide_profile_page(selected_category_name, current_search_text, current_page_number)
    current_gallery_items = []
    for current_profile_label, current_profile_name in current_page_choices:
        if current_profile_name.startswith(BUILDING_PROFILE_PREFIX):
            current_building_name, current_height_value = parse_building_guide_profile(current_profile_name)
            current_guide_image = load_building_layout_preset(current_building_name, current_height_value)
        else:
            current_guide_image = load_billboard_guide_image(current_profile_name)
        current_gallery_items.append((current_guide_image, current_profile_label))
    current_page_notice = f'검색 결과 {current_result_count}개 · {current_page_number} / {current_page_count}페이지' if current_result_count else '검색 결과가 없습니다. 검색어나 분류를 바꿔주세요.'
    return (current_gallery_items, current_page_number, current_page_notice,
            gr.update(visible=current_page_count > 1, interactive=current_page_number > 1),
            gr.update(visible=current_page_count > 1, interactive=current_page_number < current_page_count))


def select_guide_profile_item(selected_category_name, current_search_text, current_page_number, selected_subject_text, current_selection_event: gr.SelectData):
    current_page_choices, _, _, _ = search_guide_profile_page(selected_category_name, current_search_text, current_page_number)
    current_selection_index = current_selection_event.index
    if type(current_selection_index) is not int or not 0 <= current_selection_index < len(current_page_choices):
        raise gr.Error('프리셋 목록이 변경되었습니다. 검색 결과에서 다시 선택하세요.')
    current_profile_label, current_profile_name = current_page_choices[current_selection_index]
    return (current_profile_name, '선택: ' + current_profile_label, *preview_billboard_guide_inputs(current_profile_name, selected_subject_text))


def build_billboard_guide_controls():
    selected_default_profile = BILLBOARD_LAYOUT_PROFILES[0]
    selected_default_values = preview_billboard_guide_inputs(selected_default_profile, BILLBOARD_DEFAULT_SUBJECT)
    with gr.Group():
        gr.Markdown('### 1. 가이드 프리셋과 대상\n프리셋을 선택하면 미리보기만 변경됩니다. 적용 버튼을 눌러 생성 입력에 반영하세요.')
        with gr.Row():
            selected_category_control = gr.Radio(choices=list(GUIDE_CATEGORY_NAMES), value='전체', label='가이드 분류', info='분류를 바꿔도 대상 설명과 적용된 생성 입력은 유지됩니다.')
            selected_search_control = gr.Textbox(label='프리셋 검색', placeholder='예: 3x3 남쪽, 초지, 높음', lines=1, info='이름·크기·입구·높이를 검색하세요.')
        selected_profile_control = gr.State(selected_default_profile)
        selected_profile_notice = gr.Markdown('선택: ' + list_guide_profile_choices('전체')[0][0])
        initial_page_values = render_guide_search_page('전체', '', 1)
        selected_gallery_control = gr.Gallery(value=initial_page_values[0], label='가이드 프리셋', columns=5, rows=2, object_fit='contain', allow_preview=False, interactive=False)
        selected_page_control = gr.State(1)
        selected_page_notice = gr.Markdown(initial_page_values[2])
        with gr.Row():
            selected_previous_button = gr.Button('← 이전', interactive=False)
            selected_next_button = gr.Button('다음 →')
        with gr.Row():
            selected_guide_preview = gr.Image(value=selected_default_values[0], type='pil', interactive=False, label='가이드 미리보기', height=REFERENCE_IMAGE_CARD_HEIGHT)
            with gr.Column():
                selected_subject_control = gr.Textbox(value=BILLBOARD_DEFAULT_SUBJECT, label='대상·재질 설명', placeholder='예: stone house with wooden door', info='만들 대상과 재질을 짧게 입력하세요. 입력 내용은 프리셋을 바꿔도 유지됩니다.', lines=2)
                with gr.Accordion('프리셋 크기와 색상 안내', open=False):
                    gr.Markdown('타일 260×130 기준 · 높은형 520 · 중간 벽면형 260 · 낮은형 90 · 1×1 바닥형 높이 2배 180 / 4배 360. 도복목은 타일 300×150 기준 높이 80–105의 반원통이며 우상단에서 좌하단으로 놓입니다. 뿌리 분포 풀은 1×1·3군집·높이 65–100(상한 110), 자연 풍화 암반은 2×1·높이 90 이하입니다. 초지 피복은 1×1·높이 35–50·뿌리 80% 분포입니다. 4×4 뿌리는 중앙의 낮은 그루터기와 사방으로 뻗는 뿌리 구도이며, 뿌리 끝을 16칸 점유 경계 안에 둡니다. 2×2 호숫돌은 낮고 둥근 바위 세 개와 작은 자갈을 점유 안에 비대칭으로 배치합니다. 건물 구조 50종은 2×2~5×5 점유와 고정 지붕·층수·문 방향을 사용합니다. 80×40 타일에서 층당 높이는 80px, 문 높이는 64px입니다. 문이 있는 변이 2~3칸이면 폭 한 칸, 4~5칸이면 두 칸입니다. 그림은 생성 구도 기준이며 게임의 표시 크기를 저장하지 않습니다.')
        selected_prompt_preview = gr.Textbox(value=selected_default_values[1], label='합성된 생성 문구', interactive=False, lines=5)
        selected_prompt_count = gr.Markdown(selected_default_values[2])
        selected_apply_button = gr.Button('가이드와 문구를 생성 입력에 적용', variant='primary', interactive=True)
        gr.Markdown('규격 선택은 미리보기만 바꿉니다. 적용 후 생성 입력을 확인하세요. 생성 결과는 검수 전 후보이며 자동 등록하지 않습니다.')
    current_pagination_outputs = [selected_gallery_control, selected_page_control, selected_page_notice, selected_previous_button, selected_next_button]
    for current_filter_control in (selected_category_control, selected_search_control):
        current_filter_control.change(lambda current_category_name, current_search_text: render_guide_search_page(current_category_name, current_search_text, 1),
            [selected_category_control, selected_search_control], current_pagination_outputs, queue=False)
    selected_previous_button.click(lambda current_category_name, current_search_text, current_page_number: render_guide_search_page(current_category_name, current_search_text, current_page_number - 1),
        [selected_category_control, selected_search_control, selected_page_control], current_pagination_outputs, queue=False)
    selected_next_button.click(lambda current_category_name, current_search_text, current_page_number: render_guide_search_page(current_category_name, current_search_text, current_page_number + 1),
        [selected_category_control, selected_search_control, selected_page_control], current_pagination_outputs, queue=False)
    selected_gallery_control.select(select_guide_profile_item,
        [selected_category_control, selected_search_control, selected_page_control, selected_subject_control],
        [selected_profile_control, selected_profile_notice, selected_guide_preview, selected_prompt_preview, selected_prompt_count, selected_apply_button], queue=True)
    selected_subject_control.change(preview_billboard_guide_inputs, [selected_profile_control, selected_subject_control],
        [selected_guide_preview, selected_prompt_preview, selected_prompt_count, selected_apply_button], queue=True)
    return selected_profile_control, selected_subject_control, selected_apply_button
