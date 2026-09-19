"""검수 CLI의 명시적 입력과 파일 쓰기 경계."""
from pathlib import Path
import subprocess
import sys
import unittest
import test_sidecar as fixtures
from workflow.artifacts.registry import archive_register
from workflow.artifacts.reviews import current_review


class ReviewCliTests(unittest.TestCase):
    setUp = fixtures.PairTests.setUp
    write = fixtures.PairTests.write

    def prepare(self):
        self.db = self.root.parent / 'registry.sqlite'
        self.entry = archive_register(self.db, self.root, self.sidecar)
        self.command = [sys.executable, '-m', 'workflow.artifacts.review_cli', '--registry', str(self.db),
                        '--artifact-id', 'terrain.test', '--version', '1.0.0',
                        '--log', str(self.root.parent / 'review.log')]

    def record_args(self, review_id='review.cli'):
        return ['record', '--review-id', review_id, '--decision', 'APPROVED',
                '--reviewer', 'synthetic-test', '--evidence-ref', 'synthetic-evidence',
                '--content-hash', self.entry['content_hash'], '--metadata-hash', self.entry['metadata_hash']]

    def run_cli(self, args):
        return subprocess.run(self.command + args, capture_output=True, text=True)

    def test_show_does_not_approve_and_record_is_explicit(self):
        self.prepare()
        shown = self.run_cli(['show'])
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn('"review": null', shown.stdout)
        self.assertIsNone(current_review(self.db, 'terrain.test', '1.0.0'))
        recorded = self.run_cli(self.record_args())
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
        self.assertEqual(current_review(self.db, 'terrain.test', '1.0.0')['review_id'], 'review.cli')
        self.assertEqual(self.run_cli(self.record_args()).returncode, 0)
        stale = self.run_cli(self.record_args('review.stale'))
        self.assertEqual(stale.returncode, 1)
        self.assertIn('/artifact-review/failure', stale.stdout)

    def test_missing_evidence_is_rejected_before_writing(self):
        self.prepare()
        result = self.run_cli(['record', '--review-id', 'review.cli', '--decision', 'APPROVED'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(current_review(self.db, 'terrain.test', '1.0.0'))

    def test_log_cannot_overwrite_registry_or_archived_pair(self):
        self.prepare()
        for target in [self.db, Path(self.entry['root']) / 'tile.json']:
            with self.subTest(target=target):
                before = target.read_bytes()
                self.command[-1] = str(target)
                self.assertNotEqual(self.run_cli(['show']).returncode, 0)
                self.assertEqual(target.read_bytes(), before)
