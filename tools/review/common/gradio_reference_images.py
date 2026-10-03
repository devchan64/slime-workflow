"""건물 타일 생성기를 기준으로 한 공용 참조 이미지 입력 UI."""
import gradio as gr

REFERENCE_IMAGE_SLOT_COUNT = 3
REFERENCE_IMAGE_CARD_HEIGHT = 230
REFERENCE_IMAGE_MINIMUM_WIDTH = 180


def build_reference_image_inputs(*, reference_panel_visible=True, reference_panel_identifier=None, reference_image_mode='RGB', reference_slot_count=REFERENCE_IMAGE_SLOT_COUNT):
    if reference_slot_count not in (1, 3):
        raise ValueError('참조 슬롯은 1개 또는 3개만 지원합니다.')
    with gr.Group(visible=reference_panel_visible,elem_id=reference_panel_identifier,elem_classes=['reference-upload-panel']) as reference_upload_group:
        gr.Markdown('### 참조 이미지\n원본 한 장 · 이미지를 끌어놓거나 아래 버튼으로 추가하세요.' if reference_slot_count == 1 else '### 참조 이미지\n최대 3장 · 이미지를 끌어놓거나 아래 버튼으로 추가하세요. 참조 1 → 2 → 3 순서로 전달합니다.')
        with gr.Row(elem_classes=['reference-upload-grid']):
            reference_image_controls=[gr.Image(type='pil',image_mode=reference_image_mode,sources=['upload','clipboard'],label=f'참조 이미지 {reference_slot_index+1}',height=REFERENCE_IMAGE_CARD_HEIGHT,scale=1,min_width=REFERENCE_IMAGE_MINIMUM_WIDTH,elem_classes=['reference-upload-card'],placeholder='이미지 끌어놓기') for reference_slot_index in range(reference_slot_count)]
    return reference_upload_group,reference_image_controls
