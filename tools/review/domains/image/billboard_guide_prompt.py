"""빌보드 점유 가이드와 생성 문구의 공용 원본."""
from pathlib import Path
from PIL import Image

BILLBOARD_CONFIG_DIRECTORY = Path(__file__).resolve().parents[4] / 'generators/image/config'
BILLBOARD_LAYOUT_PROFILES = ('3x1-tall', '2x1-tall', '1x2-tall', '1x3-tall', '3x1-medium', '2x1-medium', '1x2-medium', '1x3-medium', '1x1-low', '1x1-low-2x', '1x1-low-4x', '2x1-low', '3x1-low', '2x2-low', '2x3-low', '3x2-low', '1x3-fallen-log')
BILLBOARD_DEFAULT_SUBJECT = 'charcoal rock with prominent milky white quartz veins'


def load_billboard_guide_image(selected_profile_name):
    if selected_profile_name not in BILLBOARD_LAYOUT_PROFILES:
        raise ValueError('등록된 빌보드 규격 중 하나를 선택하세요.')
    selected_image_path = BILLBOARD_CONFIG_DIRECTORY / 'billboard-layouts' / f'billboard-guide-{selected_profile_name}.png'
    with Image.open(selected_image_path) as selected_image_data:
        return selected_image_data.copy()


def compose_billboard_guide_prompt(selected_profile_name, selected_subject_text):
    if selected_profile_name not in BILLBOARD_LAYOUT_PROFILES:
        raise ValueError('등록되지 않은 빌보드 규격입니다.')
    if not isinstance(selected_subject_text, str) or not selected_subject_text.strip():
        raise ValueError('생성할 대상과 재질을 입력하세요.')
    selected_height_value = {'1x1-low-2x': 180, '1x1-low-4x': 360}.get(selected_profile_name, 90)
    selected_contact_text = ('Tall formation, rear flush against an imaginary wall; uneven receding front and summit.'
                             if selected_profile_name.endswith('tall') else
                             (f'Formation height {selected_height_value} relative to tile width 260; uneven top, broad grounded base.'
                              if selected_profile_name in ('1x1-low-2x', '1x1-low-4x') else
                              'Very low formation, height 90 relative to tile width 260; shallow uneven top.'))
    selected_template_text = (BILLBOARD_CONFIG_DIRECTORY / 'billboard-guide-prompt.txt').read_text(encoding='utf-8').strip()
    if selected_profile_name.endswith('medium'):
        selected_contact_text = 'Medium formation, height 260 relative to tile width 260; rear flush against an imaginary wall; uneven top, broad grounded base.'
    if selected_profile_name == '1x3-fallen-log':
        selected_contact_text = 'Low half-cylinder, height 80–105 relative to tile width 300; long axis upper-right to lower-left, resting flat on ground.'
    selected_prompt_text = selected_template_text.format(subject=selected_subject_text.strip(), contact=selected_contact_text)
    if len(selected_prompt_text.split()) >= 100:
        raise ValueError('최종 문구는 99단어 이하여야 합니다. 대상 설명을 줄이세요.')
    return selected_prompt_text
