"""In-process adapter for a single running Hermes agent.

Only an explicit receipt can establish acceptance; a lost connection is ambiguous.
"""
import re
import threading

_ID = re.compile(r'[A-Za-z0-9_-]{8,80}\Z')


class LiveInstructionRuntime:
    def __init__(self, agent):
        self.agent = agent
        self.lock = threading.Lock()
        self.requests = {}
        self.closed = False

    def submit(self, request_id, mode, text):
        if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
            raise ValueError('지시 접수 ID 형식 오류')
        if mode not in ('steer', 'redirect') or not isinstance(text, str) or not text.strip() or len(text) > 8000:
            raise ValueError('지시 형식 오류')
        with self.lock:
            prior = self.requests.get(request_id)
            if prior:
                if (prior['mode'], prior['text']) != (mode, text):
                    raise ValueError('같은 접수 ID를 다른 지시에 사용할 수 없습니다.')
                return dict(prior)
            if self.closed:
                return {'request_id': request_id, 'state': 'undelivered'}
            row = {'request_id': request_id, 'mode': mode, 'text': text, 'state': 'delivering'}
            self.requests[request_id] = row
        try:
            marked_text = text + '\n[지시 접수 ID: ' + request_id + ']'
            accepted = (self.agent.steer(marked_text, ticket=request_id) if mode == 'steer'
                        else self.agent.redirect(marked_text))
        except Exception:
            accepted = 'unknown'
        with self.lock:
            # The gateway may finish while the response is in flight.
            if row['state'] == 'delivering':
                row['state'] = 'accepted' if accepted is True else 'unknown' if accepted == 'unknown' else 'undelivered'
            return dict(row)

    def observe(self, messages):
        transcript = [message.get('content') for message in messages if isinstance(message, dict) and message.get('role') == 'user'] if isinstance(messages, list) else []
        with self.lock:
            for row in self.requests.values():
                marker = '[지시 접수 ID: ' + row['request_id'] + ']'
                if row['state'] == 'accepted' and any(isinstance(text, str) and marker in text for text in transcript):
                    row['state'] = 'applied'
            return [dict(row) for row in self.requests.values()]

    def close(self, result=None):
        messages = result.get('messages', []) if isinstance(result, dict) else []
        transcript = [message.get('content') for message in messages if isinstance(message, dict) and message.get('role') == 'user'] if isinstance(messages, list) else []
        with self.lock:
            self.closed = True
            for row in self.requests.values():
                if row['state'] == 'accepted' and row['mode'] == 'steer':
                    try:
                        fates = getattr(self.agent, '_steer_ticket_fates', {})
                        consumed = fates.get(row['request_id']) is True
                        removed = self.agent.withdraw_steer(row['request_id'])
                        row['state'] = 'undelivered' if removed else 'applied' if consumed else 'unknown'
                    except Exception:
                        row['state'] = 'unknown'
                elif row['state'] == 'accepted' and row['mode'] == 'redirect':
                    marker = '[지시 접수 ID: ' + row['request_id'] + ']'
                    row['state'] = 'applied' if any(isinstance(text, str) and marker in text for text in transcript) else 'unknown'
                elif row['state'] in ('accepted', 'delivering'):
                    row['state'] = 'unknown'
            return [dict(row) for row in self.requests.values()]
