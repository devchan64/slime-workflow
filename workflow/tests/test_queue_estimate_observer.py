import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from workflow.domains.hermes_agent import queue_estimate_observer

from workflow.domains.hermes_agent.queue_estimate_observer import observe_running_queue_estimate


class QueueEstimateObserverTests(unittest.TestCase):
    def test_current_running_estimate_only_and_no_files_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = {'status': 'running'}
            (root / 'status.json').write_text(json.dumps(status))
            (root / 'queue-telemetry.json').write_text(json.dumps({'attempt_id': '123'}))
            metrics_path = root / 'queue-telemetry' / '123' / 'metrics.json'
            metrics_path.parent.mkdir(parents=True)
            estimate = {'remaining': 20, 'completion': (datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat(),
                        'total_seconds': 40, 'estimated_progress': 50, 'sample_count': 2,
                        'updated_at': (datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat(),
                        'scope': 'GPU 대기 제외', 'basis': '동일 조건'}
            metrics = {'job_id': 'job', 'attempt_id': '123', 'status': 'running', 'estimate': estimate}
            metrics_path.write_text(json.dumps(metrics))
            before = {path: path.read_bytes() for path in (root/'status.json',root/'queue-telemetry.json',metrics_path)}
            self.assertEqual(observe_running_queue_estimate(root, 'job', status), estimate)
            self.assertEqual(before, {path: path.read_bytes() for path in before})
            self.assertIsNone(observe_running_queue_estimate(root, 'other', status))
            self.assertIsNone(observe_running_queue_estimate(root, 'job', {'status': 'completed'}))
            for change in ({'attempt_id': '124'}, {'status': 'completed'}, {'estimate': {**estimate, 'remaining': -1}}, {'estimate': {**estimate, 'estimated_progress': 100}}, {'estimate': {**estimate, 'total_seconds': 0}},
                           {'estimate': {**estimate, 'updated_at': '2000-01-01T00:00:00+00:00'}}):
                with self.subTest(change=change):
                    metrics_path.write_text(json.dumps({**metrics, **change}))
                    self.assertIsNone(observe_running_queue_estimate(root, 'job', status))

    def test_worker_progress_current_attempt_only(self):
        observe = queue_estimate_observer.observe_running_queue_progress
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = {'status': 'running'}
            (root/'status.json').write_text(json.dumps(status))
            (root/'queue-telemetry.json').write_text('{"attempt_id":"123"}')
            path = root/'queue-telemetry'/'123'/'metrics.json'
            path.parent.mkdir(parents=True)
            progress = {'stage':'inference','step':3,'total':20,'updated_at':(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat(),'scope':'추론 단계'}
            record = {'job_id':'job','attempt_id':'123','status':'running','worker_progress':progress}
            path.write_text(json.dumps(record))
            self.assertEqual(observe(root,'job',status),progress)
            self.assertIsNone(observe(root,'other',status))
            for change in ({'step':21}, {'total':0}, {'updated_at':'2000-01-01T00:00:00+00:00'}):
                path.write_text(json.dumps({**record,'worker_progress':{**progress,**change}}))
                self.assertIsNone(observe(root,'job',status))

    def test_pointer_or_status_change_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = {'status': 'running'}
            (root/'status.json').write_text(json.dumps(status))
            pointer = root/'queue-telemetry.json'
            pointer.write_text('{"attempt_id":"123"}')
            metrics_path = root/'queue-telemetry'/'123'/'metrics.json'
            metrics_path.parent.mkdir(parents=True)
            estimate = {'remaining':None,'completion':None,'total_seconds':None,'estimated_progress':None,
                        'sample_count':0,'updated_at':(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat(),
                        'scope':'test','basis':'test'}
            metrics_path.write_text(json.dumps({'job_id':'job','attempt_id':'123','status':'running','estimate':estimate}))
            original = queue_estimate_observer.read_bounded_delegation_record
            for target in ('pointer', 'status'):
                pointer.write_text('{"attempt_id":"123"}')
                (root/'status.json').write_text(json.dumps(status))
                calls = []
                def change_before_recheck(path):
                    calls.append(path)
                    if target == 'pointer' and path == pointer and calls.count(pointer) == 2:
                        pointer.write_text('{"attempt_id":"124"}')
                    if target == 'status' and path == root/'status.json':
                        (root/'status.json').write_text('{"status":"completed"}')
                    return original(path)
                with self.subTest(target=target), patch.object(queue_estimate_observer,'read_bounded_delegation_record',side_effect=change_before_recheck):
                    self.assertIsNone(observe_running_queue_estimate(root, 'job', status))

    def test_video_source_exposes_estimate_without_recovery(self):
        from workflow.domains.hermes_agent import video_operations
        with tempfile.TemporaryDirectory() as directory:
            job_id = '2026-11-21_01-02-03-12345678'
            root = Path(directory)/job_id
            root.mkdir()
            (root/'status.json').write_text('{"status":"running"}')
            (root/'queue-telemetry.json').write_text('{"attempt_id":"123"}')
            metrics = root/'queue-telemetry'/'123'/'metrics.json'
            metrics.parent.mkdir(parents=True)
            estimate = {'remaining':None,'completion':None,'total_seconds':None,'estimated_progress':None,
                        'sample_count':0,'updated_at':(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat(),
                        'scope':'test','basis':'test'}
            metrics.write_text(json.dumps({'job_id':job_id,'attempt_id':'123','status':'running','estimate':estimate}))
            with patch.object(video_operations,'make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=Path(directory))):
                before = (root/'status.json').read_bytes()
                result = video_operations.read_hermes_video_source_job('wan22-vace',job_id)
                self.assertEqual(result['estimate'],estimate)
                self.assertEqual((root/'status.json').read_bytes(),before)

    def test_video_estimate_crosses_isolated_gateway(self):
        import threading
        from http.server import ThreadingHTTPServer
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, execute_management_command
        from workflow.common.management_runtime import ManagementServiceRuntime, bind_stored_management_service
        from workflow.domains.hermes_agent import video_operations
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.gateway_server import create_gateway_request_handler
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_id = '2026-11-21_01-02-03-12345678'
            job = root/'jobs'/job_id
            job.mkdir(parents=True)
            (job/'status.json').write_text('{"status":"running"}')
            (job/'queue-telemetry.json').write_text('{"attempt_id":"123"}')
            metrics = job/'queue-telemetry'/'123'/'metrics.json'
            metrics.parent.mkdir(parents=True)
            estimate = {'remaining':20,'completion':(datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat(),
                        'total_seconds':40,'estimated_progress':50,'sample_count':2,
                        'updated_at':(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat(),
                        'scope':'test','basis':'test'}
            metrics.write_text(json.dumps({'job_id':job_id,'attempt_id':'123','status':'running','estimate':estimate}))
            manager = HermesServiceManager(root/'hermes',root/'sessions')
            bindings = {name:bind_stored_management_service(lambda request:False,root) for name in MANAGEMENT_SERVICE_ROUTES}
            bindings['hermes-agent'] = bind_stored_management_service(manager.handle_hermes_request,root/'hermes')
            runtime = ManagementServiceRuntime(bindings,lambda request:False,lambda:None)
            server = ThreadingHTTPServer(('127.0.0.1',0),create_gateway_request_handler(runtime.dispatch_runtime_request))
            server.emit_gateway_trace=lambda *values:None
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                with patch.object(video_operations,'make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=root/'jobs')):
                    response = execute_management_command('hermes-agent','hermes-video-source-status',
                        {'service':'wan22-vace','job_id':job_id},f'http://127.0.0.1:{server.server_port}')
                self.assertEqual(response['job']['estimate'],estimate)
                self.assertEqual(json.loads((job/'status.json').read_text()),{'status':'running'})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_rejects_symlinked_attempt(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root/'status.json').write_text('{"status":"running"}')
            (root/'queue-telemetry.json').write_text('{"attempt_id":"123"}')
            (root/'queue-telemetry').mkdir()
            (root/'queue-telemetry'/'123').symlink_to(external, target_is_directory=True)
            self.assertIsNone(observe_running_queue_estimate(root, 'job', {'status':'running'}))
