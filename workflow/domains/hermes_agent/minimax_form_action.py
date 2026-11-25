"""Constrained session-bound form changes proposed by an isolated assistant."""
import re


def _bound_question_target(user_prompt, payload):
    ids = re.findall(r'(?m)^대상 폼 ID: ([a-f0-9]{32})[ \t]*$', user_prompt)
    versions = re.findall(r'(?m)^대상 폼 버전: ([1-9][0-9]*)[ \t]*$', user_prompt)
    if (len(re.findall(r'(?m)^대상 폼 ID:', user_prompt)) != 1 or len(re.findall(r'(?m)^대상 폼 버전:', user_prompt)) != 1
            or len(ids) != 1 or len(versions) != 1 or ids[0] != payload['form_id'] or int(versions[0]) != payload['revision']):
        raise ValueError('사용자가 확인한 폼 ID 또는 버전과 접수 대상이 다릅니다.')


def _question_form_snapshot(session_id, payload, dispatch):
    form = dispatch('hermes-minimax-form-read', {'session_id':session_id, 'form_id':payload['form_id']})
    if (not isinstance(form, dict) or form.get('session_id') != session_id or form.get('form_id') != payload['form_id']
            or form.get('revision') != payload['revision'] or form.get('state') != 'editing'
            or form.get('service') != 'minimax-h3-image' or not isinstance(form.get('request'), dict)):
        raise ValueError('승인 대상 이미지 폼이 변경되었거나 확인되지 않습니다.')
    from .reference_intent import requires_reference
    if requires_reference(form['request'].get('prompt')) and not form['request'].get('images'):
        raise ValueError('참조 이미지가 필요한 폼입니다. 참조 PNG를 첨부하고 저장한 뒤 다시 확인하세요.')
    return form


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
    is_question_answer = bool(re.search(r'(?m)^질문 작업 \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}에 대한 답변:', user_prompt))
    authorization_text = '\n'.join(re.findall(r'(?m)^답변(?: 계속)?: ([^\r\n]*)$', user_prompt)) if is_question_answer else user_prompt
    # A standalone approval is meaningful only with a bound form and version.
    # The binding and resident GPU check below must both succeed first.
    bound_approval = bool(re.fullmatch(
        r'질문 작업 \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}에 대한 답변:\n'
        r'대상 폼 ID: [a-f0-9]{32}\n대상 폼 버전: [1-9][0-9]*\n1\. [^\r\n]+\n답변: 승인', user_prompt.strip()))
    if not bound_approval and (not re.search(r'접수|대기열|enqueue|submit', authorization_text, re.IGNORECASE)
            or not re.search(r'해\s*(?:줘|주세요|라)|(?:넣|추가|보내|올려|등록)(?:어|아|해|줘|주세요|라)|\b(?:enqueue|submit)\b', authorization_text, re.IGNORECASE)
            or re.search(r'거절|반대|취소|하지\s*(?:마|말|않)|(?:접수|대기열).{0,12}(?:마세요|말아|하지\s*마)|\b(?:do not|don.t|never)\b|(?:가능|될까|되나요|할까|할까요|할\s*수\s*있)', authorization_text, re.IGNORECASE)):
        raise ValueError('현재 사용자 메시지에서 접수 지시를 확인할 수 없습니다.')
    if not isinstance(payload, dict) or set(payload) != {'form_id','revision'} or not isinstance(payload['form_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', payload['form_id']) or type(payload['revision']) is not int or payload['revision'] < 1:
        raise ValueError('폼 ID 또는 버전 오류')
    if is_question_answer and not re.search(r'(?m)^대상 폼 (?:ID|버전):', user_prompt):
        raise ValueError('질문한 폼 ID와 버전을 확인하세요.')
    if re.search(r'(?m)^대상 폼 (?:ID|버전):', user_prompt):
        _bound_question_target(user_prompt, payload)
    if is_question_answer:
        form = _question_form_snapshot(session_id, payload, dispatch)
        owner = dispatch('hermes-resident-status', {'session_id':session_id})
        if not isinstance(owner, dict) or not isinstance(owner.get('resident'), dict):
            raise ValueError('상주 모델 상태를 확인할 수 없습니다.')
        if owner['resident'].get('state') == 'ready':
            resident_id = owner.get('resident_id')
            target = {'form_id':payload['form_id'],'revision':payload['revision'],'request':form['request']}
            review = dispatch('hermes-gpu-handoff-preview', {'session_id':session_id,'resident_id':resident_id,
                              'service':form['service'],'request':target})
            if not isinstance(review, dict) or not re.fullmatch(r'[a-f0-9]{64}', str(review.get('review_hash',''))):
                raise ValueError('GPU 양도 검토 결과를 확인할 수 없습니다.')
            return {'state':'requires_gpu_handoff', 'form_id':payload['form_id'], 'revision':payload['revision'],
                    'resident_id':resident_id, 'review_hash':review['review_hash']}
        if owner['resident'].get('state') != 'not_found':
            raise ValueError('상주 모델 상태를 확인하거나 별도 GPU 양도 검토와 동의를 먼저 진행하세요.')
    result = dispatch('hermes-minimax-form-submit', {'session_id':session_id, **payload})
    if not isinstance(result, dict) or result.get('state') not in ('accepted', 'unknown'):
        raise ValueError('접수 결과를 확인할 수 없습니다. 기존 접수 상태를 다시 조회하세요.')
    if result['state'] == 'accepted' and (not isinstance(result.get('job_id'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', result['job_id'])):
        raise ValueError('접수 작업 ID를 확인할 수 없습니다.')
    return {key:result[key] for key in ('state','job_id','service','duplicate') if key in result}


def confirm_question_handoff(session_id, user_prompt, payload, dispatch):
    """An independently confirmed question may approve only its exact GPU review."""
    if not isinstance(session_id,str) or not re.fullmatch(r'[a-f0-9]{32}',session_id) or not isinstance(user_prompt,str) or len(user_prompt)>8000:
        raise ValueError('대화 또는 사용자 응답 오류')
    if (not isinstance(payload,dict) or set(payload)!={'form_id','revision','resident_id','review_hash'}
            or not isinstance(payload['form_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',payload['form_id'])
            or type(payload['revision']) is not int or payload['revision']<1
            or not isinstance(payload['resident_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',payload['resident_id'])
            or not isinstance(payload['review_hash'],str) or not re.fullmatch(r'[a-f0-9]{64}',payload['review_hash'])):
        raise ValueError('양도 검토 대상 오류')
    if not re.fullmatch(r'질문 작업 \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}에 대한 답변:\n'
                        r'대상 폼 ID: [a-f0-9]{32}\n대상 폼 버전: [1-9][0-9]*\n'
                        r'상주 모델 ID: [A-Za-z0-9_-]{8,80}\nGPU 양도 검토: [a-f0-9]{64}\n'
                        r'1\. [^\r\n]+\n답변: GPU 양도에 동의',user_prompt.strip()):
        raise ValueError('GPU 양도에 대한 별도 동의가 필요합니다.')
    _bound_question_target(user_prompt,payload)
    for label,key in (('상주 모델 ID','resident_id'),('GPU 양도 검토','review_hash')):
        values = re.findall(r'(?m)^'+label+r': ([A-Za-z0-9_-]+)[ \t]*$',user_prompt)
        if len(values)!=1 or values[0]!=payload[key] or len(re.findall(r'(?m)^'+label+r':',user_prompt))!=1:
            raise ValueError('사용자가 확인한 GPU 양도 대상이 다릅니다.')
    form = _question_form_snapshot(session_id,payload,dispatch)
    owner = dispatch('hermes-resident-status',{'session_id':session_id})
    if not isinstance(owner,dict) or owner.get('resident_id')!=payload['resident_id'] or owner.get('resident',{}).get('state')!='ready':
        raise ValueError('상주 모델이 변경되었거나 준비되지 않았습니다.')
    from .flux_reports import proposal_request_id
    request = {'form_id':payload['form_id'],'revision':payload['revision'],'request':form['request']}
    result = dispatch('hermes-gpu-handoff-approve', {'request_id':proposal_request_id(session_id,form['source_job_id'],form['service']),
        'session_id':session_id,'resident_id':payload['resident_id'],'service':form['service'],'request':request,
        'review_hash':payload['review_hash'],'confirmed':True})
    if not isinstance(result,dict) or not isinstance(result.get('state'),str):
        raise ValueError('양도 승인 결과를 확인할 수 없습니다.')
    return {key:result[key] for key in ('id','state','revision','duplicate') if key in result}
