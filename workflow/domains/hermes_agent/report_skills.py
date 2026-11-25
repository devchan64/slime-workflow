"""자동 보고서의 원 서비스 ID로 검수 지침을 선택한다."""
from pathlib import Path
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS

REPORT_SERVICES = frozenset((*FLUX_IMAGE_PROFILE_RECORDS, 'flux-expression', 'minimax-h3-image', 'minimax-h3-i2v'))


def report_instructions(service):
    if service not in REPORT_SERVICES:
        raise ValueError('보고서 스킬이 등록되지 않은 생성기입니다.')
    path = Path(__file__).with_name('skills') / ('report-' + service) / 'SKILL.md'
    _, separator, body = path.read_text(encoding='utf-8').partition('\n---\n')
    if not separator or not body.strip():
        raise ValueError(f'{service} 보고서 스킬 본문이 없습니다.')
    return ' '.join(body.split())
