import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from workflow.common.model_backup_sync import sync_snapshot, _resume_parent
from workflow.common.model_backup_service import verify_snapshot_manifest
import json
import os


class SnapshotResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.backup = root/'source', root/'backup'
        (self.source/'model').mkdir(parents=True)
        self.backup.mkdir()
        (self.source/'model'/'a').write_bytes(b'a'*64)
        (self.source/'model'/'b').write_bytes(b'b'*128)
        self.pending = self.backup/'.model-backup-snapshots'/'model'/('.pending-'+'a'*32)
        self.pending.mkdir(parents=True)
        self.roots = (self.source, self.backup, None)

    def test_resumes_verified_complete_file_and_partial_file(self):
        (self.pending/'a').write_bytes(b'a'*64)
        (self.pending/'b').write_bytes(b'b'*37)
        stages = []
        result = sync_snapshot('model', 'a'*32, roots=self.roots, resume=True,
                               phase=lambda stage, path, done, total: stages.append((stage, path, done, total)))
        self.assertFalse(self.pending.exists())
        self.assertEqual(result['bytes'], 192)
        self.assertEqual(result['resumed_bytes'], 101)
        self.assertEqual(result['copied_bytes'], 91)
        self.assertIn(('기존 부분 대조', 'b', 37, 37), stages)
        config = self.source.parent/'config.json'
        config.write_text(json.dumps({'source_path': str(self.source), 'local_mount_path': str(self.backup)}))
        verification = verify_snapshot_manifest('model', config, compare_source=True)
        self.assertTrue(verification['complete'])
        self.assertTrue(all(x['status'] == 'verified' for x in verification['files']))
        self.assertTrue(all(x['status'] == 'verified' for x in verification['local_comparison']['files']))

    def test_rejects_different_prefix_without_overwriting_pending(self):
        partial = self.pending/'b'
        partial.write_bytes(b'x'*37)
        with self.assertRaisesRegex(ValueError, '내용이 다릅니다'):
            sync_snapshot('model', 'a'*32, roots=self.roots, resume=True)
        self.assertEqual(partial.read_bytes(), b'x'*37)
        self.assertFalse((self.pending.parent/('a'*32)).exists())

    def test_rejects_unexpected_files_and_symlinks(self):
        for name, link in (('unexpected', False), ('b', True)):
            with self.subTest(name=name):
                path = self.pending/name
                if link:
                    path.symlink_to(self.source/'model'/'b')
                else:
                    path.write_bytes(b'extra')
                with self.assertRaises(ValueError):
                    sync_snapshot('model', 'a'*32, roots=self.roots, resume=True)
                path.unlink()
        self.assertTrue(self.pending.exists())

    def test_resume_parent_rejects_replaced_directory_symlink(self):
        outside = self.source.parent/'outside'
        outside.mkdir()
        (outside/'file').write_bytes(b'untouched')
        (self.pending/'nested').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            _resume_parent(self.pending, 'nested/file')
        self.assertEqual((outside/'file').read_bytes(), b'untouched')

    def test_rejects_hardlink_without_modifying_its_target(self):
        outside = self.source.parent/'other-file'
        outside.write_bytes(b'b'*37)
        os.link(outside, self.pending/'b')
        with self.assertRaisesRegex(ValueError, '하드링크'):
            sync_snapshot('model', 'a'*32, roots=self.roots, resume=True)
        self.assertEqual(outside.read_bytes(), b'b'*37)
        self.assertTrue((self.pending/'b').exists())

    def test_explicit_resume_preserves_previous_attempt_and_uses_same_job(self):
        from workflow.common.model_backup_verification import resume_backup_job
        state = self.source.parent/'state'
        (state/'jobs').mkdir(parents=True)
        job = 'a'*32
        original = {'job_id': job, 'model': 'model', 'operation': 'sync', 'target': 'canonical',
                    'status': 'failed', 'error': 'connection lost', 'started_at': 'before'}
        (state/'jobs'/f'{job}.json').write_text(json.dumps(original))
        with patch('workflow.common.model_backup_service.read_backup_roots', return_value=self.roots), \
             patch('workflow.common.model_backup_verification.subprocess.Popen') as launch:
            result = resume_backup_job(job, state_root=state)
        self.assertEqual(result['job_id'], job)
        saved = json.loads((state/'jobs'/f'{job}.json').read_text())
        self.assertEqual(saved['status'], 'running')
        self.assertEqual(saved['attempt_history'][0]['error'], 'connection lost')
        self.assertIn('--resume', launch.call_args.args[0])
        self.assertTrue(self.pending.exists())

    def test_completed_job_cannot_be_restarted_as_resume(self):
        from workflow.common.model_backup_verification import resume_backup_job
        state = self.source.parent/'state'
        (state/'jobs').mkdir(parents=True)
        job = 'a'*32
        (state/'jobs'/f'{job}.json').write_text(json.dumps({'job_id':job, 'model':'model', 'operation':'sync',
                                                          'target':'canonical', 'status':'completed'}))
        with patch('workflow.common.model_backup_verification.subprocess.Popen') as launch:
            result = resume_backup_job(job, state_root=state)
        self.assertEqual(result['status'], 'completed')
        launch.assert_not_called()

    def test_resume_passes_explicit_configuration_to_worker(self):
        from workflow.common.model_backup_verification import resume_backup_job
        state = self.source.parent/'state'
        (state/'jobs').mkdir(parents=True)
        job = 'a'*32
        config = self.source.parent/'config.json'
        config.write_text(json.dumps({'source_path':str(self.source), 'local_mount_path':str(self.backup)}))
        (state/'jobs'/f'{job}.json').write_text(json.dumps({'job_id':job, 'model':'model', 'operation':'sync',
                                                          'target':'canonical', 'status':'interrupted'}))
        with patch('workflow.common.model_backup_verification.subprocess.Popen') as launch:
            resume_backup_job(job, state_root=state, config_path=config)
        command=launch.call_args.args[0]
        self.assertEqual(command[command.index('--config-path')+1], str(config.resolve()))

    def test_gateway_routes_explicit_resume_by_job_id(self):
        from unittest.mock import Mock
        from workflow.common.management_gateway import ManagementCommandGateway
        from workflow.tests.test_management_gateway import GatewayContractTest
        job = 'a'*32
        gateway = ManagementCommandGateway({'model-downloads': Mock()})
        handler = GatewayContractTest().create_request_handler('/management/command',
            {'service': 'model-downloads', 'command': 'backup-resume', 'payload': {'job_id': job}})
        with patch('workflow.common.model_backup_verification.resume_backup_job', return_value={'job_id': job, 'status': 'running'}) as resume:
            self.assertTrue(gateway.handle(handler))
        resume.assert_called_once_with(job)
        self.assertEqual(json.loads(handler.wfile.getvalue())['status'], 'running')

    def test_worker_resumes_pending_and_publishes_completed_record(self):
        from workflow.common.model_backup_verification import run_worker
        state = self.source.parent/'state'
        (state/'jobs').mkdir(parents=True)
        job = 'a'*32
        record = {'job_id':job, 'model':'model', 'operation':'sync', 'target':'canonical',
                  'status':'running', 'started_at':'now', 'attempt_history':[{'status':'failed'}]}
        (state/'jobs'/f'{job}.json').write_text(json.dumps(record))
        (self.pending/'a').write_bytes(b'a'*17)
        fd = os.open(state/'worker.lock', os.O_CREAT | os.O_WRONLY, 0o600)
        args = ['worker', '--model','model', '--job-id',job, '--state-root',str(state),
                '--status-path',str(state/'status.json'), '--lock-fd',str(fd), '--operation','sync',
                '--target','canonical', '--resume']
        def sync_with_roots(*args, **kwargs):
            return sync_snapshot(*args, roots=self.roots, **kwargs)
        with patch('sys.argv', args), \
             patch('workflow.common.model_backup_sync.sync_snapshot', side_effect=sync_with_roots), \
             patch('workflow.common.model_backup_metadata.model_metadata', return_value={'state':'unavailable'}):
            run_worker()
        completed=json.loads((state/'jobs'/f'{job}.json').read_text())
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['attempt_history'], [{'status':'failed'}])
        self.assertEqual(completed['result']['snapshot_id'],job)
        self.assertFalse(self.pending.exists())
