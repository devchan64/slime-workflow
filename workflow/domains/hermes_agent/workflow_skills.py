"""작업 스냅샷의 워크플로우 지침을 요청 주제에 맞게 선택한다."""
from pathlib import Path
import re

SKILL_ROOT = Path('workflow/domains/hermes_agent/skills')
# 고정 목록만 읽는다. 사용자 입력은 경로나 파일 이름으로 사용하지 않는다.
SKILL_TERMS = {
    'generation-result-lookup': ('결과', '상태', '완료', '재생', '다운로드', 'result', 'status', 'output', 'preview'),
    'generation-request': ('생성', '만들', '제작', '그려', '이미지', '영상', '모션', '음악', '효과음', '번역', 'generate', 'create', 'image', 'video', 'audio', 'flux', 'kimodo', 'wan', 'qwen'),
    'history-operations': ('이력', '기록', '재개', '중단', '취소', '삭제', '초기화', '작업', '상태', 'history', 'resume', 'status', 'job', 'queue'),
    'generator-development': ('코드', '구현', '수정', '개발', '버그', '테스트', '생성기', 'gateway', 'gui', 'cli', 'code', 'implement', 'debug', 'test', 'generator'),
    'map-asset-review': ('맵', '지도', '에셋', '건물', '빌보드', '스프라이트', '이펙트', '앵커', '좌표', 'map', 'asset', 'building', 'billboard', 'sprite', 'effect', 'anchor'),
}


def select_workflow_skills(prompt, context=None):
    """현재 요청과 최근 사용자 발화로 선택한다. 모델 답변은 분류에 사용하지 않는다."""
    messages = context.get('messages', []) if isinstance(context, dict) else []
    previous = [item.get('content', '') for item in messages if isinstance(item, dict) and item.get('role') == 'user' and isinstance(item.get('content'), str)] if isinstance(messages, list) else []
    text = '\n'.join([*previous[-3:], prompt]).casefold()
    def matches(term):
        if term.isascii():
            return re.search(r'(?<![a-z0-9_])' + re.escape(term) + r'(?![a-z0-9_])', text) is not None
        return term in text
    return [name for name, terms in SKILL_TERMS.items() if any(matches(term) for term in terms)]


def build_workflow_guidance(workspace, prompt, context=None):
    root = Path(workspace) / SKILL_ROOT
    guidance = '\n\n[워크플로우 공통 입문]\n' + (root / 'workflow-introduction.md').read_text(encoding='utf-8')
    for name in select_workflow_skills(prompt, context):
        guidance += '\n\n[워크플로우 스킬: ' + name + ']\n' + (root / name / 'SKILL.md').read_text(encoding='utf-8')
    return guidance
