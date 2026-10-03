"""건물 타일 생성기를 기준으로 한 공용 참조 이미지 입력 UI."""
import gradio as gr
from pathlib import Path

REFERENCE_CLIPBOARD_SCRIPT = (Path(__file__).parents[1] / "ui/shared/reference-clipboard.js").read_text()

REFERENCE_IMAGE_SLOT_COUNT = 3
REFERENCE_IMAGE_CARD_HEIGHT = 230
REFERENCE_IMAGE_MINIMUM_WIDTH = 180


def build_reference_image_inputs(*, reference_panel_visible=True, reference_panel_identifier=None, reference_image_mode='RGB', reference_slot_count=REFERENCE_IMAGE_SLOT_COUNT):
    if reference_slot_count not in (1, 3, 10):
        raise ValueError('참조 슬롯은 1개·3개·10개를 지원합니다.')
    dynamic_slots_enabled = reference_slot_count == 10
    with gr.Group(visible=reference_panel_visible,elem_id=reference_panel_identifier,elem_classes=['reference-upload-panel']) as reference_upload_group:
        gr.Markdown('### 참조 이미지\n원본 한 장 · 이미지를 끌어놓거나 아래 버튼으로 추가하세요.' if reference_slot_count == 1 else f'### 참조 이미지\n최대 {reference_slot_count}장 · 이미지를 끌어놓거나 아래 버튼으로 추가하세요. 입력된 참조를 번호 순서대로 전달합니다.')
        visible_slot_state = gr.State(1) if dynamic_slots_enabled else None
        reference_slot_groups = []
        reference_delete_buttons = []
        with gr.Row(elem_classes=['reference-upload-grid']):
            reference_image_controls = []
            for reference_slot_index in range(reference_slot_count):
                with gr.Column(min_width=REFERENCE_IMAGE_MINIMUM_WIDTH, visible=not dynamic_slots_enabled or reference_slot_index == 0, elem_classes=['reference-upload-slot']) as reference_slot_group:
                    reference_slot_groups.append(reference_slot_group)
                    reference_image_controls.append(gr.Image(type='pil', image_mode=reference_image_mode, sources=['upload'], label=f'참조 이미지 {reference_slot_index+1}', height=REFERENCE_IMAGE_CARD_HEIGHT, elem_classes=['reference-upload-card'], placeholder='이미지 끌어놓기'))
                    gr.HTML('<div class="reference-upload-actions"><button type="button" class="sm secondary" data-reference-action="upload">파일 불러오기</button><button type="button" class="sm secondary" data-reference-action="clipboard">클립보드 붙여넣기</button></div><p role="status" aria-live="polite"></p>', js_on_load=REFERENCE_CLIPBOARD_SCRIPT)
                    if dynamic_slots_enabled:
                        reference_delete_buttons.append(gr.Button('삭제', size='sm', variant='secondary'))

        if dynamic_slots_enabled:
            with gr.Row():
                reference_add_button = gr.Button('이미지 추가', size='sm', variant='secondary')
                reference_slot_status = gr.Markdown(f'1 / {reference_slot_count}칸 · 빈 칸은 모델에 전달하지 않습니다.')

            def update_visible_slots(visible_slot_count, *reference_image_values):
                populated_slot_count = max((slot_index + 1 for slot_index, image_value in enumerate(reference_image_values) if image_value is not None), default=1)
                return max(int(visible_slot_count), populated_slot_count)

            def describe_reference_slots(visible_slot_count):
                return f'{visible_slot_count} / {reference_slot_count}칸 · ' + ('최대 개수입니다. 삭제 후 새 이미지를 추가할 수 있습니다.' if visible_slot_count == reference_slot_count else '빈 칸은 모델에 전달하지 않습니다.')

            def build_slot_updates(visible_slot_count):
                return (visible_slot_count, *[gr.update(visible=slot_index < visible_slot_count) for slot_index in range(reference_slot_count)],
                        gr.update(interactive=visible_slot_count < reference_slot_count), describe_reference_slots(visible_slot_count))

            def add_reference_slot(visible_slot_count, *reference_image_values):
                visible_slot_count = update_visible_slots(visible_slot_count, *reference_image_values)
                return build_slot_updates(min(reference_slot_count, visible_slot_count + 1))

            def reveal_loaded_slots(visible_slot_count, *reference_image_values):
                return build_slot_updates(update_visible_slots(visible_slot_count, *reference_image_values))

            def create_delete_callback(selected_slot_index):
                def delete_reference_slot(visible_slot_count, *reference_image_values):
                    visible_slot_count = update_visible_slots(visible_slot_count, *reference_image_values)
                    remaining_image_values = list(reference_image_values)
                    remaining_image_values.pop(selected_slot_index)
                    remaining_image_values.append(None)
                    return (*build_slot_updates(max(1, visible_slot_count - 1)), *remaining_image_values)
                return delete_reference_slot

            slot_update_outputs = [visible_slot_state, *reference_slot_groups, reference_add_button, reference_slot_status]
            reference_upload_group.reference_slot_outputs = slot_update_outputs
            reference_upload_group.build_reference_updates = build_slot_updates
            slot_update_inputs = [visible_slot_state, *reference_image_controls]
            reference_add_button.click(add_reference_slot, slot_update_inputs, slot_update_outputs, queue=False)
            for reference_slot_index, reference_delete_button in enumerate(reference_delete_buttons):
                reference_delete_button.click(create_delete_callback(reference_slot_index), slot_update_inputs,
                                              [*slot_update_outputs, *reference_image_controls], queue=False)
            for reference_image_control in reference_image_controls:
                reference_image_control.change(reveal_loaded_slots, slot_update_inputs, slot_update_outputs, queue=False)

    return reference_upload_group,reference_image_controls
