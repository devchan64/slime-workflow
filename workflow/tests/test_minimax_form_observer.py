import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from workflow.domains.hermes_agent.minimax_form_observer import read_session_minimax_forms
from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore


class MiniMaxFormObserverTests(unittest.TestCase):
    def test_multiple_forms_keep_their_own_proposal_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory)/'forms.sqlite3')
            session = 'a'*32
            first, second = '2026-11-24_22-01-26-b482d868', '2026-11-24_22-23-17-2a551ada'
            forms.create(session,'b'*32,'minimax-h3-image',first,{'prompt':'빨간 지붕','images':[]})
            forms.create(session,'c'*32,'minimax-h3-image',second,{'prompt':'파란 지붕','images':[]})
            result = read_session_minimax_forms(session,sessions=Mock(),forms=forms)
            by_id = {form['form_id']:form for form in result['forms']}
            self.assertEqual((by_id['b'*32]['source_job_id'],by_id['b'*32]['prompt']),(first,'빨간 지붕'))
            self.assertEqual((by_id['c'*32]['source_job_id'],by_id['c'*32]['prompt']),(second,'파란 지붕'))

    def test_scoped_summary_does_not_disclose_image_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            forms = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            session, other = 'a'*32, 'c'*32
            job = '2026-11-24_22-01-26-b482d868'
            forms.create(session, 'b'*32, 'minimax-h3-i2v', job, {'prompt':'장면', 'images':['private-image'], 'seed':42})
            forms.create(other, 'd'*32, 'minimax-h3-image', job, {'prompt':'다른 대화', 'images':[]})
            sessions = Mock()
            result = read_session_minimax_forms(session, sessions=sessions, forms=forms)
            self.assertEqual(len(result['forms']), 1)
            self.assertEqual(result['forms'][0]['source_job_id'], job)
            self.assertTrue(result['forms'][0]['reference_attached'])
            self.assertNotIn('private-image', str(result))
            self.assertNotIn('다른 대화', str(result))
            sessions.read_session_record.assert_called_with(session)

    def test_observer_reconciles_accepted_receipt_after_restart(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.flux_reports import proposal_request_id
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);forms=MiniMaxFormStore(root/'forms.sqlite3');receipts=HermesDelegationStore(root/'receipts')
            session,form='a'*32,'b'*32
            source='2026-11-24_22-01-26-b482d868';job='2026-11-24_22-23-17-2a551ada';service='minimax-h3-image'
            request={'prompt':'성당','images':[]}
            request_id=proposal_request_id(session,source,service)
            forms.create(session,form,service,source,request)
            forms.pin_submission(session,form,1,request_id)
            receipts.execute_service_delegation_once(request_id,service,request,lambda _: {'id':job},lambda _: None)
            result=read_session_minimax_forms(session,sessions=Mock(),forms=MiniMaxFormStore(root/'forms.sqlite3'),receipts=receipts)
            self.assertEqual((result['forms'][0]['state'],result['forms'][0]['job_id']),('accepted',job))


if __name__ == '__main__':
    unittest.main()
