import json
import multiprocessing
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from workflow.common.generation_records import write_record_atomically
from workflow.common.gpu_memory_history import identify_execution_command
from workflow.domains.hermes_agent.resident_worker import _release_requested, _run_proxy, run_resident_worker
from workflow.domains.hermes_agent.resident_queue import enqueue_resident_once, request_resident_release, inspect_resident, hold_verified_resident_lease, find_session_resident, ensure_session_resident
from workflow.domains.hermes_agent.resident_client import connect_resident_socket, hold_resident_lease
from workflow.domains.hermes_agent.worker import wait_worker_model_ready


class _LiveServer:
    pid = 12345

    def poll(self):
        return None


def _run_test_proxy(port, directory, token):
    _run_proxy(_LiveServer(), port, Path(directory), token, 'offloaded 1/1 layers to GPU')


class HermesResidentWorkerTests(unittest.TestCase):
    def test_release_requires_exact_token_and_normal_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'release.request'
            token = 'a' * 32
            self.assertFalse(_release_requested(path, token))
            write_record_atomically(path, {'token': 'b' * 32})
            self.assertFalse(_release_requested(path, token))
            write_record_atomically(path, {'token': token, 'extra': True})
            self.assertFalse(_release_requested(path, token))
            write_record_atomically(path, {'token': token})
            self.assertTrue(_release_requested(path, token))
            target = Path(root) / 'link'
            target.symlink_to(path)
            self.assertFalse(_release_requested(target, token))

    def test_release_drains_existing_proxy_connection(self):
        with tempfile.TemporaryDirectory() as root, socket.socket() as backend:
            backend.bind(('127.0.0.1', 0))
            backend.listen()
            def echo():
                connection, _ = backend.accept()
                with connection:
                    while data := connection.recv(1024):
                        connection.sendall(data)
            backend_thread = threading.Thread(target=echo, daemon=True)
            backend_thread.start()
            token = 'a' * 32
            process = multiprocessing.Process(target=_run_test_proxy, args=(backend.getsockname()[1], root, token))
            process.start()
            try:
                status = Path(root) / 'resident-status.json'
                deadline = time.monotonic() + 5
                while not status.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(json.loads(status.read_text())['status'], 'ready')
                with socket.socket(socket.AF_UNIX) as client:
                    client.settimeout(3)
                    client.connect(str(Path(root) / 'resident-model.sock'))
                    client.sendall(b'before')
                    self.assertEqual(client.recv(1024), b'before')
                    write_record_atomically(Path(root) / 'release.request', {'token':token})
                    deadline = time.monotonic() + 5
                    while json.loads(status.read_text())['status'] != 'draining' and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertEqual(json.loads(status.read_text())['status'], 'draining')
                    self.assertTrue(process.is_alive())
                    client.sendall(b'after')
                    self.assertEqual(client.recv(1024), b'after')
                process.join(5)
                self.assertEqual(process.exitcode, 0)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(5)

    def test_lease_keeps_model_available_for_whole_chat_when_draining(self):
        with tempfile.TemporaryDirectory() as root, socket.socket() as backend:
            directory = Path(root) / ('long-path-' * 12)
            directory.mkdir()
            backend.bind(('127.0.0.1', 0))
            backend.listen()
            def echo():
                connection, _ = backend.accept()
                with connection:
                    while data := connection.recv(1024):
                        connection.sendall(data)
            threading.Thread(target=echo, daemon=True).start()
            token = 'b' * 32
            process = multiprocessing.Process(target=_run_test_proxy, args=(backend.getsockname()[1], str(directory), token))
            process.start()
            try:
                status = directory / 'resident-status.json'
                deadline = time.monotonic() + 5
                while not status.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(json.loads(status.read_text())['status'], 'ready')
                with hold_resident_lease(directory):
                    write_record_atomically(directory / 'release.request', {'token':token})
                    deadline = time.monotonic() + 5
                    while json.loads(status.read_text())['status'] != 'draining' and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertEqual(json.loads(status.read_text())['status'], 'draining')
                    self.assertTrue(process.is_alive())
                    with self.assertRaises(OSError):
                        with hold_resident_lease(directory):
                            pass
                    with connect_resident_socket(directory, 'resident-model.sock') as client:
                        client.sendall(b'inference')
                        self.assertEqual(client.recv(1024), b'inference')
                process.join(5)
                self.assertEqual(process.exitcode, 0)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(5)

    def test_resident_uses_qwen_38_memory_floor_identity(self):
        with tempfile.TemporaryDirectory() as root:
            write_record_atomically(Path(root) / 'request.json', {'model_profile':'qwen3.8-27b'})
            self.assertEqual(identify_execution_command(['python', '/x/hermes_agent/resident_worker.py'], root, 'vram'), 'hermes:qwen3.8-27b:vram')

    def test_queue_submission_is_idempotent_and_binds_session(self):
        with tempfile.TemporaryDirectory() as root:
            calls = []
            def launch(*args, **kwargs):
                calls.append((args, kwargs))
            first = enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=launch)
            second = enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=launch)
            self.assertEqual(first['state'], 'accepted')
            self.assertTrue(second['duplicate'])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0][2], 'hermes-agent')
            with self.assertRaises(ValueError):
                enqueue_resident_once('handoff_123', 'b'*32, root=root, launcher=launch)

    def test_uncertain_launch_is_never_retried(self):
        with tempfile.TemporaryDirectory() as root:
            calls = []
            def lost(*args, **kwargs):
                calls.append(1)
                raise OSError('launch result lost')
            with self.assertRaises(OSError):
                enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=lost)
            result = enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=lost)
            self.assertEqual(result['state'], 'unknown')
            self.assertEqual(len(calls), 1)

    def test_zero_gpu_layers_is_not_a_ready_model(self):
        from io import BytesIO
        with tempfile.TemporaryDirectory() as root:
            log = Path(root) / 'server.log'
            log.write_text('offloaded 0/0 layers to GPU')
            with patch('workflow.domains.hermes_agent.worker.urllib.request.urlopen', return_value=BytesIO(b'{"status":"ok"}')):
                with self.assertRaises(RuntimeError):
                    wait_worker_model_ready(_LiveServer(), 1, log)

    def test_missing_rocm_device_fails_before_loading_model(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as root:
            write_record_atomically(Path(root) / 'request.json', {'model_profile':'qwen3.8-27b','release_token':'a'*32})
            with patch('workflow.domains.hermes_agent.resident_worker.worker.wait_hermes_gpu_reservation'), \
                 patch('workflow.domains.hermes_agent.resident_worker.hold_hermes_model_usage_guard', return_value=nullcontext()), \
                 patch('workflow.domains.hermes_agent.resident_worker.os.access', return_value=False), \
                 patch('workflow.domains.hermes_agent.resident_worker.worker.verify_hermes_model_integrity') as verify, \
                 patch('workflow.domains.hermes_agent.resident_worker.subprocess.Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, 'CPU 모델 적재'):
                    run_resident_worker(root)
                verify.assert_not_called()
                launch.assert_not_called()

    def test_release_requires_matching_live_reservation(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as queue:
            enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=lambda *args, **kwargs: None)
            directory = Path(root) / 'handoff_123'
            write_record_atomically(directory / 'resident-status.json', {'status':'ready','model':'qwen3.8-27b','worker_pid':42})
            reservation = Path(queue) / 'reservation.json'
            write_record_atomically(reservation, {'path':str(directory.resolve()),'service':'hermes-agent','worker_pgid':41})
            lock = patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock', return_value=nullcontext(Path(queue)))
            identity = patch('workflow.common.gpu_job_queue.inspect_gpu_ticket_executor_identity', return_value='verified')
            leader = patch('workflow.common.gpu_job_queue.open_verified_hermes_process_group', side_effect=lambda _: os.open('/dev/null', os.O_RDONLY))
            with lock, identity, leader:
                with self.assertRaises(ValueError):
                    request_resident_release('handoff_123', 'a'*32, root=root)
                self.assertFalse((directory / 'release.request').exists())
                write_record_atomically(reservation, {'path':str(directory.resolve()),'service':'hermes-agent','worker_pgid':42})
                checked_reservation_records = []
                def reject_stale_release_condition(active_reservation_root, active_reservation_record):
                    checked_reservation_records.append((active_reservation_root, active_reservation_record))
                    return False
                self.assertEqual(request_resident_release('handoff_123', 'a'*32, root=root, release_condition_check=reject_stale_release_condition)['state'], 'deferred')
                self.assertEqual(checked_reservation_records[0][0], Path(queue))
                self.assertEqual(checked_reservation_records[0][1]['worker_pgid'], 42)
                self.assertFalse((directory / 'release.request').exists())
                self.assertEqual(request_resident_release('handoff_123', 'a'*32, root=root)['state'], 'requested')
                request = json.loads((directory / 'request.json').read_text())
                self.assertEqual(json.loads((directory / 'release.request').read_text()), {'token':request['release_token']})

    def test_ready_and_released_require_verified_process_and_reservation(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as queue:
            enqueue_resident_once('handoff_123', 'a'*32, root=root, launcher=lambda *args, **kwargs: None)
            directory = Path(root) / 'handoff_123'
            write_record_atomically(directory / 'status.json', {'status':'running'})
            write_record_atomically(directory / 'resident-status.json', {'status':'ready','model':'qwen3.8-27b',
                'worker_pid':42,'server_pid':43,'offload':'offloaded 10/10 layers to GPU'})
            reservation = Path(queue) / 'reservation.json'
            write_record_atomically(reservation, {'path':str(directory.resolve()),'service':'hermes-agent','worker_pgid':42})
            lock = patch('workflow.domains.hermes_agent.writer_reservation.hold_writer_reservation_queue_lock', side_effect=lambda: nullcontext(Path(queue)))
            identity = patch('workflow.common.gpu_job_queue.inspect_gpu_ticket_executor_identity', return_value='verified')
            leader = patch('workflow.common.gpu_job_queue.open_verified_hermes_process_group', side_effect=lambda _: os.open('/dev/null', os.O_RDONLY))
            child = patch('workflow.domains.hermes_agent.resident_queue._server_is_child', return_value=True)
            health = patch('workflow.domains.hermes_agent.resident_queue._healthy_resident_socket', return_value=True)
            with lock, identity, leader, child, health:
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'ready')
                write_record_atomically(directory / 'release.request', {'token':'a'*32})
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'running')
                (directory / 'release.request').unlink()
                write_record_atomically(reservation, {'path':str(directory.resolve()),'service':'hermes-agent','worker_pgid':99})
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'unknown')
                write_record_atomically(directory / 'status.json', {'status':'completed'})
                write_record_atomically(directory / 'resident-status.json', {'status':'stopped','model':'qwen3.8-27b','worker_pid':42})
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'unknown')
                write_record_atomically(reservation, {'path':str(directory.resolve()),'service':'hermes-agent','worker_pgid':42})
                with patch('workflow.common.gpu_job_queue.open_verified_hermes_process_group', return_value=None):
                    self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'running')
                reservation.unlink()
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'released')
                write_record_atomically(directory / 'status.json', {'status':'failed','exit_code':0})
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'released')
                write_record_atomically(directory / 'status.json', {'status':'failed','exit_code':1})
                self.assertEqual(inspect_resident('handoff_123', 'a'*32, root=root)['state'], 'unknown')

    def test_lease_rechecks_reservation_after_acceptance(self):
        from contextlib import contextmanager
        released = []
        @contextmanager
        def lease(_directory):
            try:
                yield
            finally:
                released.append(True)
        with patch('workflow.domains.hermes_agent.resident_client.hold_resident_lease', side_effect=lease), \
             patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', side_effect=[{'state':'ready'}, {'state':'unknown'}]):
            with self.assertRaises(ValueError):
                with hold_verified_resident_lease('handoff_123', 'a'*32, root='/tmp'):
                    self.fail('예약 확인이 실패한 서버를 사용하면 안 됩니다.')
        self.assertEqual(released, [True])

    def test_resident_selection_is_session_bound_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as root:
            enqueue_resident_once('resident_123', 'a'*32, root=root, launcher=lambda *args, **kwargs: None)
            enqueue_resident_once('resident_456', 'b'*32, root=root, launcher=lambda *args, **kwargs: None)
            with patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'ready'}):
                self.assertEqual(find_session_resident('a'*32, root=root), 'resident_123')
                self.assertIsNone(find_session_resident('c'*32, root=root))
                with self.assertRaises(ValueError):
                    enqueue_resident_once('resident_789', 'a'*32, root=root, launcher=lambda *args, **kwargs: None)
                duplicate = Path(root) / 'resident_789'; duplicate.mkdir()
                write_record_atomically(duplicate / 'request.json', {'context':{'session_id':'a'*32}})
                with self.assertRaises(ValueError):
                    find_session_resident('a'*32, root=root)

    def test_first_resident_is_idempotent_and_blocked_by_open_handoff(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            residents = Path(root) / 'residents'
            handoffs = GpuHandoffStore(Path(root) / 'handoffs')
            calls = []
            def launch(command, directory, service, **kwargs):
                calls.append(command)
                write_record_atomically(Path(directory) / 'status.json', {'status':'queued'})
            first = ensure_session_resident('a'*32, 'request_123', root=residents, handoff_store=handoffs, launcher=launch)
            second = ensure_session_resident('a'*32, 'request_456', root=residents, handoff_store=handoffs, launcher=launch)
            self.assertEqual(first['id'], second['id'])
            self.assertTrue(second['duplicate'])
            self.assertEqual(len(calls), 1)
            payload = {'prompt':'walk'}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            handoffs.approve('handoff_123', 'a'*32, 'kimodo', digest, target_request=payload, resident_id=first['id'], confirmed=True)
            with self.assertRaises(ValueError):
                ensure_session_resident('a'*32, 'request_789', root=residents, handoff_store=handoffs, launcher=launch)
            with self.assertRaises(ValueError):
                ensure_session_resident('b'*32, 'request_789', root=residents, handoff_store=handoffs, launcher=launch)
            self.assertEqual(len(calls), 1)

    def test_handoff_rejects_other_queued_resident_at_commit(self):
        from workflow.domains.hermes_agent.resident_queue import ensure_no_other_active_residents
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            residents = Path(root) / 'residents'
            handoffs = GpuHandoffStore(Path(root) / 'handoffs')
            def launch(command, directory, service, **kwargs):
                write_record_atomically(Path(directory) / 'status.json', {'status':'queued'})
            first = ensure_session_resident('a'*32, 'request_123', root=residents, handoff_store=handoffs, launcher=launch)
            second = ensure_session_resident('b'*32, 'request_456', root=residents, handoff_store=handoffs, launcher=launch)
            payload = {'prompt':'walk'}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            with self.assertRaisesRegex(ValueError, '다른 상주 모델'):
                handoffs.approve('handoff_123', 'a'*32, 'kimodo', digest, target_request=payload, resident_id=first['id'], confirmed=True,
                                 precommit_check=lambda:ensure_no_other_active_residents(first['id'], root=residents))
            self.assertIsNone(handoffs.read('handoff_123'))
            self.assertNotEqual(first['id'], second['id'])

    def test_other_resident_cannot_start_during_handoff_commit(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            residents = Path(root) / 'residents'
            handoffs = GpuHandoffStore(Path(root) / 'handoffs')
            payload = {'prompt':'walk'}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            entered, release = Event(), Event()
            def check():
                entered.set()
                if not release.wait(5): raise RuntimeError('test timed out')
            def approve():
                return handoffs.approve('handoff_123', 'a'*32, 'kimodo', digest, target_request=payload,
                                        resident_id='resident_123', confirmed=True, precommit_check=check)
            def launch(command, directory, service, **kwargs):
                write_record_atomically(Path(directory) / 'status.json', {'status':'queued'})
            with ThreadPoolExecutor(max_workers=2) as pool:
                approval = pool.submit(approve)
                self.assertTrue(entered.wait(5))
                start = pool.submit(ensure_session_resident, 'b'*32, 'request_456', root=residents, handoff_store=handoffs, launcher=launch)
                release.set()
                self.assertEqual(approval.result()['state'], 'approved')
                with self.assertRaisesRegex(ValueError, 'GPU 양도'):
                    start.result()

    def test_chat_worker_holds_verified_lease_and_binds_session(self):
        from contextlib import contextmanager
        from workflow.domains.hermes_agent.worker import execute_resident_hermes_job
        events = []
        @contextmanager
        def lease(identifier, session):
            events.append(('lease', identifier, session))
            try:
                yield
            finally:
                events.append(('released',))
        @contextmanager
        def model_guard(root, *, inference):
            events.append(('guard', inference))
            yield
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            write_record_atomically(directory / 'request.json', {'context':{'session_id':'a'*32}})
            def execute(path, *, resident_directory):
                self.assertEqual(events, [('lease','resident_123','a'*32), ('guard', True)])
                self.assertEqual(resident_directory.name, 'resident_123')
                return 'ok'
            with patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'ready'}), \
                 patch('workflow.domains.hermes_agent.resident_queue.hold_verified_resident_lease', side_effect=lease), \
                 patch('workflow.common.model_prepare_process.hold_hermes_model_usage_guard', side_effect=model_guard), \
                 patch('workflow.domains.hermes_agent.worker.execute_hermes_gpu_job', side_effect=execute):
                self.assertEqual(execute_resident_hermes_job(directory, 'resident_123', 'a'*32), 'ok')
                self.assertEqual(events[-1], ('released',))
                with self.assertRaises(ValueError):
                    execute_resident_hermes_job(directory, 'resident_123', 'b'*32)

    def test_resident_chat_uses_sandbox_without_starting_another_model(self):
        import shutil
        from unittest.mock import Mock
        from workflow.domains.hermes_agent import worker
        with tempfile.TemporaryDirectory() as root:
            job = Path(root) / 'job'
            runtime = Path(root) / 'runtime'
            source_root = Path(root) / 'source'
            project_python = source_root / '.venv/bin/python'
            project_python.parent.mkdir(parents=True)
            project_python.write_bytes(b'test interpreter')
            real_workflow_root = worker.WORKFLOW_ROOT_DIRECTORY
            job.mkdir(); runtime.mkdir()
            write_record_atomically(job / 'request.json', {'prompt':'test', 'model_profile':'qwen3.8-27b'})
            write_record_atomically(runtime / 'prepared.json', {'server_binary_sha256':'digest', 'runtime_library_paths':[]})
            def snapshot(_source, destination):
                skill = Path('workflow/domains/hermes_agent/skills')
                shutil.copytree(real_workflow_root / skill, destination / skill)
                return {'baseline_commit':'a'*40}
            agent = Mock(); agent.wait.return_value = 0; agent.poll.return_value = 0
            previous = os.getcwd()
            try:
                with patch.object(worker, 'RUNTIME_INSTALL_ROOT', runtime), \
                     patch.object(worker, 'WORKFLOW_ROOT_DIRECTORY', source_root), \
                     patch.object(worker, 'verify_hermes_model_integrity'), \
                     patch.object(worker, 'verify_hermes_runtime_integrity'), \
                     patch.object(worker, 'calculate_file_digest', return_value='digest'), \
                     patch.object(worker, 'copy_snapshot_source_files', side_effect=snapshot), \
                     patch.object(worker, 'collect_snapshot_change_diff', return_value=b''), \
                     patch.object(worker.subprocess, 'Popen', return_value=agent) as launch, \
                     patch.object(worker.threading.Thread, 'start'), \
                     patch.object(worker, 'wait_hermes_gpu_reservation') as wait_reservation:
                    worker.execute_hermes_gpu_job(job, resident_directory=Path(root) / 'resident')
                    wait_reservation.assert_not_called()
                    self.assertEqual(launch.call_count, 1)
                    self.assertEqual(launch.call_args.args[0][0], 'bwrap')
            finally:
                os.chdir(previous)
            result = json.loads((job / 'result.json').read_text())
            self.assertEqual(result['gpu_offload'], 'resident GPU reservation verified')
            self.assertEqual(result['agent_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
