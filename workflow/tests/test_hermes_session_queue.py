import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.session_queue import append_session_video_jobs


class SessionQueueTests(unittest.TestCase):
    def test_direct_receipts_and_workflow_deduplication(self):
        session = 'a' * 32
        forms = [{'form_id':c * 32,'created_at':'2026-11-21T09:00:00+00:00'} for c in '1234']
        payload = {'session_id':session,'category':'','state':'','search_filters':{}}
        result = {'steps':[{'source_job_id':'job-duplicate'}], 'truncated':False}
        # Forms are examined newest first.
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.session_queue.read_hermes_video_source_job',return_value={'status':'running','queried_at':'now'}):
            sessions.return_value.read_session_record.return_value={'messages':forms}
            receipts.return_value.read_service_delegation.side_effect=[{'state':'accepted','job_id':'job-live'}, {'state':'accepted','job_id':'job-duplicate'}, {'state':'unknown'}, {'state':'not_found'}]
            response=append_session_video_jobs(result,payload)
        self.assertEqual([(row['source_job_id'],row['state']) for row in response['direct_jobs']], [('job-live','running'),(None,'unknown')])
        self.assertEqual(response['steps'],result['steps'])

    def test_filters_and_failed_status_are_not_reported_as_running(self):
        payload={'session_id':'a'*32,'category':'motion','state':'unknown','search_filters':{}}
        result={'steps':[],'truncated':False}
        with patch('workflow.domains.hermes_agent.session_queue.HermesSessionStore') as sessions, \
             patch('workflow.domains.hermes_agent.session_queue.HermesDelegationStore') as receipts, \
             patch('workflow.domains.hermes_agent.session_queue.read_hermes_video_source_job',side_effect=OSError('unavailable')):
            sessions.return_value.read_session_record.return_value={'messages':[{'form_id':'b'*32,'created_at':'2026-11-21T09:00:00+00:00'}]}
            receipts.return_value.read_service_delegation.return_value={'state':'accepted','job_id':'job-live'}
            response=append_session_video_jobs(result,payload)
            self.assertEqual(response['direct_jobs'][0]['state'],'unknown')
            payload['category']='image'
            self.assertEqual(append_session_video_jobs(result,payload)['direct_jobs'],[])
