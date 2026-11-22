import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import resident_preload as preload


class ResidentPreloadTests(unittest.TestCase):
    def test_only_idle_gpu_without_queue_starts_once_and_records_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'policy'
            queue = Path(tmp) / 'queue'
            queue.mkdir()
            with preload.locked_policy(root) as policy:
                preload.save_policy(policy, 'a' * 32, True)
            with patch('workflow.domains.hermes_agent.session_store.HermesSessionStore.read_session_record'), \
                 patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value=None), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted'}) as start, \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch('workflow.common.gpu_job_queue.GPU_QUEUE_DIRECTORY', queue), \
                 patch('workflow.common.gpu_status.read_gpu_status', return_value={'status':'busy','processes':[{}]}) as gpu:
                self.assertEqual(preload.preload_if_idle(root), 'busy')
                start.assert_not_called()
                gpu.return_value = {'status':'unavailable','processes':[]}
                self.assertEqual(preload.preload_if_idle(root), 'busy')
                start.assert_not_called()
                gpu.return_value = {'status':'idle','processes':[]}
                (queue / 'ticket.json').write_text('{}')
                self.assertEqual(preload.preload_if_idle(root), 'busy')
                (queue / 'ticket.json').unlink()
                (queue / 'active').mkdir()
                (queue / 'active' / 'ticket.json').write_text('{}')
                self.assertEqual(preload.preload_if_idle(root), 'busy')
                (queue / 'active' / 'ticket.json').unlink()
                self.assertEqual(preload.preload_if_idle(root), 'accepted')
                request = start.call_args.args[1]
                self.assertEqual(preload.preload_if_idle(root), 'accepted')
                self.assertEqual(start.call_args.args[1], request)
                with preload.locked_policy(root) as policy:
                    preload.save_policy(policy, 'a' * 32, False)
                self.assertEqual(preload.preload_if_idle(root), 'disabled')
                self.assertEqual(start.call_count, 2)

    def test_active_handoff_rejection_never_triggers_direct_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'policy'
            queue = Path(tmp) / 'queue'
            queue.mkdir()
            with preload.locked_policy(root) as policy:
                preload.save_policy(policy, 'a' * 32, True)
            with patch('workflow.domains.hermes_agent.session_store.HermesSessionStore.read_session_record'), \
                 patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value=None), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', side_effect=ValueError('GPU 양도 진행 중')), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch('workflow.common.gpu_job_queue.GPU_QUEUE_DIRECTORY', queue), \
                 patch('workflow.common.gpu_status.read_gpu_status', return_value={'status':'idle','processes':[]}):
                with self.assertRaisesRegex(ValueError, '양도'):
                    preload.preload_if_idle(root)

    def test_corrupt_policy_does_not_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'policy'
            with preload.locked_policy(root):
                (root / 'policy.json').write_text('{}')
            with self.assertRaises(ValueError):
                preload.preload_if_idle(root)

    def test_manual_release_disables_preload_and_explicit_start_reenables_it(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            with patch.object(preload, 'POLICY_ROOT', root / 'policy'), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}), \
                 patch('workflow.domains.hermes_agent.resident_queue.request_resident_release', return_value={'state':'requested'}), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore.run_without_open_session_handoff', side_effect=lambda session, action: action()):
                manager.execute_hermes_command('hermes-resident-start', {'session_id':session,'request_id':'request_123'})
                manager.execute_hermes_command('hermes-resident-release', {'session_id':session,'resident_id':'resident_123','confirmed':True})
                self.assertEqual(preload.preload_if_idle(root / 'policy'), 'disabled')
                manager.execute_hermes_command('hermes-resident-start', {'session_id':session,'request_id':'request_456'})
                with preload.locked_policy(root / 'policy') as policy:
                    self.assertTrue(preload.read_policy(policy)['enabled'])

if __name__ == '__main__':
    unittest.main()
