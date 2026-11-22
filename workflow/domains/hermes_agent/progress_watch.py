"""Hermes 실행의 관측된 진행과 관측 공백을 구분한다."""
import json
import re
import subprocess
import time
from pathlib import Path

_PROMPT = re.compile(r'task\s+(\d+)\s+\| prompt processing, n_tokens\s*=\s*(\d+)')

class ProgressWatch:
    def __init__(self, log_path, event_path):
        self.paths = [Path(log_path), Path(event_path)]
        self.offsets = [self.paths[0].stat().st_size if self.paths[0].exists() else 0, 0]
        self.pending = ['', '']
        self.task = None
        self.tokens = -1

    def read(self):
        activity = None
        for i, path in enumerate(self.paths):
            try:
                with path.open('r', encoding='utf-8', errors='replace') as stream:
                    stream.seek(self.offsets[i]); data = stream.read(); self.offsets[i] = stream.tell()
            except FileNotFoundError:
                continue
            lines = (self.pending[i] + data).split('\n')
            self.pending[i] = lines.pop()
            for line in lines:
                if i == 0:
                    match = _PROMPT.search(line)
                    if match:
                        task, tokens = map(int, match.groups())
                        if task != self.task or tokens > self.tokens:
                            self.task, self.tokens, activity = task, tokens, 'prompt_processing'
                else:
                    try: event = json.loads(line)
                    except ValueError: continue
                    if isinstance(event, dict) and event.get('type') in ('tool_use', 'tool_result', 'result'):
                        activity = 'agent_event'
        return activity


def wait_for_progress(process, watch, *, idle_seconds=1200, max_seconds=3600, interval=5,
                      clock=time.monotonic, notify=print, phase='에이전트 실행'):
    """관측 공백은 대기 상태로 유지하고 이후 신호가 오면 복귀한다."""
    start = last = clock()
    last_kind = None
    unobserved = False
    while True:
        code = process.poll()
        if code is not None:
            return code
        now = clock()
        kind = watch.read()
        if kind:
            last, last_kind = now, kind
            if unobserved:
                notify(f'{phase}: 진행 관측 재개 ({kind})', flush=True)
                unobserved = False
        if now - start >= max_seconds:
            raise TimeoutError(f'{phase}: 전체 실행 제한 초과 ({max_seconds}초); 마지막 관측: {last_kind or "없음"}')
        if not unobserved and now - last >= idle_seconds:
            notify(f'{phase}: {idle_seconds}초 동안 진행 관측 불가; 종료를 단정하지 않고 계속 대기합니다.', flush=True)
            unobserved = True
        try:
            return process.wait(timeout=min(interval, max_seconds-(now-start)))
        except subprocess.TimeoutExpired:
            pass
