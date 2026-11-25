import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent.context_runtime import prepare_context_request

class Summary:
    _last_summary_error = None
    calls = []
    def __init__(self, **kwargs): pass
    def _generate_summary(self, prefix):
        self.calls.append(prefix)
        return '핵심 요약: 이전 요구와 정정'

class ContextBudgetTest(unittest.TestCase):
    def setUp(self):
        Summary.calls = []
        self.tail = [{'role':'user','content':'최근 사용자 정정'}, {'role':'assistant','content':'최근 응답'}]
        self.result = {'state':'compressed','messages':[{'role':'user','content':'과거 요구'}, {'role':'assistant','content':'첫 요약'}, *self.tail], 'tokens':100,'threshold':50}
    def prepare(self, counter, compressor=Summary):
        with patch('workflow.domains.hermes_agent.context_runtime.compress_context',return_value=self.result):
            return prepare_context_request([{'role':'user','content':'원문'}], '현재 요청', counter, 'local', compressor_factory=compressor)
    def test_rejects_protected_input_before_model_summary(self):
        counts = iter([30000, 24100])
        with patch('workflow.domains.hermes_agent.context_runtime.compress_context') as compress:
            with self.assertRaisesRegex(RuntimeError, '24,100'):
                prepare_context_request(self.tail, '현재 요청', lambda _: next(counts), 'local')
            compress.assert_not_called()

    def test_over_budget_summarizes_prefix_and_preserves_tail_and_query(self):
        counts=iter([100,70,20,35])
        result=self.prepare(lambda q: next(counts))
        self.assertEqual(result['tokens_after'],35)
        self.assertEqual(result['messages'][-2:],self.tail)
        self.assertTrue(result['messages'][0]['_compressed_summary'])
        self.assertEqual(Summary.calls[0],self.result['messages'][:-2])
        self.assertIn('현재 요청',result['query'])
    def test_protected_tail_too_large_fails_without_summary(self):
        counts=iter([100,70,51])
        with self.assertRaisesRegex(RuntimeError,'최근 대화와 현재 요청'):
            self.prepare(lambda q: next(counts))
        self.assertEqual(Summary.calls,[])
    def test_summary_failure_and_still_over_budget_fail(self):
        class Bad(Summary):
            def _generate_summary(self, prefix): return None
        counts=iter([100,70,20])
        with self.assertRaisesRegex(RuntimeError,'추가 대화 요약에 실패'):
            self.prepare(lambda q: next(counts),Bad)
        counts=iter([100,70,20,51])
        with self.assertRaisesRegex(RuntimeError,'추가 요약 후에도'):
            self.prepare(lambda q: next(counts))
    def test_long_prefix_is_split_without_dropping_text(self):
        text = '앞' * 6100 + '뒤' * 1100
        self.result['messages'] = [{'role':'user', 'content':text}, *self.tail]
        counts = iter([100,70,20,35])
        self.prepare(lambda q: next(counts))
        chunks = Summary.calls[0]
        self.assertTrue(all(len(item['content']) <= 5000 for item in chunks))
        self.assertEqual(''.join(item['content'] for item in chunks), text)

    def test_no_safe_window_and_oversized_prefix_are_rejected(self):
        self.result['messages'] = self.tail
        counts = iter([100,70])
        with self.assertRaisesRegex(RuntimeError, '추가 요약할 범위가 없습니다'):
            self.prepare(lambda q: next(counts))
        self.result['messages'] = [{'role':'user','content':'가' * 100001}, *self.tail]
        counts = iter([100,70,20])
        with self.assertRaisesRegex(RuntimeError, '추가 요약 범위가 너무 큽니다'):
            self.prepare(lambda q: next(counts))
        self.assertEqual(Summary.calls, [])

    def test_unchanged_oversized_context_is_not_accepted(self):
        self.result['state'] = 'unchanged'
        with self.assertRaisesRegex(RuntimeError, '정리 가능한 대화 범위가 없어'):
            self.prepare(lambda q: 100)

    def test_within_budget_does_not_repeat_summary(self):
        counts=iter([100,50])
        result=self.prepare(lambda q: next(counts))
        self.assertEqual(result['tokens_after'],50)
        self.assertEqual(Summary.calls,[])

if __name__ == '__main__': unittest.main()
