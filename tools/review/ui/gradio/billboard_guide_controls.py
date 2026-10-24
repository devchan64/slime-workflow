"""빌보드 가이드 선택·문구 합성 공용 Gradio 영역."""
import gradio as gr
from tools.review.domains.image.billboard_guide_prompt import (
    BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT,
    load_billboard_guide_image, compose_billboard_guide_prompt,
)


def preview_billboard_guide_inputs(selected_profile_name, selected_subject_text):
    selected_prompt_text = compose_billboard_guide_prompt(selected_profile_name, selected_subject_text)
    selected_subject_count = len(selected_subject_text.split())
    selected_final_count = len(selected_prompt_text.split())
    return (load_billboard_guide_image(selected_profile_name), selected_prompt_text,
            f'대상 {selected_subject_count}단어 · 가이드 조건 {selected_final_count - selected_subject_count}단어 · 최종 {selected_final_count}단어 / 최대 99단어')


def build_billboard_guide_controls():
    selected_default_profile = BILLBOARD_LAYOUT_PROFILES[0]
    selected_default_values = preview_billboard_guide_inputs(selected_default_profile, BILLBOARD_DEFAULT_SUBJECT)
    with gr.Group():
        gr.Markdown('### 1. 점유 가이드와 대상\n약 80% 채움은 형태 목표입니다. 모서리를 채우지 않고 아래로 갈수록 넓힙니다. 높은형과 중간형은 뒤쪽 벽면·바닥에 밀착하며, 낮은형은 기존 높이의 절반입니다.')
        with gr.Row():
            with gr.Column():
                selected_profile_control = gr.Dropdown(
                    [(current_profile_name.replace('1x3-fallen-log', '1×3 · 낮은 도복목').replace('-tall', ' · 높은형').replace('-medium', ' · 중간 벽면형').replace('-low-2x', ' · 바닥형 높이 2배').replace('-low-4x', ' · 바닥형 높이 4배').replace('-low', ' · 낮은 판형'), current_profile_name) for current_profile_name in BILLBOARD_LAYOUT_PROFILES],
                    value=selected_default_profile, label='점유 열×행 · 형태')
                selected_subject_control = gr.Textbox(value=BILLBOARD_DEFAULT_SUBJECT, label='대상·재질 설명', lines=3)
                gr.Markdown('타일 260×130 기준 · 높은형 520 · 중간 벽면형 260 · 낮은형 90 · 1×1 바닥형 높이 2배 180 / 4배 360. 도복목은 타일 300×150 기준 높이 80~105의 반원통이며 우상단에서 좌하단으로 놓입니다. 그림은 생성 구도 기준이며 게임의 표시 크기를 저장하지 않습니다.')
            selected_guide_preview = gr.Image(value=selected_default_values[0], type='pil', interactive=False, label='가이드 미리보기')
        selected_prompt_preview = gr.Textbox(value=selected_default_values[1], label='합성된 생성 문구', interactive=False, lines=5)
        selected_prompt_count = gr.Markdown(selected_default_values[2])
        selected_apply_button = gr.Button('가이드와 문구를 생성 입력에 적용', variant='primary')
        gr.Markdown('규격 선택은 미리보기만 바꿉니다. 적용 후 생성 입력을 확인하세요. 생성 결과는 검수 전 후보이며 자동 등록하지 않습니다.')
    for selected_input_control in (selected_profile_control, selected_subject_control):
        selected_input_control.change(preview_billboard_guide_inputs, [selected_profile_control, selected_subject_control],
                                      [selected_guide_preview, selected_prompt_preview, selected_prompt_count], queue=False)
    return selected_profile_control, selected_subject_control, selected_apply_button
