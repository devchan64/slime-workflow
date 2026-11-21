"""Resolve explicit, unchanged Kimodo example requests without guessing model output."""
import json
import re

_REQUEST = re.compile(
    r'\s*Kimodo\s+[^\n()]{1,100}예제\s*\((?P<id>[a-z0-9_]{1,80})\)를\s*'
    r'최신\s*설정\s*그대로\s*사용하여\s*서기\s*(?P<a>\d+)\s*프레임\s*,\s*'
    r'휴식\s*(?P<b>\d+)\s*프레임\s*,\s*일어서기\s*(?P<c>\d+)\s*프레임의\s*'
    r'총\s*(?P<total>\d+)\s*프레임\s*순차\s*생성\s*작업을\s*접수해\s*주세요\.\s*'
    r'예제의\s*나머지\s*설정과\s*참조\s*이미지도\s*그대로\s*사용해\s*주세요\.?\s*', re.IGNORECASE)


def resolve_kimodo_example_request(prompt, examples):
    """Only resolve a fully specified request when it agrees with the registered example."""
    match = _REQUEST.fullmatch(prompt) if isinstance(prompt, str) else None
    if not match:
        return None
    example = examples.get(match['id'])
    segments = [int(match[key]) for key in ('a', 'b', 'c')]
    total = int(match['total'])
    if not isinstance(example, dict) or example.get('frames') != total or sum(segments) != total:
        return None
    if example.get('settings', {}).get('segment_frames') != segments or not example.get('reference_example'):
        return None
    return {'example_id': match['id'], 'label': example['label'], 'frames': total, 'segments': segments}


def kimodo_example_response(resolved):
    proposal = json.dumps({'example_id': resolved['example_id']}, ensure_ascii=False)
    return (f"등록된 Kimodo 예제 **{resolved['label']}**를 확인했습니다. "
            f"총 {resolved['frames']}프레임 ({' + '.join(map(str, resolved['segments']))})의 "
            "설정과 참조 이미지를 생성 폼에서 검토할 수 있습니다. 아직 생성 작업은 접수되지 않았습니다.\n\n"
            f"HERMES_KIMODO_PROPOSAL\n{proposal}\nEND_HERMES_KIMODO_PROPOSAL")
