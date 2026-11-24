"""접수 시 정책에 따라 영상 제안의 생성기를 확정한다."""
import re

_ALIASES = {
    'minimax-h3-i2v': ('minimax-h3-i2v', 'minimax i2v', '미니맥스 i2v'),
    'minimax-h3-ref2va': ('minimax-h3-ref2va', 'ref2va', '미니맥스 영상 편집'),
    'wan22-i2v': ('wan22-i2v', 'wan 2.2 i2v', 'wan2.2 i2v'),
    'wan21-i2v': ('wan21-i2v', 'wan 2.1 i2v'),
    'wan21-t2v': ('wan21-t2v', 'wan 2.1 t2v'),
    'wan22-vace': ('vace',),
    'wan22-fun-control': ('fun control', 'fun-control'),
    'wan22-animate2': ('animate2', 'animate-2'),
    'dwpose': ('dwpose',),
}


def select_video_proposal(proposal, request):
    """이전 기록은 보존하고 신규 기록은 명시 여부와 정책을 검증한다."""
    if 'minimax_preferred' not in request:
        return proposal
    preferred = request['minimax_preferred']
    if type(preferred) is not bool or type(proposal.get('explicit_service')) is not bool:
        raise ValueError('생성기 선택 또는 게이트웨이 정책을 확인할 수 없습니다. 요청을 다시 확인하세요.')
    context = request.get('context') or {}
    messages = context.get('messages', []) if isinstance(context, dict) else []
    texts = [item.get('content', '') for item in messages[-3:] if isinstance(item, dict) and item.get('role') == 'user' and isinstance(item.get('content'), str)] if isinstance(messages, list) else []
    texts.append(request.get('prompt', ''))
    text = '\n'.join(value for value in texts if isinstance(value, str)).casefold()
    mentioned = {service for service, aliases in _ALIASES.items() if any(re.search(r'(?<![a-z0-9])' + re.escape(alias) + r'(?![a-z0-9])', text) for alias in aliases)}
    if not mentioned and re.search(r'(?<![a-z0-9])(?:minimax|mini max)(?![a-z0-9])|미니\s*맥스', text):
        mentioned.add('minimax-h3-ref2va' if proposal.get('mode') == 'video_edit' else 'minimax-h3-i2v')
    # 일반적인 Wan 명칭만으로는 버전이나 용도를 확정할 수 없다.
    ambiguous_wan = bool(re.search(r'(?<![a-z0-9])wan(?:\s*2(?:\.\s*[12])?)?(?![a-z0-9])|완\s*모델', text)) and not mentioned
    explicit = proposal['explicit_service']
    service = proposal['service']
    if ambiguous_wan or (mentioned and (len(mentioned) != 1 or not explicit or service not in mentioned)) or (explicit and service not in mentioned):
        raise ValueError('사용자가 지정한 영상 생성기를 확정할 수 없습니다. 생성기를 명확히 지정해 주세요.')
    result = {key: value for key, value in proposal.items() if key != 'explicit_service'}
    if explicit:
        result['selection_reason'] = '사용자가 생성기를 지정했습니다.'
    elif preferred and proposal['mode'] == 'first_frame' and service in ('wan22-i2v', 'wan21-i2v', 'wan22-vace', 'minimax-h3-i2v'):
        result['service'] = 'minimax-h3-i2v'
        result['selection_reason'] = 'MiniMax 우선 정책과 첫 프레임 입력을 적용했습니다.'
    else:
        result['selection_reason'] = '요청 형식과 기존 선택을 적용했습니다.'
    return result
