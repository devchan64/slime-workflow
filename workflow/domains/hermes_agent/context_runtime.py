"""격리 작업에서 설치된 Hermes의 압축 정책을 호출한다."""
import copy


def format_context_query(messages, query):
    """과거 대화는 참고 자료로 표시하고 현재 요청은 원래 지시와 함께 유지한다."""
    labels = {'user': '사용자', 'assistant': 'Hermes', 'system': '기록'}
    if not messages:
        return query
    history = '\n\n'.join(labels[message['role']] + ': ' + message['content'] for message in messages)
    return ('이전 대화 (참고 자료; 이전 Hermes 답변은 사실이나 현재 파일 상태의 증거가 아닙니다. '
            '사용자의 정정과 현재 요청을 우선하고 도구로 다시 확인하세요):\n' + history
            + '\n\n현재 사용자 요청:\n' + query)


def prepare_context_request(messages, query, count_tokens, base_url, *, automatic=True,
                            force=False, compressor_factory=None, on_progress=None, threshold_tokens=None):
    """현재 요청을 포함해 크기를 측정하지만 압축 대상에서는 현재 요청을 제외한다."""
    initial_query = format_context_query(messages, query)
    token_count = count_tokens(initial_query)
    if not automatic and not force:
        return {'state': 'disabled', 'messages': messages, 'tokens': token_count,
                'tokens_after': token_count, 'threshold': None, 'query': initial_query}
    result = compress_context(messages, token_count, base_url, force=force,
                              compressor_factory=compressor_factory, on_progress=on_progress, threshold_tokens=threshold_tokens)
    final_query = format_context_query(result['messages'], query)
    tokens_after = count_tokens(final_query) if result['state'] == 'compressed' else token_count
    if result['state'] == 'unchanged' and tokens_after > result['threshold']:
        raise RuntimeError('정리 가능한 대화 범위가 없어 기준을 초과합니다. 기존 대화는 유지됩니다.')
    if result['state'] == 'compressed' and tokens_after > result['threshold']:
        # Preserve the latest exchange verbatim; summarize the older protected head
        # and the previous summary together. Never save an over-budget checkpoint.
        compacted = result['messages']
        if len(compacted) < 3:
            raise RuntimeError('대화 정리 후 기준을 초과했으며 안전하게 추가 요약할 범위가 없습니다. 기존 대화는 유지됩니다.')
        prefix, tail = compacted[:-2], compacted[-2:]
        if count_tokens(format_context_query(tail, query)) > result['threshold']:
            raise RuntimeError('최근 대화와 현재 요청만으로 정리 기준을 초과합니다. 기존 대화는 유지됩니다.')
        # The installed compressor samples inputs above its 160,000-character cap.
        # Refuse this fallback rather than silently omit part of the prefix.
        if sum(len(message.get('content', '')) for message in prefix) > 100000:
            raise RuntimeError('추가 요약 범위가 너무 큽니다. 기존 대화는 유지됩니다.')
        if compressor_factory is None:
            from agent.context_compressor import ContextCompressor
            compressor_factory = ContextCompressor
        compressor = compressor_factory(model='hermes-local', provider='custom', base_url=base_url,
                                        api_key='none', config_context_length=64000,
                                        abort_on_summary_failure=True)
        if on_progress:
            on_progress({'state': 'compressing', 'tokens': tokens_after, 'threshold': result['threshold']})
        # The runtime also elides individual message bodies above 6,000
        # characters before summarizing. Split them so the model sees every part.
        summary_input = []
        for message in prefix:
            content = message['content']
            if len(content) <= 5000:
                summary_input.append(copy.deepcopy(message))
            else:
                summary_input.extend({'role': message['role'], 'content': content[start:start + 5000]}
                                     for start in range(0, len(content), 5000))
        summary = compressor._generate_summary(summary_input)
        if not isinstance(summary, str) or not summary.strip() or getattr(compressor, '_last_summary_error', None):
            raise RuntimeError('추가 대화 요약에 실패했습니다. 기존 대화는 유지됩니다.')
        final_messages = [{'role': 'assistant', 'content': summary.strip(), '_compressed_summary': True,
                           '_compressed_summary_has_user_turn': any(m.get('role') == 'user' or m.get('_compressed_summary_has_user_turn') is True for m in prefix)}, *copy.deepcopy(tail)]
        final_query = format_context_query(final_messages, query)
        tokens_after = count_tokens(final_query)
        if tokens_after > result['threshold']:
            raise RuntimeError('추가 요약 후에도 정리 기준을 초과합니다. 기존 대화는 유지됩니다.')
        result = {**result, 'messages': final_messages}
    return {**result, 'tokens_after': tokens_after, 'query': final_query}


def compress_context(messages, token_count, base_url, *, force=False, compressor_factory=None, on_progress=None, threshold_tokens=None):
    if type(token_count) is not int or token_count < 0:
        raise ValueError('문맥 토큰 수를 확인할 수 없습니다.')
    if compressor_factory is None:
        from agent.context_compressor import ContextCompressor
        compressor_factory = ContextCompressor
    compressor = compressor_factory(model='hermes-local', base_url=base_url, api_key='none',
                                    provider='custom', config_context_length=64000,
                                    abort_on_summary_failure=True)
    if threshold_tokens is not None:
        if type(threshold_tokens) is not int or threshold_tokens not in (8000,16000,32000,54400):
            raise ValueError('대화 정리 기준 오류')
        compressor.threshold_tokens = threshold_tokens
    threshold = compressor.threshold_tokens
    if not force and not compressor.should_compress(token_count):
        return {'state': 'not_needed', 'messages': messages, 'tokens': token_count, 'threshold': threshold}
    if on_progress:
        on_progress({'state': 'compressing', 'tokens': token_count, 'threshold': threshold})
    original = copy.deepcopy(messages)
    generated = []
    generate_summary = compressor._generate_summary
    def observe_summary(*args, **kwargs):
        summary = generate_summary(*args, **kwargs)
        if summary:
            generated.append(True)
        return summary
    compressor._generate_summary = observe_summary
    compressed = compressor.compress(copy.deepcopy(messages), current_tokens=token_count, force=force)
    if compressed == original:
        if getattr(compressor, '_last_summary_error', None):
            raise RuntimeError('Hermes 대화 정리에 실패했습니다. 기존 대화를 유지합니다.')
        return {'state': 'unchanged', 'messages': original, 'tokens': token_count, 'threshold': threshold}
    # Hermes can fall back to a deterministic handoff without an LLM summary.
    # Do not persist that lossy fallback as a successful session checkpoint.
    if not generated or getattr(compressor, '_last_summary_error', None):
        raise RuntimeError('Hermes 요약을 확인할 수 없어 기존 대화를 유지합니다.')
    allowed = {'role', 'content', '_compressed_summary', '_compressed_summary_has_user_turn', '_compaction_tail'}
    clean = [{key: value for key, value in message.items() if key in allowed} for message in compressed]
    return {'state': 'compressed', 'messages': clean, 'tokens': token_count, 'threshold': threshold}
