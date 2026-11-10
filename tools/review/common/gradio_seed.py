"""생성 화면에서 공용으로 사용하는 무작위 Seed 선택."""
import secrets

RANDOM_SEED_UPPER_BOUND = 4294967296


def generate_random_seed_value():
    """게이트웨이가 허용하는 uint32 정수를 선택한다. 생성을 실행하지 않는다."""
    return secrets.randbelow(RANDOM_SEED_UPPER_BOUND)


def build_generation_seed(default_seed_value=10107, maximum_seed_value=RANDOM_SEED_UPPER_BOUND-1):
    """시드 입력과 랜덤 선택을 함께 제공한다. 실행은 별도 생성 버튼에서 한다."""
    import gradio as gr
    with gr.Column(min_width=220):
        with gr.Row(equal_height=True):
            generation_seed_control = gr.Number(value=default_seed_value, precision=0, label='Seed', minimum=0, maximum=maximum_seed_value, scale=3, min_width=110)
            random_seed_button = gr.Button('랜덤 시드', size='lg', scale=1, min_width=140)
        gr.Markdown(f'시드 범위: 0~{maximum_seed_value:,}. 시드만 변경하며 생성 시 표시된 값을 사용합니다.')
    def generate_bounded_seed_value():
        return secrets.randbelow(maximum_seed_value + 1)
    random_seed_button.click(generate_random_seed_value if maximum_seed_value == RANDOM_SEED_UPPER_BOUND-1 else generate_bounded_seed_value, outputs=generation_seed_control, queue=False)
    return generation_seed_control
