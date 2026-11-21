import json
import os
from pathlib import Path
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import patch

from generators.wan_fun.progress_otel import FunProgressRecorder
from workflow.domains.hermes_agent.video_operations import read_fun_progress_event


class FunProgressTests(unittest.TestCase):
    def test_sdk_event_and_current_attempt_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / '2026-11-21_10-21-48-00e8c029'
            attempt = 'a' * 32
            root = job / 'attempts' / attempt
            root.mkdir(parents=True)
            (job / 'current-attempt.json').write_text(json.dumps({'id': attempt}))
            (job / 'status.json').write_text(json.dumps({'status': 'running'}))
            with patch.dict(os.environ, {'OTEL_EXPORTER_OTLP_ENDPOINT': '', 'OTEL_EXPORTER_OTLP_LOGS_ENDPOINT': ''}):
                recorder = FunProgressRecorder(root, 20, [])
                self.assertIsNotNone(recorder._otel_provider)
                recorder.save_generation_metrics()
                event = read_fun_progress_event(job, job.name, {'status': 'running'})
                self.assertEqual(event['event.name'], 'generation.progress')
                self.assertEqual(event['generation.step.total'], 20)
                self.assertNotIn('generation.estimate.remaining_seconds', event)
                self.assertNotIn('code.file.path', event)
                recorder.current_run_state['stage'] = 'inference'
                recorder.current_step_samples = [1, 2, 3]
                recorder.save_generation_metrics()
                event = read_fun_progress_event(job, job.name, {'status': 'running'})
                self.assertGreater(event['generation.estimate.remaining_seconds'], 0)
                self.assertIn('generation.estimate.completion_time', event)
                self.assertEqual(event['generation.estimate.sample_count'], 2)
                self.assertIsNone(read_fun_progress_event(job, job.name, {'status': 'queued'}))
                self.assertIsNone(read_fun_progress_event(job, job.name, {'status': 'completed', 'attempt': 'b' * 32}))
                self.assertIsNotNone(read_fun_progress_event(job, job.name, {'status': 'completed', 'attempt': attempt}))
                recorder._otel_provider.shutdown()

    def test_missing_or_malformed_event_does_not_hide_status(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(read_fun_progress_event(Path(directory), 'job', {'status': 'running'}))

    def test_otlp_http_export(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.end_headers()
            def log_message(self, *args):
                pass
        with HTTPServer(('127.0.0.1', 0), Handler) as server, tempfile.TemporaryDirectory() as directory:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                root = Path(directory) / 'job' / 'attempts' / ('a' * 32)
                root.mkdir(parents=True)
                endpoint = f'http://127.0.0.1:{server.server_port}/v1/logs'
                with patch.dict(os.environ, {'OTEL_EXPORTER_OTLP_ENDPOINT': '', 'OTEL_EXPORTER_OTLP_LOGS_ENDPOINT': endpoint}):
                    recorder = FunProgressRecorder(root, 10, [])
                    recorder.save_generation_metrics()
                    self.assertTrue(recorder._otel_provider.force_flush())
                    recorder._otel_provider.shutdown()
                self.assertEqual(received[0][0], '/v1/logs')
                from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
                request = ExportLogsServiceRequest.FromString(received[0][1])
                record = request.resource_logs[0].scope_logs[0].log_records[0]
                self.assertEqual(record.body.string_value, 'generation.progress')
                self.assertEqual({item.key: item.value.string_value for item in record.attributes}['generation.job.id'], 'job')
            finally:
                server.shutdown()
                thread.join()
