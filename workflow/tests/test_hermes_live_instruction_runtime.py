import unittest
from workflow.domains.hermes_agent.live_instruction_runtime import LiveInstructionRuntime


class Agent:
    def __init__(self):
        self.calls = []
        self.delivered = False
        self._steer_ticket_fates = {}
    def steer(self, text, ticket=None):
        self.calls.append((text, ticket))
        return True
    def redirect(self, text):
        self.calls.append(text)
        return True
    def withdraw_steer(self, ticket):
        return not self.delivered


class LiveInstructionRuntimeTests(unittest.TestCase):
    def test_duplicate_and_unread_recovery(self):
        agent = Agent()
        runtime = LiveInstructionRuntime(agent)
        self.assertEqual(runtime.submit('request_01', 'steer', '추가')['state'], 'accepted')
        self.assertEqual(runtime.submit('request_01', 'steer', '추가')['state'], 'accepted')
        self.assertEqual(len(agent.calls), 1)
        with self.assertRaises(ValueError):
            runtime.submit('request_01', 'steer', '다른 요청')
        self.assertEqual(runtime.close()[0]['state'], 'undelivered')
        self.assertEqual(runtime.submit('request_02', 'redirect', '수정')['state'], 'undelivered')

    def test_observed_user_message_marks_only_matching_receipt_applied(self):
        runtime = LiveInstructionRuntime(Agent())
        runtime.submit('request_01', 'steer', '추가')
        runtime.submit('request_02', 'redirect', '수정')
        rows = runtime.observe([{'role':'user','content':'추가\n[지시 접수 ID: request_01]'}])
        self.assertEqual([row['state'] for row in rows], ['applied', 'accepted'])

    def test_consumed_steer_and_redirect_uncertainty(self):
        agent = Agent()
        runtime = LiveInstructionRuntime(agent)
        runtime.submit('request_01', 'steer', '추가')
        runtime.submit('request_02', 'redirect', '수정')
        agent.delivered = True
        agent._steer_ticket_fates['request_01'] = True
        result = {'messages':[{'role':'user','content':'수정\n[지시 접수 ID: request_02]'}]}
        self.assertEqual([row['state'] for row in runtime.close(result)], ['applied', 'applied'])

    def test_runtime_exception_has_unknown_outcome(self):
        class Ambiguous(Agent):
            def redirect(self, text):
                self.calls.append(text)
                raise OSError('connection lost after processing')
        agent = Ambiguous()
        runtime = LiveInstructionRuntime(agent)
        self.assertEqual(runtime.submit('request_01', 'redirect', '수정')['state'], 'unknown')
        self.assertEqual(runtime.submit('request_01', 'redirect', '수정')['state'], 'unknown')
        self.assertEqual(len(agent.calls), 1)
