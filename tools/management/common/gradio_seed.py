"""생성 화면에서 공용으로 사용하는 무작위 Seed 선택."""
import secrets

RANDOM_SEED_UPPER_BOUND = 4294967296


def generate_random_seed_value():
    """게이트웨이가 허용하는 uint32 정수를 선택한다. 생성을 실행하지 않는다."""
    return secrets.randbelow(RANDOM_SEED_UPPER_BOUND)


def select_generation_seed_value(current_seed_value, random_seed_enabled):
    """자동 선택이면 새 값을 만들고, 수동이면 입력값을 그대로 사용한다."""
    return generate_random_seed_value() if random_seed_enabled else int(current_seed_value)


QWEN_SEED_GUIDANCE = 'Qwen 2.1 편집에서 참조 이미지를 만든 시드와 같은 시드를 재사용하면 이미지 전체에 얼룩이나 거친 선이 생길 수 있습니다. 새 생성마다 무작위 시드를 사용하고, 재현할 때는 자동 선택을 끄고 기록된 시드를 입력하세요. 시드를 바꿔도 품질과 신체 비율은 검수해야 합니다.'


def build_generation_seed(default_seed_value=10107, maximum_seed_value=RANDOM_SEED_UPPER_BOUND-1, random_initial_enabled=False):
    """시드 입력과 랜덤 선택을 함께 제공한다. 실행은 별도 생성 버튼에서 한다."""
    import gradio as gr
    with gr.Column(min_width=220):
        with gr.Row(equal_height=True):
            initial_seed_value = generate_random_seed_value if random_initial_enabled and maximum_seed_value == RANDOM_SEED_UPPER_BOUND-1 else default_seed_value
            generation_seed_control = gr.Number(value=initial_seed_value, precision=0, label='Seed', minimum=0, maximum=maximum_seed_value, scale=3, min_width=110)
            random_seed_button = gr.Button('랜덤 시드', size='lg', scale=1, min_width=140)
        if random_initial_enabled:
            gr.Markdown(f'시드 범위: 0~{maximum_seed_value:,}. 자동 선택이 켜져 있으면 생성 시 새 값을 선택하고 사용값을 표시합니다. 수동 모드에서는 표시된 값을 사용합니다.')
        else:
            gr.Markdown(f'시드 범위: 0~{maximum_seed_value:,}. 시드만 변경하며 생성 시 표시된 값을 사용합니다.')
    def generate_bounded_seed_value():
        return secrets.randbelow(maximum_seed_value + 1)
    random_seed_button.click(generate_random_seed_value if maximum_seed_value == RANDOM_SEED_UPPER_BOUND-1 else generate_bounded_seed_value, outputs=generation_seed_control, queue=False)
    return generation_seed_control
