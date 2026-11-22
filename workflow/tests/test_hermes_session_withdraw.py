from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
import unittest

from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.chat_queue_store import enqueue


class SessionWithdrawTests(unittest.TestCase):
    def test_management_command_withdraws_and_rejects_invalid_fields(self):
        from pathlib import Path
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = HermesServiceManager(root / 'jobs', root / 'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            payload = {'session_id':session, 'request_id':'request_123'}
            self.assertEqual(manager.execute_hermes_command('hermes-session-withdraw-unsubmitted', payload)['state'], 'withdrawn')
            with self.assertRaises(ValueError):
                manager.execute_hermes_command('hermes-session-withdraw-unsubmitted', {**payload, 'extra':True})

    def test_withdraw_blocks_late_direct_and_queued_submissions(self):
        with TemporaryDirectory() as directory:
            store = HermesSessionStore(directory)
            session = 'a' * 32
            store.create_session_record(session)
            result = store.withdraw_unsubmitted_request(session, 'request_123')
            self.assertEqual(result['state'], 'withdrawn')
            self.assertEqual(store.withdraw_unsubmitted_request(session, 'request_123'), result)
            with self.assertRaisesRegex(ValueError, '철회'):
                store.append_session_request(session, 'request_123', 'hello')
            with self.assertRaisesRegex(ValueError, '철회'):
                enqueue(store, session, 'request_123', 'hello')

    def test_accepted_request_is_never_withdrawn(self):
        with TemporaryDirectory() as directory:
            store = HermesSessionStore(directory)
            session = 'a' * 32
            store.create_session_record(session)
            enqueue(store, session, 'request_123', 'hello')
            self.assertEqual(store.withdraw_unsubmitted_request(session, 'request_123')['state'], 'accepted')
            self.assertEqual(store.read_session_record(session)['chat_queue'][0]['state'], 'queued')

    def test_concurrent_submit_and_withdraw_are_exclusive(self):
        with TemporaryDirectory() as directory:
            store = HermesSessionStore(directory)
            session = 'a' * 32
            store.create_session_record(session)
            def submit():
                try:
                    enqueue(store, session, 'request_123', 'hello')
                    return 'accepted'
                except ValueError:
                    return 'withdrawn'
            with ThreadPoolExecutor(max_workers=2) as pool:
                submitted = pool.submit(submit)
                withdrawn = pool.submit(store.withdraw_unsubmitted_request, session, 'request_123')
                self.assertEqual(submitted.result(), withdrawn.result()['state'])
