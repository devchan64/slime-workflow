import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import resident_worker
from workflow.domains.hermes_agent.service import HermesServiceManager


class ResidentDflashTests(unittest.TestCase):
    def test_dflash_status_reads_session_settings_without_resident_lookup(self):
        with tempfile.TemporaryDirectory() as root:
            manager = HermesServiceManager(Path(root)/'jobs', Path(root)/'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            with patch.object(resident_worker, 'dflash_model_present', return_value=True), \
                 patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', side_effect=AssertionError('unexpected resident lookup')):
                self.assertEqual(manager.execute_hermes_command('hermes-dflash-status', {'session_id':session}),
                                 {'session_id':session,'enabled':False,'available':True})
                with self.assertRaises(ValueError):
                    manager.execute_hermes_command('hermes-dflash-status', {'session_id':session,'extra':True})

    def test_session_toggle_is_persistent_and_reversible(self):
        with tempfile.TemporaryDirectory() as root:
            manager = HermesServiceManager(Path(root)/'jobs', Path(root)/'sessions')
            session = 'a' * 32
            manager.execute_hermes_command('hermes-session-create', {'session_id':session})
            with patch('workflow.domains.hermes_agent.resident_queue.find_session_resident',return_value=None):
                def state():
                    return manager.execute_hermes_command('hermes-resident-status', {'session_id':session})['dflash_enabled']
                def save(enabled):
                    return manager.execute_hermes_command('hermes-resident-dflash', {'session_id':session, 'enabled':enabled})
                self.assertFalse(state())
                with patch.object(resident_worker,'DFLASH_MODEL',Path(root)/'missing'):
                    with self.assertRaises(ValueError):
                        save(True)
                self.assertFalse(state())
                with patch.object(resident_worker,'dflash_arguments',return_value=[]):
                    save(True)
                self.assertTrue(state())
                save(False)
                self.assertFalse(state())
                with self.assertRaises(ValueError):
                    save('false')

    def test_queue_retries_preserve_original_mode(self):
        from workflow.domains.hermes_agent.chat_queue_store import enqueue
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        with tempfile.TemporaryDirectory() as root:
            store = HermesSessionStore(Path(root))
            session = 'a' * 32
            store.create_session_record(session)
            store.set_dflash(session, True)
            first = enqueue(store, session, 'request_001', '확인', require_resident=True)
            store.set_dflash(session, False)
            retry = enqueue(store, session, 'request_001', '확인', require_resident=True)
            second = enqueue(store, session, 'request_002', '확인', require_resident=True)
            self.assertTrue(first['request']['dflash_enabled'])
            self.assertEqual(retry['request'], first['request'])
            self.assertFalse(second['request']['dflash_enabled'])

    def test_incomplete_download_cannot_enable_dflash(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'draft.gguf'
            with patch.object(resident_worker, 'DFLASH_MODEL', path):
                for candidate in (path.with_suffix('.gguf.part'), path):
                    candidate.write_bytes(b'partial')
                    self.assertFalse(resident_worker.dflash_model_present())
                    with self.assertRaises(ValueError):
                        resident_worker.dflash_arguments(True)
                    self.assertEqual(resident_worker.dflash_arguments(False), [])

    def test_launch_arguments_only_add_drafter_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'draft.gguf'
            with path.open('wb') as model_file:
                model_file.truncate(resident_worker.DFLASH_MODEL_BYTES)
            with patch.object(resident_worker,'DFLASH_MODEL',path), patch.object(resident_worker.worker,'calculate_file_digest',return_value=resident_worker.DFLASH_SHA256):
                self.assertEqual(resident_worker.dflash_arguments(False),[])
                args=resident_worker.dflash_arguments(True)
                self.assertIn('draft-dflash',args)
                self.assertEqual(args[args.index('--spec-draft-model')+1],str(path))
