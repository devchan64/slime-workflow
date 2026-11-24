import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.domains.hermes_agent.conversation_observation import conversation_observation

class ObservationTest(unittest.TestCase):
    def test_separates_verified_executor_model_and_event_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);job=root/'job';job.mkdir();resident=root/'resident_1';resident.mkdir();(resident/'server.log').write_text('log')
            (job/'request.json').write_text(json.dumps({'resident_id':'resident_1','context':{'session_id':'a'*32}}))
            (job/'hermes-events.jsonl').write_text(json.dumps({'type':'tool_result','timestamp':1700000000000})+'\n')
            with patch('workflow.domains.hermes_agent.resident_queue.RESIDENT_ROOT',root),patch('workflow.domains.hermes_agent.resident_queue.inspect_resident',return_value={'state':'ready'}),patch('workflow.domains.hermes_agent.resident_chat_executor.observe_resident_chat_status',return_value={'status':'running'}):
                actual=conversation_observation(job,{'status':'running'},'a'*32)
                self.assertEqual(actual['executor'],'verified');self.assertEqual(actual['model']['state'],'ready');self.assertIn('last_log_at',actual['model']);self.assertTrue(actual['last_event_at'].startswith('2023-11-14'))
                mismatch=conversation_observation(job,{'status':'running'},'b'*32)
                self.assertEqual(mismatch['executor'],'unknown');self.assertNotIn('last_log_at',mismatch['model'])
    def test_missing_data_does_not_claim_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            actual=conversation_observation(tmp,{'status':'running'},'a'*32)
            self.assertEqual(actual['executor'],'unknown');self.assertIsNone(actual['last_event_at']);self.assertEqual(actual['model']['state'],'unknown')

    def test_model_connection_observation_is_per_job_and_balanced(self):
        from workflow.domains.hermes_agent.resident_client import ModelRequestObservation
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'model-observation.json';monitor=ModelRequestObservation(path)
            monitor.change('start');monitor.change('start');monitor.change('response')
            recorded=json.loads(path.read_text());self.assertEqual(recorded['active'],2);self.assertIsNotNone(recorded['last_response_at'])
            monitor.change('end');monitor.change('end');recorded=json.loads(path.read_text())
            self.assertEqual(recorded['active'],0);self.assertIsNotNone(recorded['last_end_at']);self.assertNotIn('prompt',recorded)

    def test_token_signal_does_not_reuse_previous_model_task(self):
        from workflow.domains.hermes_agent.conversation_observation import model_token_signal
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'server.log'
            log.write_text('I slot print_timing: id 0 | task 42 | prompt processing, n_tokens = 256, progress = 0.50, t = 2.00 s / 128.00 tokens per second\n')
            self.assertEqual(model_token_signal(log)['input']['tokens_per_second'],128)
            with log.open('a') as stream: stream.write('I slot update: id 0 | task 43 | new prompt\n')
            self.assertEqual(model_token_signal(log),{})
