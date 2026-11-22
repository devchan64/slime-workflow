import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from workflow.domains.hermes_agent.context_checkpoint import build_context_messages, build_coding_context_messages, context_prefix_digest, make_context_checkpoint
from workflow.domains.hermes_agent.context_runtime import compress_context, format_context_query, prepare_context_request
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class HermesContextCheckpointTest(unittest.TestCase):
    def test_coding_context_preserves_user_corrections_and_discloses_omissions(self):
        records = [{'text': text, 'job_id': str(index)} for index, text in enumerate(('요구', '정정', '마지막'))]
        responses = ['오래된 답변', '긴 응답' * 2000, '최근 답변']
        context, omitted = build_coding_context_messages({'messages': records}, lambda job_id: {
            'status': {'status': 'completed'}, 'final_response': responses[int(job_id)]})
        self.assertEqual([m['content'] for m in context if m['role'] == 'user'], ['요구', '정정', '마지막'])
        self.assertEqual(omitted, 2)
        self.assertIn('2건을 생략', context[0]['content'])
        self.assertEqual(context[-1]['content'], '최근 답변')

    def test_token_counter_includes_system_and_tool_template(self):
        from workflow.domains.hermes_agent.sandbox_client import count_model_tokens
        calls = []
        def post(base, route, data):
            calls.append((route, data))
            return {'prompt': 'formatted'} if route == '/apply-template' else {'tokens': [1, 2, 3]}
        with patch('workflow.domains.hermes_agent.sandbox_client.post_model_json', side_effect=post):
            self.assertEqual(count_model_tokens('http://local', 'query', 'system', [{'name': 'tool'}]), 3)
        self.assertEqual(calls[0][1]['messages'][0]['content'], 'system')
        self.assertEqual(calls[0][1]['tools'], [{'name': 'tool'}])
        self.assertEqual(calls[1][1]['content'], 'formatted')

    def test_worker_commits_compressed_context_before_chat(self):
        from workflow.domains.hermes_agent.worker import prepare_worker_context
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = HermesSessionStore(root / 'sessions')
            session_id = 'a' * 32
            store.create_session_record(session_id)
            store.append_session_request(session_id, 'request_1', '질문')
            records = store.read_session_record(session_id)['messages']
            messages = [{'role': 'user', 'content': '질문'}, {'role': 'assistant', 'content': '답변'}]
            digest = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            context = {'session_id': session_id, 'count': 1, 'digest': context_prefix_digest(records, 1),
                       'messages_digest': digest, 'expected_checkpoint': None, 'automatic': True, 'messages': messages,
                       'force': False, 'only': False}
            job = root / 'job'; job.mkdir(); (job / 'query.txt').write_text('다음 질문')
            compressed = [{'role': 'user', 'content': '이전 대화 요약', '_compressed_summary': True}]
            def run_preflight(*args, **kwargs):
                result = {'state': 'compressed', 'messages': compressed, 'tokens': 54400,
                          'threshold': 54400, 'query': format_context_query(compressed, '다음 질문')}
                (job / 'context-exchange' / 'result.json').write_text(json.dumps(result, ensure_ascii=False))
                return SimpleNamespace(poll=lambda: 0)
            with (job / 'events').open('w') as stream, \
                 patch('workflow.domains.hermes_agent.worker.subprocess.Popen', side_effect=run_preflight), \
                 patch('workflow.domains.hermes_agent.session_store.HermesSessionStore', return_value=store):
                prepare_worker_context(job, context, ['bwrap', '--', 'client'], stream)
            self.assertEqual(store.read_session_record(session_id)['context_checkpoint']['messages'], compressed)
            self.assertIn('이전 대화 요약', (job / 'query.txt').read_text())
            self.assertIn('다음 질문', (job / 'query.txt').read_text())

    def test_automatic_and_manual_share_compressor_and_reject_lossy_fallback(self):
        class Compressor:
            threshold_tokens = 54400
            _previous_summary = 'summary'
            _last_summary_error = None
            def __init__(self, **kwargs):
                self.kwargs = kwargs
            def should_compress(self, count):
                return count >= self.threshold_tokens
            def _generate_summary(self):
                return self._previous_summary
            def compress(self, messages, **kwargs):
                self._generate_summary()
                return [{'role': 'user', 'content': 'summary', '_compressed_summary': True}]
        messages = [{'role': 'user', 'content': '원문'}]
        self.assertEqual(compress_context(messages, 100, 'http://localhost', compressor_factory=Compressor)['state'], 'not_needed')
        self.assertEqual(compress_context(messages, 54400, 'http://localhost', compressor_factory=Compressor)['state'], 'compressed')
        self.assertEqual(compress_context(messages, 100, 'http://localhost', force=True, compressor_factory=Compressor)['state'], 'compressed')
        measured = []
        result = prepare_context_request(messages, '현재 요청', lambda query: measured.append(query) or 54400,
                                         'http://localhost', compressor_factory=Compressor)
        self.assertIn('현재 요청', measured[0])
        self.assertIn('현재 요청', result['query'])
        self.assertIn('summary', result['query'])
        disabled = prepare_context_request(messages, '현재 요청', lambda _: 54400, 'http://localhost',
                                           automatic=False, compressor_factory=Compressor)
        self.assertEqual(disabled['state'], 'disabled')
        class Fallback(Compressor):
            _previous_summary = None
        with self.assertRaises(RuntimeError):
            compress_context(messages, 54400, 'http://localhost', compressor_factory=Fallback)

    def test_reconstructs_checkpoint_and_uncompressed_tail(self):
        records = [{'text': '첫 질문', 'job_id': 'first'}, {'text': '다음 질문', 'job_id': 'second'}]
        checkpoint = {'count': 1, 'digest': context_prefix_digest(records, 1),
                      'messages': [{'role': 'user', 'content': '요약', '_compressed_summary': True}]}
        def read_job(job_id):
            self.assertEqual(job_id, 'second')
            return {'status': {'status': 'completed'}, 'final_response': '다음 답변'}
        context = build_context_messages({'messages': records, 'context_checkpoint': checkpoint}, read_job)
        self.assertEqual(context, [*checkpoint['messages'], {'role': 'user', 'content': '다음 질문'},
                                   {'role': 'assistant', 'content': '다음 답변'}])
        with self.assertRaises(ValueError):
            build_context_messages({'messages': records}, lambda _: {'status': {'status': 'running'}})
        with self.assertRaises(ValueError):
            build_context_messages({'messages': records}, lambda _: {'status': {'status': 'completed'}, 'final_response_truncated': True})

    def test_commit_preserves_tail_and_rejects_stale_results(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HermesSessionStore(directory)
            session_id = 'a' * 32
            store.create_session_record(session_id)
            store.append_session_request(session_id, 'request_1', '첫 메시지')
            snapshot = store.read_session_record(session_id)['messages']
            checkpoint = {'count': 1, 'digest': context_prefix_digest(snapshot, 1),
                          'messages': [{'role': 'assistant', 'content': '요약'}]}
            store.append_session_request(session_id, 'request_2', '새 메시지')
            store.commit_context_checkpoint(session_id, checkpoint, None)
            result = store.read_session_record(session_id)
            self.assertEqual(len(result['messages']), 2)
            self.assertEqual(result['context_checkpoint'], checkpoint)
            next_checkpoint = make_context_checkpoint(result, [{'role': 'assistant', 'content': '새 요약'}])
            store.set_context_automatic(session_id, False)
            self.assertFalse(store.read_session_record(session_id)['context_automatic'])
            store.commit_context_checkpoint(session_id, next_checkpoint, checkpoint)
            with self.assertRaises(ValueError):
                store.commit_context_checkpoint(session_id, checkpoint, None)
            altered = dict(checkpoint, digest='0' * 64)
            with self.assertRaises(ValueError):
                store.commit_context_checkpoint(session_id, altered, next_checkpoint)


if __name__ == '__main__':
    unittest.main()
