"""Constrained session-bound form changes proposed by an isolated assistant."""
import re


def apply_requested_form_update(session_id, user_prompt, payload, dispatch):
    """Use the actual current user turn as authority, never model-supplied text.

    This guard is deliberately limited to explicit edit language.  A model
    response, form content, or earlier conversation alone cannot authorize a
    mutation; unsupported phrasing can be handled by direct panel editing.
    """
    if not isinstance(session_id, str) or not re.fullmatch(r'[a-f0-9]{32}', session_id):
        raise ValueError('대화 세션을 확인할 수 없습니다.')
    if not isinstance(user_prompt, str) or len(user_prompt) > 8000:
        raise ValueError('현재 사용자 지시를 확인할 수 없습니다.')
    if (not re.search(r'수정|변경|바꿔|바꾸|고쳐|고치|조정|edit|change|modify|update', user_prompt, re.IGNORECASE)
            or re.search(r'하지\s*(?:마|말|않)|(?:바꾸|바꿔|수정|변경|고치|고쳐|조정).{0,8}(?:마세요|말아|하지\s*마)|\b(?:do not|don.t|never)\b|(?:가능|될까|되나요|할까|할까요|할\s*수\s*있)', user_prompt, re.IGNORECASE)):
        raise ValueError('현재 사용자 메시지에서 폼 수정 지시를 확인할 수 없습니다.')
    if not isinstance(payload, dict) or set(payload) != {'form_id','revision','request'}:
        raise ValueError('폼 ID·버전·변경 항목이 필요합니다.')
    if not isinstance(payload['form_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', payload['form_id']) or type(payload['revision']) is not int or payload['revision'] < 1:
        raise ValueError('폼 ID 또는 버전 오류')
    if not isinstance(payload['request'], dict) or not payload['request'] or set(payload['request']) - {'prompt','seed','width','height'}:
        raise ValueError('허용된 폼 변경 항목만 전달하세요.')
    terms = {
        'prompt': r'프롬프트|지시문|내용|장면|prompt|description',
        'seed': r'시드|seed',
        'width': r'크기|해상도|가로|너비|width|size|resolution|\d+\s*[x×]\s*\d+',
        'height': r'크기|해상도|세로|높이|height|size|resolution|\d+\s*[x×]\s*\d+',
    }
    # A request such as "지붕을 파란색으로 바꿔줘" is an explicit
    # content edit even if the user does not say the word "prompt".
    # Numeric-only settings do not authorize an unrelated prompt change.
    numeric_only = any(re.search(terms[key], user_prompt, re.IGNORECASE) for key in ('seed', 'width', 'height'))
    if any(not re.search(terms[key], user_prompt, re.IGNORECASE)
           and not (key == 'prompt' and not numeric_only)
           for key in payload['request']):
        raise ValueError('현재 사용자 메시지에서 변경 항목을 확인할 수 없습니다.')
    # Numeric settings must be explicitly present in the user's current turn;
    # the assistant cannot invent a value merely because a field was mentioned.
    numbers = {int(value) for value in re.findall(r'(?<![\d.])\d+(?![\d.])', user_prompt)}
    for key in ('seed', 'width', 'height'):
        if key in payload['request']:
            value = payload['request'][key]
            if type(value) is not int or value not in numbers:
                raise ValueError('변경할 숫자 값이 현재 사용자 지시에 명시되어 있지 않습니다.')
    dimensions = re.findall(r'(?<!\d)(\d+)\s*[x×]\s*(\d+)(?!\d)', user_prompt, re.IGNORECASE)
    if dimensions:
        if len(dimensions) != 1:
            raise ValueError('변경할 해상도를 명확히 지정하세요.')
        for key, value in zip(('width', 'height'), dimensions[0]):
            if key in payload['request'] and payload['request'][key] != int(value):
                raise ValueError('변경할 해상도가 사용자 지시와 일치하지 않습니다.')
    seed_value = re.search(r'(?:시드|seed)\s*(?:를|을|는|은|=|:)?\s*(\d+)', user_prompt, re.IGNORECASE)
    if 'seed' in payload['request'] and seed_value and payload['request']['seed'] != int(seed_value.group(1)):
        raise ValueError('변경할 시드가 사용자 지시와 일치하지 않습니다.')
    result = dispatch('hermes-minimax-form-update', {'session_id':session_id, **payload})
    if not isinstance(result, dict) or result.get('form_id') != payload['form_id'] or result.get('revision') != payload['revision'] + 1:
        raise ValueError('폼 수정 결과를 확인할 수 없습니다. 최신 폼을 다시 조회하세요.')
    return {key:result[key] for key in ('form_id','service','revision','state') if key in result}


def submit_requested_form(session_id, user_prompt, payload, dispatch):
    """Submit only when this user turn explicitly asks to enqueue a form."""
    if not isinstance(session_id, str) or not re.fullmatch(r'[a-f0-9]{32}', session_id):
        raise ValueError('대화 세션을 확인할 수 없습니다.')
    if not isinstance(user_prompt, str) or len(user_prompt) > 8000:
        raise ValueError('현재 사용자 지시를 확인할 수 없습니다.')
    if (not re.search(r'접수|대기열|enqueue|submit', user_prompt, re.IGNORECASE)
            or not re.search(r'해\s*(?:줘|주세요|라)|(?:넣|추가|보내|올려|등록)(?:어|아|해|줘|주세요|라)|\b(?:enqueue|submit)\b', user_prompt, re.IGNORECASE)
            or re.search(r'하지\s*(?:마|말|않)|(?:접수|대기열).{0,12}(?:마세요|말아|하지\s*마)|\b(?:do not|don.t|never)\b|(?:가능|될까|되나요|할까|할까요|할\s*수\s*있)', user_prompt, re.IGNORECASE)):
        raise ValueError('현재 사용자 메시지에서 접수 지시를 확인할 수 없습니다.')
    if not isinstance(payload, dict) or set(payload) != {'form_id','revision'} or not isinstance(payload['form_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', payload['form_id']) or type(payload['revision']) is not int or payload['revision'] < 1:
        raise ValueError('폼 ID 또는 버전 오류')
    result = dispatch('hermes-minimax-form-submit', {'session_id':session_id, **payload})
    if not isinstance(result, dict) or result.get('state') not in ('accepted', 'unknown'):
        raise ValueError('접수 결과를 확인할 수 없습니다. 기존 접수 상태를 다시 조회하세요.')
    if result['state'] == 'accepted' and (not isinstance(result.get('job_id'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', result['job_id'])):
        raise ValueError('접수 작업 ID를 확인할 수 없습니다.')
    return {key:result[key] for key in ('state','job_id','service','duplicate') if key in result}
