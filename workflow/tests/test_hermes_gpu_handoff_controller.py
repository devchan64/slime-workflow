"""GPU나 생성기 없이 승인·불확실한 접수·재적재 상태 전이를 검증한다."""
from tempfile import TemporaryDirectory
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import fcntl
import hashlib
import json
from datetime import datetime, timedelta, timezone

from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff, recover_release_observation, recover_accepted_submission, recover_verified_reload, retry_failed_reload, cancel_handoff
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter


PAYLOAD = {'prompt': 'test'}
DIGEST = hashlib.sha256(json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class Adapter:
    def __init__(self):
        self.release = 'waiting'
        self.target = {'service':'flux-image','job_id':'2026-11-22_12-00-00-12345678','status':'running'}
        self.reload = {'state':'queued'}
        self.submissions = 0
        self.reloads = 0
        self.release_requests = 0
    def ensure_release_requested(self, record): self.release_requests += 1
    def inspect_release(self, record): return self.release
    def submit_target(self, record):
        self.submissions += 1
        return {'state':'accepted','service':record['service'],'input_digest':record['input_digest'],'job_id':self.target['job_id']}
    def lookup_target(self, record): return {'state':'unknown'}
    def inspect_target(self, record): return self.target
    def submit_reload(self, record): self.reloads += 1
    def inspect_reload(self, record): return self.reload
    def cancel_target(self, record): return {'job_id':record['job_id'],'cancel_requested':True}


class GpuHandoffControllerTests(unittest.TestCase):
    def test_retry_reload_persists_attempt_before_submission(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            row = store.transition(row['id'], row['revision'], 'submitting')
            row = store.transition(row['id'], row['revision'], 'running', job_id='2026-11-22_12-00-00-12345678')
            row = store.transition(row['id'], row['revision'], 'reload_queued', target_status='failed')
            row = store.transition(row['id'], row['revision'], 'reloading')
            row = store.transition(row['id'], row['revision'], 'needs_attention', reason='3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.')
            adapter = Adapter(); adapter.inspect_failed_reload_cleanup = lambda record: False
            with self.assertRaises(ValueError):
                retry_failed_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            adapter.inspect_failed_reload_cleanup = lambda record: True
            retried = retry_failed_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            self.assertEqual((retried['state'],retried['reload_retry']),('reload_queued',1))
            self.assertEqual(adapter.reloads,0)
            self.assertEqual(advance_gpu_handoff(GpuHandoffStore(directory),row['id'],adapter)['state'],'reloading')
            self.assertEqual(adapter.reloads,1)

    def test_failed_resident_cleanup_requires_unlocked_executor_and_no_reservation(self):
        from workflow.domains.hermes_agent.resident_queue import inspect_failed_resident_cleanup
        with TemporaryDirectory() as directory:
            root = Path(directory); residents = root / 'residents'; residents.mkdir()
            queue = root / 'queue'; queue.mkdir(); active = queue / 'active'; active.mkdir()
            job = residents / 'reload_123'; job.mkdir()
            (job/'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':'a'*32}}))
            (job/'launch.json').write_text(json.dumps({'id':'reload_123','state':'accepted'}))
            (job/'status.json').write_text(json.dumps({'status':'failed','exit_code':1}))
            (job/'execution.lock').touch()
            @contextmanager
            def held_queue():
                yield active
            with patch('workflow.common.gpu_job_queue.GPU_QUEUE_DIRECTORY',queue), patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock',held_queue):
                inspect = lambda: inspect_failed_resident_cleanup('reload_123','a'*32,root=residents,gpu_idle=lambda:True)
                self.assertTrue(inspect())
                with (job/'execution.lock').open('r') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    self.assertFalse(inspect())
                (active/'job.json').write_text(json.dumps({'path':str(job.resolve()),'service':'hermes-agent'}))
                self.assertFalse(inspect())
                (active/'job.json').unlink()
                (queue/'waiting.json').write_text(json.dumps({'path':str(job.resolve())}))
                self.assertFalse(inspect())
                (queue/'waiting.json').unlink()
                (active/'bad.json').write_text('{}')
                self.assertFalse(inspect())
                (active/'bad.json').unlink()
                self.assertFalse(inspect_failed_resident_cleanup('reload_123','a'*32,root=residents,gpu_idle=lambda:False))
                self.assertFalse(inspect_failed_resident_cleanup('reload_123','b'*32,root=residents,gpu_idle=lambda:True))
                (job/'status.json').write_text(json.dumps({'status':'running'}))
                self.assertFalse(inspect())

    def test_resident_retry_requires_explicit_verified_failed_attempt(self):
        from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once
        with TemporaryDirectory() as directory:
            root = Path(directory); residents = root/'residents'; residents.mkdir()
            queue = root/'queue'; queue.mkdir(); active = queue/'active'; active.mkdir()
            old = residents/'reload_old'; old.mkdir()
            (old/'request.json').write_text(json.dumps({'model_profile':'qwen3.8-27b','context':{'session_id':'a'*32}}))
            (old/'launch.json').write_text(json.dumps({'id':'reload_old','state':'accepted'}))
            (old/'status.json').write_text(json.dumps({'status':'failed','exit_code':1}))
            (old/'execution.lock').touch()
            @contextmanager
            def held_queue():
                yield active
            launches = []
            with patch('workflow.common.gpu_job_queue.GPU_QUEUE_DIRECTORY',queue), patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock',held_queue), patch('workflow.domains.hermes_agent.gpu_handoff_kimodo._gpu_idle_fresh',return_value=True):
                with self.assertRaises(ValueError):
                    enqueue_resident_once('reload_new','a'*32,root=residents,launcher=lambda *args,**kwargs:launches.append(args))
                with (old/'execution.lock').open('r') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaises(ValueError):
                        enqueue_resident_once('reload_new','a'*32,root=residents,recovered_failure_id='reload_old',launcher=lambda *args,**kwargs:launches.append(args))
                def verified_launcher(*args, **kwargs):
                    with (old/'execution.lock').open('r') as lock:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    launches.append(args)
                result = enqueue_resident_once('reload_new','a'*32,root=residents,recovered_failure_id='reload_old',launcher=verified_launcher)
                self.assertEqual(result['state'],'accepted')
                self.assertEqual(len(launches),1)
                self.assertTrue(enqueue_resident_once('reload_new','a'*32,root=residents,recovered_failure_id='reload_old',launcher=lambda *args,**kwargs:launches.append(args))['duplicate'])
                self.assertEqual(len(launches),1)
                (old/'recovery.json').unlink()
                self.assertTrue(enqueue_resident_once('reload_new','a'*32,root=residents,recovered_failure_id='reload_old',launcher=lambda *args,**kwargs:launches.append(args))['duplicate'])
                self.assertTrue((old/'recovery.json').exists())
                self.assertEqual(len(launches),1)
                from workflow.domains.hermes_agent.resident_queue import find_session_resident
                with patch('workflow.domains.hermes_agent.resident_queue.inspect_resident',side_effect=lambda identifier, session, **kwargs: {'state':'ready' if identifier == 'reload_new' else 'unknown'}):
                    self.assertEqual(find_session_resident('a'*32,root=residents),'reload_new')
                    (old/'recovery.json').write_text(json.dumps({'session_id':'b'*32,'failed_id':'reload_old','retry_id':'reload_new'}))
                    with self.assertRaises(ValueError):
                        find_session_resident('a'*32,root=residents)

    def test_recover_rejected_reload_requires_matching_rejection_receipt(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            row = store.transition(row['id'], row['revision'], 'submitting')
            row = store.transition(row['id'], row['revision'], 'rejected_reload_queued')
            row = store.transition(row['id'], row['revision'], 'rejected_reloading')
            row = store.transition(row['id'], row['revision'], 'needs_attention', reason='3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.')
            adapter = Adapter()
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            adapter.lookup_target = lambda record: {'state':'rejected','service':'flux-image','input_digest':'0'*64}
            with self.assertRaises(ValueError):
                recover_verified_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            adapter.lookup_target = lambda record: {'state':'rejected','service':'flux-image','input_digest':DIGEST}
            self.assertEqual(recover_verified_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)['state'],'rejected')
            self.assertEqual(adapter.reloads,0)

    def test_recover_reload_requires_existing_verified_model(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            row = store.transition(row['id'], row['revision'], 'submitting')
            row = store.transition(row['id'], row['revision'], 'running', job_id='2026-11-22_12-00-00-12345678')
            row = store.transition(row['id'], row['revision'], 'reload_queued', target_status='failed')
            row = store.transition(row['id'], row['revision'], 'reloading')
            row = store.transition(row['id'], row['revision'], 'needs_attention', reason='3.8 재적재 또는 GPU 예약을 확인할 수 없습니다.')
            adapter = Adapter()
            for result in ({'state':'unknown'}, {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':False}):
                adapter.reload = result
                with self.assertRaises(ValueError):
                    recover_verified_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            with self.assertRaises(ValueError):
                recover_verified_reload(store,row['id'],'b'*32,row['revision'],adapter,confirmed=True)
            result = recover_verified_reload(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            self.assertEqual(result['state'],'ready')
            self.assertEqual(result['target_status'],'failed')
            self.assertEqual(adapter.reloads,0)

    def test_failed_dispatch_seals_receipt_and_recovers_after_restart(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(Path(directory) / 'handoffs')
            delegation = HermesDelegationStore(Path(directory) / 'receipts')
            row = store.approve('request_123', 'a'*32, 'kimodo', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            store.transition(row['id'], row['revision'], 'submitting')
            def rejected_gateway(*args):
                raise ValueError('validation failed')
            adapter = KimodoHandoffAdapter(delegation_store=delegation, gateway=rejected_gateway)
            result = advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(result['state'], 'rejected_reload_queued')
            self.assertEqual(adapter.lookup_target(result)['state'], 'rejected')

    def test_sealed_unsubmitted_receipt_blocks_late_dispatch(self):
        for service, adapter_type in (('kimodo', KimodoHandoffAdapter), ('flux-image', FluxHandoffAdapter)):
            with self.subTest(service=service), TemporaryDirectory() as directory:
                delegation = HermesDelegationStore(directory)
                adapter = adapter_type(delegation_store=delegation)
                record = {'id':'request_123', 'service':service, 'target_request':PAYLOAD, 'input_digest':DIGEST}
                self.assertTrue(adapter.seal_unsubmitted_target(record))
                self.assertEqual(adapter.lookup_target(record)['state'], 'rejected')
                self.assertFalse(adapter.seal_unsubmitted_target(record))
                calls = []
                if service == 'kimodo':
                    from workflow.domains.hermes_agent.gpu_handoff_kimodo import _derived_id
                    receipt_id = _derived_id('handoff_', record['id'])
                    self.assertEqual(delegation.read_delegation_status(receipt_id)['state'], 'rejected')
                    self.assertEqual(delegation.list_delegation_receipts()['records'][0]['state'], 'rejected')
                    with self.assertRaises(ValueError):
                        delegation.execute_delegation_once(receipt_id, {'service':service, 'request':PAYLOAD}, lambda payload: calls.append(payload))
                else:
                    self.assertEqual(delegation.read_service_delegation(adapter.target_request_id(record), service)['state'], 'rejected')
                    self.assertEqual(delegation.list_service_delegations(service)['records'][0]['state'], 'rejected')
                    with self.assertRaises(ValueError):
                        delegation.execute_service_delegation_once(adapter.target_request_id(record), service, PAYLOAD, lambda payload: calls.append(payload), lambda payload: None)
                self.assertEqual(calls, [])

    def test_validation_rejection_blocks_late_submission(self):
        with TemporaryDirectory() as directory:
            store = HermesDelegationStore(directory)
            calls = []
            def reject(payload):
                raise ValueError('workspace changed')
            def submit(payload):
                calls.append(payload)
                return {'id':'2026-11-22_12-00-00-12345678'}
            result = store.execute_service_delegation_once('handoff_123', 'writer-agent', PAYLOAD, submit, reject, record_validation_rejection=True)
            self.assertEqual(result['state'], 'rejected')
            with self.assertRaises(ValueError):
                store.execute_service_delegation_once('handoff_123', 'writer-agent', PAYLOAD, submit, lambda payload: None)
            self.assertEqual(calls, [])

    def test_verified_rejection_reloads_after_restart_without_target(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            store.transition(row['id'], row['revision'], 'submitting')
            adapter = Adapter()
            adapter.lookup_target = lambda record: {'state':'rejected', 'service':'flux-image', 'input_digest':DIGEST}
            step = lambda: advance_gpu_handoff(GpuHandoffStore(directory), 'request_123', adapter)
            self.assertEqual(step()['state'], 'rejected_reload_queued')
            self.assertEqual(step()['state'], 'rejected_reloading')
            adapter.reload = {'state':'ready', 'model':'qwen3.8-27b', 'gpu_loaded':True, 'reservation_verified':True}
            self.assertEqual(step()['state'], 'rejected')
            self.assertEqual(adapter.submissions, 0)
            self.assertEqual(adapter.reloads, 1)

    def test_invalid_submission_requires_attention_without_reload(self):
        for restart in (False, True):
            with self.subTest(restart=restart), TemporaryDirectory() as directory:
                store = GpuHandoffStore(directory)
                row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
                row = store.transition(row['id'], row['revision'], 'waiting_release')
                if restart:
                    store.transition(row['id'], row['revision'], 'submitting')
                adapter = Adapter()
                adapter.release = 'released'
                adapter.lookup_target = lambda record: {'state': 'not_found'}
                def reject(record):
                    raise ValueError('workspace changed')
                adapter.submit_target = reject
                result = advance_gpu_handoff(store, 'request_123', adapter)
                self.assertEqual(result['state'], 'needs_attention')
                self.assertEqual(adapter.reloads, 0)
                # A ValueError can occur after the target was accepted. A later
                # matching receipt must remain recoverable without resubmission.
                adapter.lookup_target = lambda record: {'state':'accepted', 'service':'flux-image', 'input_digest':DIGEST, 'job_id':adapter.target['job_id']}
                recovered = recover_accepted_submission(store, result['id'], 'a'*32, result['revision'], adapter, confirmed=True)
                self.assertEqual(recovered['state'], 'running')
                self.assertEqual(recovered['job_id'], adapter.target['job_id'])
                self.assertEqual(adapter.submissions, 0)

    def test_uncertain_submission_recovers_only_verified_existing_receipt(self):
        with TemporaryDirectory() as directory:
            store=GpuHandoffStore(directory)
            row=store.approve('request_123','a'*32,'flux-image',DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)
            row=store.transition(row['id'],row['revision'],'waiting_release')
            row=store.transition(row['id'],row['revision'],'submitting')
            row=store.transition(row['id'],row['revision'],'needs_attention',reason='대상 접수 결과를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            adapter=Adapter()
            for receipt in ({'state':'not_found'}, {'state':'unknown'}, {'state':'accepted','service':'flux-image','input_digest':'0'*64,'job_id':adapter.target['job_id']}):
                adapter.lookup_target=lambda record, receipt=receipt:receipt
                with self.assertRaises(ValueError):
                    recover_accepted_submission(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            adapter.lookup_target=lambda record:{'state':'accepted','service':'flux-image','input_digest':DIGEST,'job_id':adapter.target['job_id']}
            with self.assertRaises(ValueError): recover_accepted_submission(store,row['id'],'a'*32,row['revision'],adapter,confirmed=False)
            with self.assertRaises(ValueError): recover_accepted_submission(store,row['id'],'b'*32,row['revision'],adapter,confirmed=True)
            restored=recover_accepted_submission(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            self.assertEqual(restored['state'],'running')
            self.assertEqual(restored['job_id'],adapter.target['job_id'])
            self.assertEqual(adapter.submissions,0)
            with self.assertRaises(ValueError): recover_accepted_submission(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)

    def test_restart_before_target_receipt_reuses_same_submission(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            store.transition(row['id'], row['revision'], 'submitting')
            adapter = Adapter()
            adapter.lookup_target = lambda record: {'state':'not_found'}
            result = advance_gpu_handoff(GpuHandoffStore(directory), 'request_123', adapter)
            self.assertEqual(result['state'], 'running')
            self.assertEqual(adapter.submissions, 1)
            self.assertEqual(result['job_id'], adapter.target['job_id'])

    def test_failed_target_reloads_only_after_gpu_release(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            step = lambda: advance_gpu_handoff(store, 'request_123', adapter)
            step(); step()
            adapter.target.update(status='failed', reservation_released=False)
            self.assertEqual(step()['state'], 'running')
            self.assertEqual(adapter.reloads, 0)
            adapter.target.update(reservation_released=True)
            row = step()
            self.assertEqual(row['state'], 'reload_queued')
            self.assertEqual(row['target_status'], 'failed')
            self.assertEqual(step()['state'], 'reloading')
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            self.assertEqual(step()['state'], 'ready')

    def test_waits_for_release_and_verified_target_before_reload(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter()
            step = lambda: advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(step()['state'], 'waiting_release')
            self.assertEqual(step()['state'], 'waiting_release')
            self.assertEqual(adapter.submissions, 0)
            self.assertEqual(adapter.release_requests, 1)
            adapter.release = 'released'
            self.assertEqual(step()['state'], 'running')
            self.assertEqual(step()['state'], 'running')
            adapter.target.update(status='completed', reservation_released=True)
            self.assertEqual(step()['state'], 'reload_queued')
            self.assertEqual(step()['state'], 'reloading')
            self.assertEqual(step()['state'], 'reloading')
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            self.assertEqual(step()['state'], 'ready')
            self.assertEqual((adapter.submissions, adapter.reloads), (1, 1))

    def test_lost_response_does_not_duplicate_submission(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            advance_gpu_handoff(store, 'request_123', adapter)
            def lost(record):
                adapter.submissions += 1
                raise OSError('response lost')
            adapter.submit_target = lost
            with self.assertRaises(OSError):
                advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(store.read('request_123')['state'], 'submitting')
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'needs_attention')
            self.assertEqual(adapter.submissions, 1)

    def test_concurrent_advancers_cannot_submit_twice(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            advance_gpu_handoff(store, 'request_123', adapter)
            entered, release = Event(), Event()
            original = adapter.submit_target
            def delayed(record):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('test timed out')
                return original(record)
            adapter.submit_target = delayed
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = pool.submit(advance_gpu_handoff, store, 'request_123', adapter)
                self.assertTrue(entered.wait(5))
                self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'in_progress')
                release.set()
                self.assertEqual(pending.result()['state'], 'running')
            self.assertEqual(adapter.submissions, 1)

    def test_waits_for_known_reservation_and_stops_if_unknown(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            advance_gpu_handoff(store, 'request_123', adapter)
            advance_gpu_handoff(store, 'request_123', adapter)
            adapter.target.update(status='completed', reservation_released=False)
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'running')
            adapter.target.update(reservation_released=None)
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'needs_attention')
            self.assertEqual(adapter.reloads, 0)

    def test_ready_requires_exact_model_and_verified_reservation(self):
        for reload_result in (
            {'state':'ready','model':'qwen3.5-4b','gpu_loaded':True,'reservation_verified':True},
            {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':False},
            {'state':'ready','model':'qwen3.8-27b','gpu_loaded':False,'reservation_verified':True},
        ):
            with self.subTest(reload_result=reload_result), TemporaryDirectory() as directory:
                store = GpuHandoffStore(directory)
                store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
                adapter = Adapter(); adapter.release = 'released'
                advance_gpu_handoff(store, 'request_123', adapter)
                advance_gpu_handoff(store, 'request_123', adapter)
                adapter.target.update(status='completed', reservation_released=True)
                advance_gpu_handoff(store, 'request_123', adapter)
                advance_gpu_handoff(store, 'request_123', adapter)
                adapter.reload = reload_result
                self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'needs_attention')

    def test_restart_before_reload_submission_recovers_with_same_request(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            advance_gpu_handoff(store, 'request_123', adapter)
            advance_gpu_handoff(store, 'request_123', adapter)
            adapter.target.update(status='completed', reservation_released=True)
            row = advance_gpu_handoff(store, 'request_123', adapter)
            store.transition(row['id'], row['revision'], 'reloading')
            adapter.reload = {'state':'not_found'}
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'reloading')
            self.assertEqual(adapter.reloads, 1)
            adapter.reload = {'state':'queued'}
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'reloading')
            self.assertEqual(adapter.reloads, 1)

    def test_transient_unknown_reload_is_rechecked_without_duplicate(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            row = store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            row = store.transition(row['id'], row['revision'], 'waiting_release')
            row = store.transition(row['id'], row['revision'], 'submitting')
            row = store.transition(row['id'], row['revision'], 'running', job_id='2026-11-22_12-00-00-12345678')
            row = store.transition(row['id'], row['revision'], 'reload_queued', target_status='completed')
            store.transition(row['id'], row['revision'], 'reloading')
            adapter = Adapter(); adapter.reload = {'state':'unknown'}
            row = advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(row['state'], 'reloading')
            self.assertIsNotNone(row['uncertain_since'])
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            self.assertEqual(advance_gpu_handoff(store, 'request_123', adapter)['state'], 'ready')
            self.assertEqual(adapter.reloads, 0)

    def test_release_observation_recovery_never_duplicates_existing_target(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter(); adapter.release = 'unknown'
            advance_gpu_handoff(store, 'request_123', adapter)
            row = advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(row['state'], 'waiting_release')
            path = Path(directory) / 'request_123.json'
            saved = json.loads(path.read_text())
            saved['uncertain_since'] = (datetime.now(timezone.utc)-timedelta(seconds=35)).isoformat()
            path.write_text(json.dumps(saved))
            row = advance_gpu_handoff(store, 'request_123', adapter)
            self.assertEqual(row['state'], 'needs_attention')
            adapter.release = 'released'
            with self.assertRaises(ValueError):
                recover_release_observation(store, row['id'], 'a'*32, row['revision'], adapter, confirmed=True)
            adapter.lookup_target = lambda record: {'state':'not_found'}
            with self.assertRaises(ValueError):
                recover_release_observation(store, row['id'], 'a'*32, row['revision'], adapter, confirmed=False)
            recovered = recover_release_observation(store, row['id'], 'a'*32, row['revision'], adapter, confirmed=True)
            self.assertEqual(recovered['state'], 'waiting_release')
            self.assertEqual(advance_gpu_handoff(store, row['id'], adapter)['state'], 'running')
            self.assertEqual(adapter.submissions, 1)

    def test_cancel_before_submission_restores_model_without_generating(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123', 'a'*32, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            adapter = Adapter()
            row = advance_gpu_handoff(store, 'request_123', adapter)
            with self.assertRaises(ValueError):
                cancel_handoff(store,row['id'],'a'*32,row['revision'],adapter,confirmed=False)
            row = cancel_handoff(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            self.assertEqual(row['state'], 'cancel_waiting_release')
            adapter.release = 'released'
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'cancel_reload_queued')
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'cancel_reloading')
            adapter.reload = {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'cancelled')
            self.assertEqual((adapter.submissions,adapter.reloads), (0,1))

    def test_cancel_running_target_waits_for_actual_exit_and_reload(self):
        with TemporaryDirectory() as directory:
            store = GpuHandoffStore(directory)
            store.approve('request_123','a'*32,'flux-image',DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)
            adapter = Adapter(); adapter.release = 'released'
            advance_gpu_handoff(store,'request_123',adapter)
            row = advance_gpu_handoff(store,'request_123',adapter)
            result = cancel_handoff(store,row['id'],'a'*32,row['revision'],adapter,confirmed=True)
            self.assertTrue(result['cancel_requested'])
            self.assertEqual((result['id'],result['session_id'],result['service']),(row['id'],'a'*32,'flux-image'))
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'running')
            adapter.target.update(status='paused')
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'running')
            adapter.target.update(status='cancelled', reservation_released=True)
            self.assertEqual(advance_gpu_handoff(store,row['id'],adapter)['state'], 'reload_queued')


if __name__ == '__main__':
    unittest.main()
