import json
import tempfile
import unittest
from pathlib import Path

from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class ToolResultTests(unittest.TestCase):
    def test_full_result_is_bound_to_session_and_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, other = 'a' * 32, 'b' * 32
            job, call = '2026-11-25_23-24-11-76adffd1', 'call_123'
            store = HermesSessionStore(root / 'sessions')
            for current in (session, other): store.create_session_record(current)
            store.append_session_request(session, 'original_request', '확인')
            store.attach_session_job(session, 'original_request', job)
            path = root / 'jobs' / job
            path.mkdir(parents=True)
            output = '앞' * 5000 + '오류 끝'
            (path / 'hermes-events.jsonl').write_text(json.dumps({'type':'tool_result','tool_call_id':call,'output':output,'is_error':True},ensure_ascii=False)+'\n')
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            payload = {'session_id':session,'id':job,'call_id':call}
            result = manager.execute_hermes_command('hermes-tool-result', payload)
            self.assertEqual(result['output'], output)
            self.assertTrue(result['is_error'])
            with self.assertRaises(ValueError): manager.execute_hermes_command('hermes-tool-result', {**payload,'session_id':other})
            with self.assertRaises(ValueError): manager.execute_hermes_command('hermes-tool-result', {**payload,'call_id':'../bad'})


if __name__ == '__main__': unittest.main()
