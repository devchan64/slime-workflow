import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import resident_worker
from workflow.domains.hermes_agent.service import HermesServiceManager


class ResidentDflashTests(unittest.TestCase):
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

    def test_launch_arguments_only_add_drafter_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'draft.gguf'
            path.touch()
            with patch.object(resident_worker,'DFLASH_MODEL',path), patch.object(resident_worker.worker,'calculate_file_digest',return_value=resident_worker.DFLASH_SHA256):
                self.assertEqual(resident_worker.dflash_arguments(False),[])
                args=resident_worker.dflash_arguments(True)
                self.assertIn('draft-dflash',args)
                self.assertEqual(args[args.index('--spec-draft-model')+1],str(path))
