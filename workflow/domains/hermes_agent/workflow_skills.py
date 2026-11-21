"""저장소 스냅샷의 등록부에서 Hermes 워크플로우 스킬을 선택한다."""
import json
from pathlib import Path
import re

SKILL_ROOT = Path('workflow/domains/hermes_agent/skills')
DEFAULT_WORKSPACE = Path(__file__).resolve().parents[3]
NAME_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def _read_file(path, limit=65536):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('스킬 파일을 안전하게 읽을 수 없습니다: ' + str(path))
    return path.read_text(encoding='utf-8')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('스킬 등록부 키 중복: ' + key)
        result[key] = value
    return result


def load_skill_registry(workspace):
    """고정된 스냅샷 등록부만 읽고 ID·키워드·파일 경계를 검증한다."""
    root = Path(workspace) / SKILL_ROOT
    if root.is_symlink() or not root.is_dir():
        raise ValueError('스킬 디렉터리를 확인할 수 없습니다.')
    try:
        record = json.loads(_read_file(root / 'registry.json'), object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError('스킬 등록부 형식 오류') from error
    if not isinstance(record, dict) or set(record) != {'version', 'skills'} or type(record['version']) is not int or record['version'] != 1 or not isinstance(record['skills'], list) or len(record['skills']) > 100:
        raise ValueError('스킬 등록부 계약 오류')
    seen, result = set(), []
    for item in record['skills']:
        if not isinstance(item, dict) or set(item) != {'name', 'terms'}:
            raise ValueError('스킬 등록 항목 오류')
        name, terms = item['name'], item['terms']
        if not isinstance(name, str) or len(name) > 80 or not NAME_PATTERN.fullmatch(name) or name in seen:
            raise ValueError('스킬 이름 오류 또는 중복')
        if not isinstance(terms, list) or not terms or len(terms) > 100 or any(not isinstance(term, str) or not term.strip() or term != term.strip() or len(term) > 80 for term in terms):
            raise ValueError('스킬 선택 키워드 오류')
        if len({term.casefold() for term in terms}) != len(terms):
            raise ValueError('스킬 선택 키워드 중복')
        directory = root / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('등록된 스킬 디렉터리가 없습니다: ' + name)
        text = _read_file(directory / 'SKILL.md')
        if not re.match(r'\A---\s*\nname:\s*' + re.escape(name) + r'\s*\ndescription:\s*\S[^\n]*\n---\s*\n', text):
            raise ValueError('스킬 메타데이터 오류: ' + name)
        seen.add(name)
        result.append((name, tuple(term.casefold() for term in terms)))
    return result


def select_workflow_skills(prompt, context=None, workspace=DEFAULT_WORKSPACE):
    """현재 요청과 최근 사용자 발화로 선택한다. 모델 답변은 분류에 사용하지 않는다."""
    if not isinstance(prompt, str):
        raise ValueError('스킬 선택 요청은 문자열이어야 합니다.')
    messages = context.get('messages', []) if isinstance(context, dict) else []
    previous = [item.get('content', '') for item in messages if isinstance(item, dict) and item.get('role') == 'user' and isinstance(item.get('content'), str)] if isinstance(messages, list) else []
    text = '\n'.join([*previous[-3:], prompt]).casefold()
    def matches(term):
        if term.isascii():
            return re.search(r'(?<![a-z0-9_])' + re.escape(term) + r'(?![a-z0-9_])', text) is not None
        return term in text
    return [name for name, terms in load_skill_registry(workspace) if any(matches(term) for term in terms)]


def build_workflow_guidance(workspace, prompt, context=None):
    root = Path(workspace) / SKILL_ROOT
    selected = select_workflow_skills(prompt, context, workspace)
    guidance = '\n\n[워크플로우 공통 입문]\n' + _read_file(root / 'workflow-introduction.md')
    for name in selected:
        guidance += '\n\n[워크플로우 스킬: ' + name + ']\n' + _read_file(root / name / 'SKILL.md')
    return guidance
