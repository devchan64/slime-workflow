"""접수된 정책과 사용자 지시를 검증해 일반 이미지 생성기를 선택한다."""
import re


def select_image_proposal(proposal, request):
    from workflow.domains.hermes_agent.delegation_proposal import validate_image_proposal_for_service
    if request.get('image_selection_version') != 1:
        return validate_image_proposal_for_service(proposal)
    preferred = request.get('minimax_preferred')
    explicit = proposal.get('explicit_service')
    if type(preferred) is not bool or type(explicit) is not bool:
        raise ValueError('이미지 생성기 지정 여부를 확인할 수 없습니다. 다시 요청하세요.')
    context = request.get('context') or {}
    messages = context.get('messages', []) if isinstance(context, dict) else []
    texts = [item.get('content', '') for item in messages[-3:] if isinstance(item, dict) and item.get('role') == 'user' and isinstance(item.get('content'), str)] if isinstance(messages, list) else []
    texts.append(request.get('prompt', ''))
    text = '\n'.join(value for value in texts if isinstance(value, str)).casefold()
    has_mini = bool(re.search(r'(?<![a-z0-9])(?:minimax|mini\s+max)(?![a-z0-9])|미니\s*맥스', text))
    has_flux = bool(re.search(r'(?<![a-z0-9])flux(?:-[a-z]+)?(?![a-z0-9])|플럭스', text))
    if has_mini and has_flux or (has_mini or has_flux) != explicit:
        raise ValueError('지정한 이미지 생성기를 확정할 수 없습니다. 다시 확인해 주세요.')
    result = {key: value for key, value in proposal.items() if key != 'explicit_service'}
    service = result.get('service', 'flux-image')
    compatible = service == 'flux-image' and (result['width'], result['height']) in ((512, 512), (1024, 1024))
    if has_mini and not compatible:
        raise ValueError('MiniMax 이미지 폼은 512×512 또는 1024×1024 일반 텍스트 생성만 지원합니다. 입력을 다시 확인하세요.')
    if compatible and (has_mini or (preferred and not explicit)):
        result['service'] = 'minimax-h3-image'
        result['selection_reason'] = '사용자가 MiniMax를 지정했습니다.' if has_mini else 'MiniMax 우선 정책을 적용했습니다.'
    elif explicit:
        result['selection_reason'] = '사용자가 FLUX를 지정했습니다.'
    else:
        result['selection_reason'] = '요청 형식에 맞는 기존 생성기를 선택했습니다.'
    return validate_image_proposal_for_service(result)
