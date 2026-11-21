"""기본 Gradio 버튼과 가까운 안내를 접근성 설명으로 연결한다."""
import json
import uuid

import gradio as gr

BUTTON_GUIDANCE_LINK_SCRIPT = """
const linkButtonGuidance = () => {
    const currentGuidanceRecord = JSON.parse(props.value);
    const currentButtonElement = element.querySelector('[id="' + currentGuidanceRecord.button + '"]');
    const currentGuidanceElement = element.querySelector('[id="' + currentGuidanceRecord.guidance + '"]');
    if (!currentButtonElement || !currentGuidanceElement) return;
    const currentDescriptionTokens = new Set((currentButtonElement.getAttribute('aria-describedby') || '').split(/\\s+/).filter(Boolean));
    currentDescriptionTokens.add(currentGuidanceRecord.guidance);
    const currentDescriptionValue = [...currentDescriptionTokens].join(' ');
    if (currentButtonElement.getAttribute('aria-describedby') !== currentDescriptionValue) {
        currentButtonElement.setAttribute('aria-describedby', currentDescriptionValue);
    }
};
const currentGuidanceObserver = new MutationObserver(linkButtonGuidance);
currentGuidanceObserver.observe(element, {childList: true, subtree: true, attributes: true, attributeFilter: ['aria-describedby']});
linkButtonGuidance();
"""


def build_button_guidance(current_button_control, current_guidance_text):
    """안내는 Markdown으로 표시하고 기본 버튼의 설명 속성만 보완한다."""
    current_guidance_identifier = 'button-guidance-' + uuid.uuid4().hex
    if not current_button_control.elem_id:
        current_button_control.elem_id = 'guided-button-' + uuid.uuid4().hex
    current_button_control.unrender()
    with gr.HTML(value=json.dumps({'button': current_button_control.elem_id, 'guidance': current_guidance_identifier}),
                 html_template='@children', container=False, js_on_load=BUTTON_GUIDANCE_LINK_SCRIPT):
        current_button_control.render()
        current_guidance_control = gr.Markdown(current_guidance_text, elem_id=current_guidance_identifier)
    return current_guidance_control
