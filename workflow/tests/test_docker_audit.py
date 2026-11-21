import contextlib
import fcntl
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow.tests import docker_audit as audit


class DockerAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(audit, 'RUNS', Path(tmp)))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def test_receipt_precedes_completion_and_preserves_exit_status(self):
        with patch.object(audit.subprocess, 'Popen') as spawn:
            self.assertEqual(audit.submit(), 0)
        receipt = json.loads(self.output.getvalue())
        path = Path(receipt['report_path'])
        self.assertEqual(json.loads(path.read_text()), receipt)
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])
        with (path.parent / 'worker.lock').open() as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(audit.result(receipt['run_id']), 0)
            self.assertEqual(json.loads(path.read_text())['status'], 'queued')
        audit.publish(path, dict(receipt, status='failed', exit_code=1, failed=2))
        self.assertEqual(audit.result(receipt['run_id']), 1)
        self.assertEqual(json.loads(path.read_text())['failed'], 2)

    def test_start_failure_and_interrupted_worker_are_reported(self):
        with patch.object(audit.subprocess, 'Popen', side_effect=OSError('spawn failed')):
            self.assertEqual(audit.submit(), 1)
        receipt = json.loads(self.output.getvalue())
        self.assertEqual(receipt['reason'], 'spawn failed')
        path = Path(receipt['report_path'])
        audit.publish(path, dict(receipt, status='running'))
        self.assertEqual(audit.result(receipt['run_id']), 1)
        self.assertEqual(json.loads(path.read_text())['status'], 'error')

    def test_docker_completion_uses_test_counts_and_handles_missing_reports(self):
        for code in (0, 1, 125):
            with self.subTest(code=code):
                run = audit.RUNS / str(code)
                run.mkdir()
                report = run / 'report.json'
                audit.publish(report, {'status': 'queued'})

                def prepare(workspace):
                    (workspace / 'slime-workflow/gui').mkdir(parents=True)

                def docker(args, **kwargs):
                    if args[1] == 'build':
                        Path(args[args.index('--iidfile') + 1]).write_text('fixture-id')
                    else:
                        self.assertIn('fixture-id', args)
                        if code != 125:
                            (run / 'artifacts/summary.json').write_text(json.dumps({
                                'exit_code': code, 'passed': 8, 'failed': code, 'errors': 0, 'skipped': 0}))
                    return audit.subprocess.CompletedProcess(args, code)

                with patch.object(audit, 'prepare_workspace', side_effect=prepare), patch.object(
                        audit.subprocess, 'run', side_effect=docker):
                    audit.worker(run.name)
                record = json.loads(report.read_text())
                self.assertEqual(record['status'], {0:'passed', 1:'failed', 125:'error'}[code])
                self.assertEqual(record['exit_code'], code)
                if code != 125:
                    self.assertEqual(record['passed'], 8)
