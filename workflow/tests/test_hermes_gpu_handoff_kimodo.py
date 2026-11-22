"""기존 접수 영수증과 양도 제어기의 연결을 GPU 작업 없이 확인한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff
from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter, _derived_id, inspect_kimodo_release
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore

JOB = '2026-11-22_12-00-00-12345678'
SESSION = 'a' * 32
PAYLOAD = {'prompt':'walk', 'frames':90}
DIGEST = hashlib.sha256(json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class KimodoHandoffTests(unittest.TestCase):
    def test_real_receipt_binds_input_and_survives_controller_restart(self):
        with TemporaryDirectory() as root:
            handoffs = GpuHandoffStore(Path(root) / 'handoffs')
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            handoffs.approve('request_123', SESSION, 'kimodo', DIGEST, target_request=PAYLOAD,
                             resident_id='resident_123', confirmed=True)
            submissions = []
            def gateway(command, payload):
                if command == 'hermes-delegate-kimodo':
                    return receipts.execute_delegation_once(payload['request_id'], {'service':'kimodo','request':payload['request']},
                        lambda request: (submissions.append(request) or {'id':JOB}))
                if command == 'hermes-delegation-job-status':
                    return {'receipt':{**receipts.read_delegation_status(payload['request_id']),'service':'kimodo'},
                            'job':{'id':JOB,'status':'completed'}}
                raise AssertionError(command)
            adapter = KimodoHandoffAdapter(gateway=gateway, delegation_store=receipts, resident_root=Path(root)/'residents',
                                          release_observer=lambda job, status: True)
            model_states = {'resident_123':'ready'}
            def inspect(identifier, session, **kwargs):
                state = model_states.get(identifier, 'not_found')
                return {'state':state, **({'model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True} if state == 'ready' else {})}
            def release(identifier, session, **kwargs):
                model_states[identifier] = 'released'
            def enqueue(identifier, session, **kwargs):
                model_states[identifier] = 'queued'
            with patch('workflow.domains.hermes_agent.gpu_handoff_kimodo.inspect_resident', side_effect=inspect), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_kimodo.request_resident_release', side_effect=release), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_kimodo.enqueue_resident_once', side_effect=enqueue):
                step = lambda: advance_gpu_handoff(handoffs, 'request_123', adapter)
                self.assertEqual(step()['state'], 'waiting_release')
                self.assertEqual(step()['state'], 'running')
                self.assertEqual(step()['state'], 'reload_queued')
                self.assertEqual(step()['state'], 'reloading')
                reload_id = _derived_id('reload_', 'request_123')
                self.assertEqual(step()['state'], 'reloading')
                model_states[reload_id] = 'ready'
                self.assertEqual(step()['state'], 'ready')
            self.assertEqual(submissions, [{'service':'kimodo','request':PAYLOAD}])
            record = handoffs.read('request_123')
            self.assertEqual(adapter.lookup_target(record)['job_id'], JOB)
            receipt_path = receipts.resolve_delegation_record_path(_derived_id('handoff_', 'request_123'))
            receipt = json.loads(receipt_path.read_text())
            receipt['request_sha256'] = '0' * 64
            receipt_path.write_text(json.dumps(receipt))
            self.assertEqual(adapter.lookup_target(record)['state'], 'unknown')

    def test_fresh_gpu_observation_must_be_well_formed_and_idle(self):
        from workflow.domains.hermes_agent.gpu_handoff_kimodo import _gpu_idle_fresh
        from types import SimpleNamespace
        for payload, expected in [
            ([{'process_list':[{'process_info':'No running processes detected'}]}], True),
            ([{'process_list':[{'process_info':{'pid':123}}]}], False),
            ([{}], None), ([], None),
        ]:
            with self.subTest(payload=payload), patch('workflow.domains.hermes_agent.gpu_handoff_kimodo.subprocess.run', return_value=SimpleNamespace(stdout=json.dumps(payload))):
                self.assertIs(_gpu_idle_fresh(), expected)

    def test_lost_gateway_response_recovers_existing_receipt_without_resubmission(self):
        with TemporaryDirectory() as root:
            handoffs = GpuHandoffStore(Path(root) / 'handoffs')
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            handoffs.approve('request_123', SESSION, 'kimodo', DIGEST, target_request=PAYLOAD,
                             resident_id='resident_123', confirmed=True)
            calls = []
            def gateway(command, payload):
                calls.append(command)
                receipts.execute_delegation_once(payload['request_id'], {'service':'kimodo','request':payload['request']}, lambda _: {'id':JOB})
                raise OSError('response lost')
            adapter = KimodoHandoffAdapter(gateway=gateway, delegation_store=receipts)
            with patch.object(adapter, 'ensure_release_requested'), patch.object(adapter, 'inspect_release', return_value='released'):
                advance_gpu_handoff(handoffs, 'request_123', adapter)
                with self.assertRaises(OSError):
                    advance_gpu_handoff(handoffs, 'request_123', adapter)
                self.assertEqual(handoffs.read('request_123')['state'], 'submitting')
                self.assertEqual(advance_gpu_handoff(GpuHandoffStore(Path(root) / 'handoffs'), 'request_123', adapter)['state'], 'running')
            self.assertEqual(calls, ['hermes-delegate-kimodo'])

    def test_release_waits_for_matching_job_reservation_to_disappear(self):
        from contextlib import nullcontext
        from workflow.common.generation_records import write_record_atomically
        with TemporaryDirectory() as root, TemporaryDirectory() as queue:
            directory = Path(root) / JOB
            directory.mkdir()
            write_record_atomically(directory / 'status.json', {'status':'completed'})
            reservation = Path(queue) / 'reservation.json'
            write_record_atomically(reservation, {'path':str(directory.resolve()), 'service':'image'})
            with patch('generators.kimodo.contracts.KIMODO_JOB_STORAGE', Path(root)), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_kimodo._gpu_idle_fresh', return_value=True), \
                 patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock', side_effect=lambda: nullcontext(Path(queue))):
                self.assertIs(inspect_kimodo_release(JOB, 'completed'), False)
                reservation.unlink()
                self.assertIs(inspect_kimodo_release(JOB, 'completed'), True)
                self.assertIsNone(inspect_kimodo_release(JOB, 'failed'))

    def test_scheduler_recovers_persisted_requests_and_skips_completed(self):
        from threading import Event
        from workflow.domains.hermes_agent.gpu_handoff_scheduler import run_gpu_handoff_scheduler
        with TemporaryDirectory() as root:
            store = GpuHandoffStore(root)
            store.approve('request_123', SESSION, 'kimodo', DIGEST, target_request=PAYLOAD,
                          resident_id='resident_123', confirmed=True)
            stop = Event()
            class OneCycle:
                def is_set(self): return stop.is_set()
                def wait(self, _seconds): stop.set()
            calls = []
            with patch('workflow.domains.hermes_agent.resident_preload.POLICY_ROOT', Path(root) / 'policy'), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_scheduler.advance_gpu_handoff', side_effect=lambda current_store, request_id, adapter: calls.append(request_id)):
                run_gpu_handoff_scheduler(GpuHandoffStore(root), object(), OneCycle())
            self.assertEqual(calls, ['request_123'])
            row = store.read('request_123')
            store.transition('request_123', row['revision'], 'cancelled')
            self.assertEqual(store.list_active_ids(), [])

    def test_scheduler_prioritizes_active_handoff_over_preload(self):
        from workflow.domains.hermes_agent.gpu_handoff_scheduler import run_gpu_handoff_scheduler
        class OneCycle:
            stopped = False
            def is_set(self): return self.stopped
            def wait(self, _seconds): self.stopped = True
        store = unittest.mock.Mock()
        store.list_active_ids.return_value = ['request_123']
        with patch('workflow.domains.hermes_agent.gpu_handoff_scheduler.advance_gpu_handoff') as advance, \
             patch('workflow.domains.hermes_agent.resident_preload.preload_if_idle') as preload:
            run_gpu_handoff_scheduler(store, object(), OneCycle())
        advance.assert_called_once()
        preload.assert_not_called()

    def test_confirmation_binds_session_resident_and_exact_generator_request(self):
        from workflow.domains.hermes_agent.gpu_handoff_operations import preview_kimodo_handoff, approve_kimodo_handoff
        request = {'action':'generate','prompt':'walk','frames':90,'steps':30,'seed':42,
                   'guidance_scale':5,'heading_degrees':0,'post_processing':True}
        class Sessions:
            def read_session_record(self, value):
                if value != SESSION: raise ValueError('세션 오류')
                return {'id':value}
        available = lambda identifier, session: {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
        reservations = lambda: {'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]}
        with TemporaryDirectory() as root:
            store = GpuHandoffStore(root)
            review = preview_kimodo_handoff(SESSION, 'resident_123', request, session_store=Sessions(), resident_inspector=available, reservation_snapshot=reservations)
            kwargs = {'store':store,'session_store':Sessions(),'resident_inspector':available,'reservation_snapshot':reservations,'resident_conflict_check':lambda _:None}
            with self.assertRaises(ValueError):
                approve_kimodo_handoff('request_123', SESSION, 'resident_123', request, review['review_hash'], confirmed=False, **kwargs)
            with self.assertRaises(ValueError):
                approve_kimodo_handoff('request_123', SESSION, 'resident_123', {**request,'seed':43}, review['review_hash'], confirmed=True, **kwargs)
            self.assertIsNone(store.read('request_123'))
            result = approve_kimodo_handoff('request_123', SESSION, 'resident_123', request, review['review_hash'], confirmed=True, **kwargs)
            self.assertEqual(result['state'], 'approved')
            # Once accepted, a lost response can be retried even if the resident has since been released.
            unavailable = lambda identifier, session: {'state':'released'}
            duplicate = approve_kimodo_handoff('request_123', SESSION, 'resident_123', request, review['review_hash'],
                confirmed=True, store=store, session_store=Sessions(), resident_inspector=unavailable)
            self.assertTrue(duplicate['duplicate'])
            conflicting = lambda: {'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]*2}
            with self.assertRaises(ValueError):
                preview_kimodo_handoff(SESSION, 'resident_123', request, session_store=Sessions(), resident_inspector=available, reservation_snapshot=conflicting)

    def test_management_command_requires_exact_fields_and_preserves_confirmation(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.common.management_gateway import resolve_management_command
        with TemporaryDirectory() as root:
            manager = HermesServiceManager(Path(root) / 'jobs', Path(root) / 'sessions')
            payload = {'request_id':'request_123','session_id':SESSION,'resident_id':'resident_123',
                       'request':PAYLOAD,'review_hash':'b'*64,'confirmed':False}
            with patch('workflow.domains.hermes_agent.gpu_handoff_operations.approve_kimodo_handoff', return_value={'state':'approved','target_request':PAYLOAD}) as approve:
                result = manager.execute_hermes_command('hermes-gpu-handoff-approve', payload)
                self.assertEqual(result, {'state':'approved'})
                self.assertIs(approve.call_args.kwargs['confirmed'], False)
                with self.assertRaises(ValueError):
                    manager.execute_hermes_command('hermes-gpu-handoff-approve', {**payload, 'extra':True})
            self.assertEqual(resolve_management_command('hermes-agent','hermes-gpu-handoff-approve', payload)[0], 'POST')

    def test_resident_start_requires_existing_session_and_valid_model(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with TemporaryDirectory() as root:
            manager = HermesServiceManager(Path(root) / 'jobs', Path(root) / 'sessions')
            manager.execute_hermes_command('hermes-session-create', {'session_id':SESSION})
            with patch('workflow.domains.hermes_agent.resident_preload.POLICY_ROOT', Path(root) / 'policy'), \
                 patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready') as ready, \
                 patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'}) as start:
                self.assertEqual(manager.execute_hermes_command('hermes-resident-start', {'session_id':SESSION,'request_id':'request_123'})['state'], 'accepted')
                ready.assert_called_once_with('qwen3.8-27b')
                start.assert_called_once_with(SESSION, 'request_123')
                with self.assertRaises(ValueError):
                    manager.execute_hermes_command('hermes-resident-start', {'session_id':SESSION,'request_id':'request_123','extra':True})


if __name__ == '__main__':
    unittest.main()
