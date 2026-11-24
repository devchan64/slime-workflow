import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.chat_queue_store import enqueue,edit,update

class EditHoldTest(unittest.TestCase):
    def test_edit_holds_dispatch_until_save_or_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=HermesSessionStore(root/'sessions');session='a'*32;store.create_session_record(session)
            enqueue(store,session,'request_123','원래 내용');token='b'*32
            manager=HermesServiceManager(root/'jobs',root/'sessions')
            held=edit(store,session,'request_123',1,'begin',token)
            self.assertEqual(held['revision'],2)
            with patch('workflow.domains.hermes_agent.resident_queue.find_session_resident') as find:
                self.assertIsNone(manager.dispatch_chat_queue(session));find.assert_not_called()
            with self.assertRaises(ValueError): update(store,session,'request_123',2,prompt='다른 수정')
            with self.assertRaises(ValueError): edit(store,session,'request_123',2,'save','c'*32,prompt='다른 수정')
            saved=edit(store,session,'request_123',2,'save',token,prompt='수정 내용')
            self.assertNotIn('edit_token',saved);self.assertEqual(saved['prompt'],'수정 내용');self.assertEqual(saved['state'],'queued')
            held=edit(store,session,'request_123',3,'begin',token)
            released=edit(store,session,'request_123',4,'cancel',token)
            self.assertEqual(released['prompt'],'수정 내용');self.assertNotIn('edit_token',released)
