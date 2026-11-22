"""GPU 양도 기록은 승인과 대상 종료를 확인하기 전 자동 진행하지 않는다."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import hashlib
import json

from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore


PAYLOAD = {'prompt': 'test'}
DIGEST = hashlib.sha256(json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class GpuHandoffStoreTests(unittest.TestCase):
    def test_withdraw_blocks_late_approval_and_never_cancels_accepted_work(self):
        with TemporaryDirectory() as directory:
            store=GpuHandoffStore(directory)
            withdrawn=store.withdraw_if_unaccepted('request_123','a'*32,'flux-image')
            self.assertEqual(withdrawn['state'],'withdrawn')
            self.assertEqual(store.read_withdrawal('request_123','a'*32),withdrawn)
            with self.assertRaises(ValueError): store.read_withdrawal('request_123','b'*32)
            self.assertEqual(store.withdraw_if_unaccepted('request_123','a'*32,'flux-image'),withdrawn)
            with self.assertRaises(ValueError): store.withdraw_if_unaccepted('request_123','b'*32,'flux-image')
            with self.assertRaises(ValueError):
                store.approve('request_123','a'*32,'flux-image',DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)
            row=store.approve('request_456','a'*32,'flux-image',DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)
            self.assertEqual(store.withdraw_if_unaccepted('request_456','a'*32,'flux-image')['state'],row['state'])
            self.assertEqual(store.read('request_456')['state'],'approved')
            with self.assertRaises(ValueError): store.withdraw_if_unaccepted('request_456','b'*32,'flux-image')

    def test_withdraw_and_approval_are_serialized(self):
        with TemporaryDirectory() as directory:
            store=GpuHandoffStore(directory)
            def approve():
                try:return store.approve('request_123','a'*32,'flux-image',DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)['state']
                except ValueError:return 'rejected'
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(approve)
                second=pool.submit(store.withdraw_if_unaccepted,'request_123','a'*32,'flux-image')
                approved,withdrawn=first.result(),second.result()['state']
            self.assertIn((approved,withdrawn),[('approved','approved'),('rejected','withdrawn')])

    def test_session_history_is_scoped_and_omits_input_payload(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            store.approve('request_456', 'b'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_456', confirmed=True)
            rows = store.list_session_records('a'*32)
            self.assertEqual([row['id'] for row in rows], ['request_123'])
            self.assertNotIn('target_request', rows[0])
            self.assertEqual(rows[0]['target_summary']['prompt'], 'test')
            with self.assertRaises(ValueError): store.list_session_records('invalid')
            with self.assertRaises(ValueError): store.list_session_records('a'*32, 0)

    def test_other_session_cleanup_can_run_while_handoff_is_open(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            self.assertEqual(store.run_without_open_session_handoff('b'*32, lambda:'released'), 'released')
            with self.assertRaises(ValueError):
                store.run_without_open_session_handoff('a'*32, lambda:'released')
            with self.assertRaises(ValueError):
                store.run_without_open_session_handoff('b'*32, lambda:'started', all_sessions=True)

    def test_concurrent_different_requests_for_resident_are_exclusive(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            def approve(index):
                try:
                    return store.approve('request_'+str(index), 'a'*32, ('flux-image' if index == 0 else 'wan22-vace'), DIGEST,
                                         target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                rows = list(pool.map(approve, range(2)))
            self.assertEqual(sum(row is not None for row in rows), 1)
            row = next(row for row in rows if row)
            row = store.transition(row['id'], row['revision'], 'needs_attention', reason='확인 필요')
            with self.assertRaisesRegex(ValueError, '미완료'):
                store.approve('request_789', 'a'*32, 'kimodo', DIGEST, target_request=PAYLOAD, resident_id='resident_456', confirmed=True)

    def test_confirmation_idempotency_and_binding(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            args = ('request_123', 'a' * 32, 'flux-image', DIGEST)
            with self.assertRaises(ValueError):
                store.approve(*args, target_request=PAYLOAD, resident_id='resident_123', confirmed=False)
            self.assertIsNone(store.read(args[0]))
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: store.approve(*args, target_request=PAYLOAD, resident_id='resident_123', confirmed=True), range(4)))
            self.assertEqual(sum(not value['duplicate'] for value in results), 1)
            with self.assertRaises(ValueError):
                store.approve(*args[:-1], 'c' * 64, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            with self.assertRaisesRegex(ValueError, '미완료'):
                store.approve('request_456', *args[1:], target_request=PAYLOAD, resident_id='resident_123', confirmed=True)

    def test_requires_verified_terminal_state_before_reload(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a' * 32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            with self.assertRaises(ValueError):
                store.transition(row['id'], row['revision'], 'reload_queued', target_status='completed')
            row = store.transition(row['id'], row['revision'], 'submitting')
            with self.assertRaises(ValueError):
                store.transition(row['id'], row['revision'], 'running')
            row = store.transition(row['id'], row['revision'], 'running', job_id='2026-11-22_12-00-00-12345678')
            with self.assertRaises(ValueError):
                store.transition(row['id'], row['revision'], 'reload_queued', target_status='unknown')
            row = store.transition(row['id'], row['revision'], 'reload_queued', target_status='failed')
            row = store.transition(row['id'], row['revision'], 'reloading')
            row = store.transition(row['id'], row['revision'], 'ready')
            self.assertEqual(store.read(row['id'])['target_status'], 'failed')

    def test_stale_revision_and_ambiguous_submission_fail_closed(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a' * 32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            current = store.transition(row['id'], row['revision'], 'waiting_release')
            with self.assertRaises(ValueError):
                store.transition(row['id'], row['revision'], 'cancelled')
            current = store.transition(row['id'], current['revision'], 'submitting')
            current = store.transition(row['id'], current['revision'], 'needs_attention', reason='접수 여부 확인 불가')
            with self.assertRaises(ValueError):
                store.transition(row['id'], current['revision'], 'running', job_id='2026-11-22_12-00-00-12345678')
            self.assertEqual(store.read(row['id'])['state'], 'needs_attention')

    def test_persists_verified_input_and_resident_for_restart(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            payload = dict(PAYLOAD)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST,
                          target_request=payload, resident_id='resident_123', confirmed=True)
            payload['prompt'] = 'changed'
            saved = GpuHandoffStore(directory).read('request_123')
            self.assertEqual(saved['target_request'], PAYLOAD)
            self.assertEqual(saved['resident_id'], 'resident_123')
            with self.assertRaises(ValueError):
                store.approve('request_123', 'a'*32, 'flux-image', DIGEST,
                              target_request=PAYLOAD, resident_id='resident_456', confirmed=True)
            path = Path(directory) / 'request_123.json'
            record = json.loads(path.read_text())
            record['target_request']['prompt'] = 'tampered'
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                store.read('request_123')

    def test_reference_sized_input_survives_restart(self):
        with TemporaryDirectory() as directory:
            payload = {'proportion_images':['a' * 1200000]}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'kimodo', digest, target_request=payload,
                          resident_id='resident_123', confirmed=True)
            self.assertEqual(GpuHandoffStore(directory).read('request_123')['target_request'], payload)


if __name__ == '__main__':
    unittest.main()
