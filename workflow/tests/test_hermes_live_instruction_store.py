import tempfile
import unittest
from pathlib import Path

from workflow.domains.hermes_agent.live_instruction_store import submit, transition
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class LiveInstructionStoreTests(unittest.TestCase):
    def test_receipt_idempotency_and_uncertain_delivery(self):
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a' * 32
            store.create_session_record(session)
            args = (store, session, 'instruction_1', '2026-11-22_00-05-05-d6a85e1b', 'steer', '간결하게 답해줘')
            self.assertEqual(submit(*args)['state'], 'pending')
            self.assertEqual(submit(*args)['state'], 'pending')
            with self.assertRaises(ValueError):
                submit(*args[:-1], '다른 지시')
            transition(store, session, 'instruction_1', 'pending', 'delivering')
            transition(store, session, 'instruction_1', 'delivering', 'unknown')
            with self.assertRaises(ValueError):
                transition(store, session, 'instruction_1', 'unknown', 'pending')
            recovered = HermesSessionStore(Path(root)).read_session_record(session)
            self.assertEqual(recovered['live_instructions'][0]['state'], 'unknown')
