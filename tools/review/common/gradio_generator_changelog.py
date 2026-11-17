"""생성기 변경 기록의 고정 경로와 Gradio 표시."""
from pathlib import Path

import gradio as gr

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
GENERATOR_CHANGELOG_PATHS = {
    'flux-expression-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/flux-expression/CHANGELOG.md',
    'mannequin-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/mannequin-generator/CHANGELOG.md',
    'character-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/character-generator/CHANGELOG.md',
    'qwen-21': WORKFLOW_ROOT_DIRECTORY / 'generators/qwen-21/CHANGELOG.md',
    'qwen-21-circular': WORKFLOW_ROOT_DIRECTORY / 'generators/qwen-21-circular/CHANGELOG.md',
    'expression': WORKFLOW_ROOT_DIRECTORY / 'generators/expression/CHANGELOG.md',
    'vegetation-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/vegetation-generator/CHANGELOG.md',
    'prop-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/prop-generator/CHANGELOG.md',
    'billboard-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/billboard-generator/CHANGELOG.md',
    'music-heartmula': WORKFLOW_ROOT_DIRECTORY / 'generators/music-heartmula/CHANGELOG.md',
    'sfx-dasheng-audiogen': WORKFLOW_ROOT_DIRECTORY / 'generators/sfx-dasheng-audiogen/CHANGELOG.md',
    'writer-agent': WORKFLOW_ROOT_DIRECTORY / 'generators/writer_agent/CHANGELOG.md',
    'hermes-agent': WORKFLOW_ROOT_DIRECTORY / 'generators/hermes_agent/CHANGELOG.md',
    'dwpose-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/dwpose/CHANGELOG.md',
    'wan22-animate2-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_animate2/CHANGELOG.md',
    'wan22-vace-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_vace/CHANGELOG.md',
    'wan22-fun-control-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_fun/CHANGELOG.md',
    'kimodo-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/kimodo/CHANGELOG.md',
}
for current_flux_profile in ('flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless'):
    GENERATOR_CHANGELOG_PATHS[current_flux_profile+'-generator'] = WORKFLOW_ROOT_DIRECTORY/'generators'/current_flux_profile/'CHANGELOG.md'


def read_generator_changelog(current_generator_identifier):
    current_changelog_path = GENERATOR_CHANGELOG_PATHS.get(current_generator_identifier)
    if current_changelog_path is None:
        raise ValueError('등록되지 않은 생성기입니다.')
    try:
        return current_changelog_path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return '변경 기록을 읽을 수 없습니다. 생성기의 CHANGELOG.md 파일과 읽기 권한을 확인하세요.'


def build_generator_changelog(current_interface_blocks, current_generator_identifier):
    with gr.Accordion('변경 기록', open=False):
        current_changelog_display = gr.Markdown(
            read_generator_changelog(current_generator_identifier), sanitize_html=True
        )
        current_refresh_button = gr.Button('변경 기록 새로고침')
        current_refresh_button.click(
            lambda: read_generator_changelog(current_generator_identifier),
            inputs=None, outputs=current_changelog_display, queue=False,
        )
        current_interface_blocks.load(
            lambda: read_generator_changelog(current_generator_identifier),
            inputs=None, outputs=current_changelog_display, queue=False,
        )
