import tempfile
import unittest
from pathlib import Path

from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore


class MiniMaxFormStoreTests(unittest.TestCase):
    def test_simultaneous_edit_and_submit_cannot_pin_old_edited_value(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        with tempfile.TemporaryDirectory() as directory:
            store = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            session, form = 'a'*32, 'b'*32
            source = '2026-11-24_22-01-26-b482d868'
            store.create(session, form, 'minimax-h3-image', source, {'prompt':'원래 입력'})
            barrier = threading.Barrier(2)
            def run(operation):
                barrier.wait()
                try:
                    return operation()
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                save = pool.submit(run, lambda:store.save(session,form,1,{'prompt':'수정 입력'}))
                pin = pool.submit(run, lambda:store.pin_submission(session,form,1,'request_123'))
                saved, pinned = save.result(), pin.result()
            self.assertNotEqual(saved is None, pinned is None)
            actual = store.read(session,form)
            if saved:
                self.assertEqual((actual['state'],actual['revision'],actual['request']['prompt']), ('editing',2,'수정 입력'))
            else:
                self.assertEqual((actual['state'],actual['revision'],actual['request']['prompt']), ('submitting',1,'원래 입력'))

    def test_revision_and_submission_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MiniMaxFormStore(Path(directory) / 'forms.sqlite3')
            session, form = 'a' * 32, 'b' * 32
            source = '2026-11-24_22-01-26-b482d868'
            created = store.create(session, form, 'minimax-h3-image', source, {'prompt':'집'})
            self.assertEqual(created['revision'], 1)
            self.assertEqual(store.list(session)[0]['form_id'], form)
            self.assertEqual(store.list('c' * 32), [])
            self.assertEqual(store.create(session, form, 'minimax-h3-image', source, {'prompt':'집'})['revision'], 1)
            updated = store.save(session, form, 1, {'prompt':'성당'})
            self.assertEqual(updated['revision'], 2)
            with self.assertRaises(ValueError): store.save(session, form, 1, {'prompt':'덮어쓰기'})
            pinned = store.pin_submission(session, form, 2, 'request_123')
            self.assertEqual(pinned['request'], {'prompt':'성당'})
            self.assertEqual(store.pin_submission(session, form, 2, 'request_123')['sha256'], pinned['sha256'])
            with self.assertRaises(ValueError): store.save(session, form, 2, {'prompt':'접수 후 변경'})
            with self.assertRaises(ValueError): store.pin_submission(session, form, 2, 'another_123')
            accepted = store.mark_accepted(session, form, 'request_123', source)
            self.assertEqual(accepted['state'], 'accepted')
            with self.assertRaises(ValueError): store.mark_accepted(session, form, 'request_123', '2026-11-24_22-01-26-aaaaaaaa')
            with self.assertRaises(ValueError): store.read('c' * 32, form)


if __name__ == '__main__':
    unittest.main()
