import contextlib
import fcntl
import hashlib
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

    def test_vace_sources_are_copied_only_when_present_and_verified(self):
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            project = Path(directory) / 'snapshot'
            manifest = root / 'generators/wan_vace/config/official-runtime.yaml'
            manifest.parent.mkdir(parents=True)
            names = ('videox_fun/models/wan_transformer3d_vace.py',
                     'videox_fun/pipeline/pipeline_wan2_2_vace_fun.py',
                     'config/wan2.2/wan_civitai_t2v.yaml')
            digest = hashlib.sha256(b'approved').hexdigest()
            manifest.write_text(yaml.safe_dump({'source_files': {name: digest for name in names}}))
            source = root / '.local/videox-fun-vace-pinned' / names[0]
            source.parent.mkdir(parents=True)
            source.write_bytes(b'approved')
            audit.copy_vace_test_sources(root, project)
            self.assertEqual((project / '.local/videox-fun-vace-pinned' / names[0]).read_bytes(), b'approved')
            self.assertFalse((project / '.local/videox-fun-vace-pinned' / names[1]).exists())
            source.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, '해시'):
                audit.copy_vace_test_sources(root, project)

    def test_comfy_source_uses_pinned_commit_not_worktree(self):
        from generators.wan_fun.prepare import FUN_RUNTIME_SOURCES
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            project = Path(directory) / 'snapshot'
            source = root / '.local/wan22-animate/ComfyUI'
            (source / '.git').mkdir(parents=True)
            local = source / 'comfy_extras/nodes_wan.py'
            local.parent.mkdir()
            local.write_bytes(b'local edit')
            with patch.object(audit.subprocess, 'check_output', return_value=b'pinned source') as git:
                audit.copy_comfy_test_source(root, project)
            self.assertEqual(git.call_args.args[0], ['git', '-C', str(source), 'show',
                FUN_RUNTIME_SOURCES['ComfyUI'][1] + ':comfy_extras/nodes_wan.py'])
            self.assertEqual((project / '.local/wan22-animate/ComfyUI/comfy_extras/nodes_wan.py').read_bytes(), b'pinned source')
            self.assertEqual(local.read_bytes(), b'local edit')

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
