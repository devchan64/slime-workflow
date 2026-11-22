import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from workflow.domains.hermes_agent.progress_watch import ProgressWatch, wait_for_progress

class Clock:
    now = 0
    def __call__(self): return self.now

class Process:
    def __init__(self, clock, action=None, end=None): self.clock, self.action, self.end = clock, action, end
    def poll(self): return 0 if self.end is not None and self.clock.now >= self.end else None
    def wait(self, timeout):
        self.clock.now += timeout
        if self.action: self.action(self.clock.now)
        if self.poll() is not None: return 0
        raise subprocess.TimeoutExpired('agent', timeout)

class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name)/'server.log'; self.events = Path(self.tmp.name)/'events'
        self.log.write_text('old task 1 | prompt processing, n_tokens = 500\n'); self.events.write_text('')
        self.watch = ProgressWatch(self.log, self.events)
    def append(self, path, value):
        with path.open('a') as f: f.write(value)
    def test_only_increasing_prompt_tokens_or_agent_events_count(self):
        self.assertIsNone(self.watch.read())
        self.append(self.log, 'task 4 | prompt processing, n_tokens = 12\n')
        self.assertEqual(self.watch.read(), 'prompt_processing')
        self.append(self.log, 'task 4 | prompt processing, n_tokens = 12\nunrelated heartbeat\n')
        self.assertIsNone(self.watch.read())
        self.append(self.events, json.dumps({'type':'tool_result'})+'\n')
        self.assertEqual(self.watch.read(), 'agent_event')
    def test_observation_can_resume_after_gap(self):
        clock=Clock(); messages=[]
        def progress(now):
            if now == 15: self.append(self.events, json.dumps({'type':'tool_result'})+'\n')
        self.assertEqual(wait_for_progress(Process(clock,progress,end=20),self.watch,idle_seconds=10,max_seconds=30,interval=5,clock=clock,notify=lambda message,**kw:messages.append(message),phase='대화 문맥 준비'),0)
        self.assertTrue(any('관측 불가' in m for m in messages))
        self.assertTrue(any('관측 재개' in m for m in messages))
    def test_progress_extends_idle_but_not_hard_limit(self):
        clock=Clock()
        def progress(now): self.append(self.log, f'task 4 | prompt processing, n_tokens = {int(now)}\n')
        with self.assertRaisesRegex(TimeoutError, '전체 실행 제한'):
            wait_for_progress(Process(clock,progress),self.watch,idle_seconds=10,max_seconds=25,interval=5,clock=clock)
    def test_completion_returns_exit_code(self):
        clock=Clock()
        self.assertEqual(wait_for_progress(Process(clock,end=5),self.watch,idle_seconds=10,max_seconds=30,interval=5,clock=clock),0)

if __name__ == '__main__': unittest.main()
