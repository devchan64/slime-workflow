import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.common import gpu_job_queue
from workflow.domains.hermes_agent.service import HermesServiceManager

class ResidentQueueSubmissionTest(unittest.TestCase):
    def test_missing_or_unknown_resident_preserves_idempotent_request(self):
        for status in (None, ValueError('unknown')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as root:
                manager=HermesServiceManager(Path(root)/'jobs',Path(root)/'sessions')
                session='a'*32
                with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',Path(root)/'gpu'), patch('workflow.domains.hermes_agent.resident_queue.find_session_resident',side_effect=status if isinstance(status,Exception) else None,return_value=None):
                    manager.execute_hermes_command('hermes-session-create',{'session_id':session})
                    payload={'session_id':session,'request_id':'request_12345678','prompt':'안녕'}
                    first=manager.execute_hermes_command('hermes-session-submit',payload)
                    again=manager.execute_hermes_command('hermes-session-submit',payload)
                    self.assertTrue(first['queued']);self.assertTrue(first['request']['require_resident']);self.assertTrue(again['duplicate'])
                    self.assertEqual(first['request']['request_id'],again['request']['request_id'])
                    self.assertTrue(manager.chat_queue_wakeup.is_set())

    def test_multiple_failures_recover_only_after_verified_cleanup(self):
        import json
        from contextlib import contextmanager
        from workflow.domains.hermes_agent.resident_queue import recover_clean_failed_residents, find_session_resident
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);residents=root/'residents';residents.mkdir();queue=root/'queue';queue.mkdir();active=queue/'active';active.mkdir();session='a'*32
            for name in ('failed_1','failed_2'):
                d=residents/name;d.mkdir()
                (d/'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':session}}))
                (d/'launch.json').write_text(json.dumps({'id':name,'state':'accepted'}))
                (d/'status.json').write_text(json.dumps({'status':'failed','exit_code':1}))
                (d/'execution.lock').touch()
            @contextmanager
            def held(): yield active
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',queue),patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock',held),patch('workflow.domains.hermes_agent.gpu_handoff_kimodo._gpu_idle_fresh',return_value=False):
                self.assertEqual(recover_clean_failed_residents(session,root=residents),0)
                with self.assertRaises(ValueError): find_session_resident(session,root=residents)
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',queue),patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock',held),patch('workflow.domains.hermes_agent.gpu_handoff_kimodo._gpu_idle_fresh',return_value=True):
                self.assertEqual(recover_clean_failed_residents(session,root=residents),2)
                self.assertIsNone(find_session_resident(session,root=residents))
                (residents/'failed_1'/'status.json').write_text(json.dumps({'status':'failed','exit_code':2}))
                with self.assertRaises(ValueError): find_session_resident(session,root=residents)
