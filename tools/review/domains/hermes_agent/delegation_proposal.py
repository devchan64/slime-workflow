"""Hermes 답변의 미신뢰 Kimodo 제안을 검토 가능한 입력으로 제한한다."""
import re

HERMES_PROPOSAL_START = 'HERMES_KIMODO_PROPOSAL'
HERMES_PROPOSAL_END = 'END_HERMES_KIMODO_PROPOSAL'


def parse_hermes_kimodo_proposal(current_answer_text):
    """지정된 단일 블록만 파싱하며 동작 실행이나 접수는 수행하지 않는다."""
    from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
    from tools.review.common.management_gateway import parse_management_request_json
    if not isinstance(current_answer_text, str) or len(current_answer_text) > 8000:
        raise ValueError('최종 답변을 확인할 수 없습니다.')
    if current_answer_text.count(HERMES_PROPOSAL_START) != 2 or current_answer_text.count(HERMES_PROPOSAL_END) != 1:
        raise ValueError('Kimodo 제안 블록이 하나 필요합니다.')
    current_block_match = re.search(r'(?m)^HERMES_KIMODO_PROPOSAL\s*\n([\s\S]*?)\nEND_HERMES_KIMODO_PROPOSAL\s*$', current_answer_text)
    if current_block_match is None or len(current_block_match.group(1)) > 4000:
        raise ValueError('Kimodo 제안 형식 또는 크기 오류')
    current_proposal_record = parse_management_request_json(current_block_match.group(1))
    if not isinstance(current_proposal_record, dict) or set(current_proposal_record) != {'prompt', 'frames', 'steps', 'seed'}:
        raise ValueError('Kimodo 제안에는 prompt, frames, steps, seed만 허용합니다.')
    current_generation_record = {current_key_name: current_value for current_key_name, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key_name != 'schema_version'}
    current_generation_record.update(current_proposal_record, action='generate')
    validate_kimodo_request(current_generation_record)
    return current_proposal_record
