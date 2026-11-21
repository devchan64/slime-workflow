import unittest

from workflow.domains.hermes_agent.model_residency_policy import decide_residency


class HermesModelResidencyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.values = dict(resident_profile='qwen3.5-4b', requested_profile=None, idle_seconds=5,
                           reservation_verified=True, server_healthy=True, memory_safe=True,
                           waiting_other_work=False)

    def test_idle_and_same_profile_request(self):
        self.assertEqual(decide_residency(**self.values).action, 'keep')
        self.assertEqual(decide_residency(**{**self.values, 'requested_profile':'qwen3.5-4b'}).action, 'reuse')

    def test_competition_unknowns_and_timeout_evict(self):
        for changes in ({'waiting_other_work':True}, {'waiting_other_work':None}, {'memory_safe':False},
                        {'reservation_verified':None}, {'server_healthy':False}, {'idle_seconds':60},
                        {'requested_profile':'qwen3.8-27b'}, {'shutdown':True}):
            with self.subTest(changes=changes):
                self.assertEqual(decide_residency(**{**self.values, **changes}).action, 'evict')

    def test_invalid_values_are_not_interpreted_as_safe(self):
        for changes in ({'idle_seconds':-1}, {'idle_limit_seconds':301}, {'memory_safe':1},
                        {'requested_profile':'unknown'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                decide_residency(**{**self.values, **changes})
