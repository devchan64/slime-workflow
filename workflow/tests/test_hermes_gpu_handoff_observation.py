"""GPU 예약을 확인할 수 없으면 모델 해제를 확인했다고 판단하지 않는다."""
import unittest

from workflow.domains.hermes_agent.gpu_handoff_observation import classify_hermes_release


class GpuHandoffObservationTests(unittest.TestCase):
    def test_release_requires_terminal_38_and_unambiguous_idle_snapshot(self):
        job = {'model_profile':'qwen3.8-27b','status':'completed'}
        reservations = {'status':'available','truncated':False,'records':[]}
        gpu = {'status':'idle','process_count':0}
        self.assertEqual(classify_hermes_release(job, reservations, gpu), 'released')
        self.assertEqual(classify_hermes_release({**job,'status':'running'}, reservations, gpu), 'waiting')
        self.assertEqual(classify_hermes_release({**job,'model_profile':'qwen3.5-4b'}, reservations, gpu), 'unknown')
        self.assertEqual(classify_hermes_release(job, {**reservations,'truncated':True}, gpu), 'unknown')
        self.assertEqual(classify_hermes_release(job, {**reservations,'records':[{'state':'unknown'}]}, gpu), 'unknown')
        self.assertEqual(classify_hermes_release(job, {**reservations,'records':[{'state':'recorded','service':'hermes-agent'}]}, gpu), 'waiting')
        self.assertEqual(classify_hermes_release(job, reservations, {'status':'busy','process_count':1}), 'waiting')
        self.assertEqual(classify_hermes_release(job, reservations, {'status':'idle','process_count':1}), 'unknown')


if __name__ == '__main__':
    unittest.main()
