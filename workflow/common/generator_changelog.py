"""생성기 변경 기록의 고정 경로와 날짜별 페이지."""
from pathlib import Path
import re


WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
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
    'prompt-translation': WORKFLOW_ROOT_DIRECTORY / 'generators/prompt_translation/CHANGELOG.md',
    'writer-agent': WORKFLOW_ROOT_DIRECTORY / 'generators/writer_agent/CHANGELOG.md',
    'hermes-agent': WORKFLOW_ROOT_DIRECTORY / 'generators/hermes_agent/CHANGELOG.md',
    'dwpose-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/dwpose/CHANGELOG.md',
    'wan22-animate2-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_animate2/CHANGELOG.md',
    'wan22-vace-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_vace/CHANGELOG.md',
    'minimax-h3-i2v-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/minimax_h3/CHANGELOG.md',
    'minimax-h3-ref2va-generator': WORKFLOW_ROOT_DIRECTORY / 'workflow/generators/minimax_h3_ref2va/CHANGELOG.md',
    'minimax-h3-image-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/minimax_h3_image/CHANGELOG.md',
    'wan22-i2v-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan_i2v/CHANGELOG.md',
    'wan21-t2v-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan21_t2v/CHANGELOG.md',
    'wan21-i2v-generator': WORKFLOW_ROOT_DIRECTORY / 'generators/wan21_i2v/CHANGELOG.md',
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


def paginate_changelog(current_text):
    """날짜별로 묶되 날짜 미기재 기록과 긴 날짜도 작은 페이지로 표시한다."""
    current_sections = re.split(r'(?m)(?=^## \d{4}-\d{2}-\d{2}(?=\s|$))', current_text)
    current_preamble = current_sections[0].strip()
    current_title_match = re.match(r'^(# [^\n]+)(?:\n|$)', current_preamble)
    current_title = current_title_match.group(1) if current_title_match else ''
    current_undated = current_preamble[len(current_title):].strip()
    current_groups = {}
    for current_section in current_sections[1:]:
        current_date = re.match(r'## (\d{4}-\d{2}-\d{2})', current_section).group(1)
        current_groups.setdefault(current_date, []).append(current_section.strip())
    current_pages = []

    def append_pages(current_date, current_body):
        # 최상위 목록 항목을 분리하고 하위 목록과 설명은 원래 항목에 남긴다.
        current_parts = re.split(r'(?m)(?=^- )', current_body.strip())
        current_prefix = current_parts.pop(0).strip()
        if not current_parts:
            current_parts = [current_prefix] if current_prefix else []
            current_prefix = ''
        for current_offset in range(0, max(1, len(current_parts)), 10):
            current_chunk = current_parts[current_offset:current_offset + 10]
            current_content = '\n\n'.join(filter(None, [current_title, current_prefix, *[part.strip() for part in current_chunk]]))
            current_pages.append((current_date, current_content))

    if current_undated:
        append_pages(None, current_undated)
    for current_date, current_sections_for_date in sorted(current_groups.items(), reverse=True):
        append_pages(current_date, '\n\n'.join(current_sections_for_date))
    return current_pages or [(None, current_text)]


def read_changelog_page(generator, index=0):
    pages = paginate_changelog(read_generator_changelog(generator))
    index = max(0, min(int(index or 0), len(pages) - 1))
    date, content = pages[index]
    return {"date": date, "content": content, "index": index, "count": len(pages)}
