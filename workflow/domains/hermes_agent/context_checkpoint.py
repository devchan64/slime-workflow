"""대화 원문을 보존하면서 압축 결과의 적용 범위를 확인한다."""
import hashlib
import json


def context_prefix_digest(messages, count):
    """압축 대상 메시지의 내용과 연결된 작업을 고정한다."""
    if type(count) is not int or not 0 <= count <= len(messages):
        raise ValueError('압축 범위가 올바르지 않습니다.')
    raw = json.dumps(messages[:count], ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def validate_context_checkpoint(checkpoint, messages):
    if not isinstance(checkpoint, dict) or not {'count', 'digest', 'messages'} <= set(checkpoint) or set(checkpoint) - {'count', 'digest', 'messages', 'created_at'}:
        raise ValueError('압축 기록 형식 오류')
    if 'created_at' in checkpoint and not isinstance(checkpoint['created_at'], str):
        raise ValueError('압축 시각 형식 오류')
    count, digest, compacted = checkpoint['count'], checkpoint['digest'], checkpoint['messages']
    if not isinstance(digest, str) or digest != context_prefix_digest(messages, count):
        raise ValueError('압축 대상 대화가 변경되었습니다.')
    if not isinstance(compacted, list) or not compacted:
        raise ValueError('압축된 대화가 비어 있습니다.')
    for message in compacted:
        if not isinstance(message, dict) or not {'role', 'content'} <= set(message) or set(message) - {'role', 'content', '_compressed_summary', '_compressed_summary_has_user_turn', '_compaction_tail'} or message['role'] not in ('user', 'assistant', 'system') or not isinstance(message['content'], str):
            raise ValueError('압축된 대화 형식 오류')
        if any(type(value) is not bool for key, value in message.items() if key.startswith('_')):
            raise ValueError('압축된 대화 메타데이터 오류')
    return checkpoint


def build_context_messages(session, read_job):
    """유효한 압축본과 그 이후 원문을 Hermes 메시지 배열로 복원한다."""
    records = session['messages']
    checkpoint = session.get('context_checkpoint')
    if checkpoint:
        validate_context_checkpoint(checkpoint, records)
        context = [dict(message) for message in checkpoint['messages']]
        start = checkpoint['count']
    else:
        context, start = [], 0
    for record in records[start:]:
        if record.get('form_id'):
            context.append({'role': 'user', 'content': 'Wan Fun Control 생성 폼을 저장했습니다.'})
            continue
        job_id = record.get('job_id')
        if not job_id:
            raise ValueError('이전 메시지의 접수 상태를 확인한 뒤 다시 시도하세요.')
        job = read_job(job_id)
        status = job['status'].get('status', 'unknown')
        if status not in ('completed', 'failed', 'cancelled'):
            raise ValueError('이전 작업이 종료된 후 다시 시도하세요.')
        if job.get('final_response_truncated'):
            raise ValueError('이전 응답이 잘려 대화 문맥을 안전하게 구성할 수 없습니다.')
        context.append({'role': 'user', 'content': record['text']})
        context.append({'role': 'assistant', 'content': job.get('final_response') or '[최종 응답 없음: ' + status + ']'})
    return context


def build_coding_context_messages(session, read_job):
    """원문 사용자 발화는 모두 보존하고 오래되거나 긴 답변의 생략을 명시한다."""
    messages = build_context_messages({'messages': session['messages']}, read_job)
    assistant_indices = [index for index, message in enumerate(messages) if message['role'] == 'assistant']
    recent = set(assistant_indices[-2:])
    omitted = 0
    selected = []
    for index, message in enumerate(messages):
        if message['role'] == 'assistant' and (index not in recent or len(message['content']) > 4000):
            omitted += 1
        else:
            selected.append(message)
    if omitted:
        selected.insert(0, {'role': 'system', 'content': f'코딩 작업 문맥에서 이전 Hermes 답변 {omitted}건을 생략했습니다. 원본 대화는 보존됩니다. 생략된 답변 내용은 확인되지 않았습니다.'})
    return selected, omitted


def make_context_checkpoint(session, compressed_messages):
    """압축에 사용된 원문 경계를 고정하고 결과를 저장 가능한 형식으로 검사한다."""
    records = session['messages']
    checkpoint = {'count': len(records), 'digest': context_prefix_digest(records, len(records)),
                  'messages': compressed_messages}
    return validate_context_checkpoint(checkpoint, records)
