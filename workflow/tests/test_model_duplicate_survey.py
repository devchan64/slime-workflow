import json
from pathlib import Path
import tempfile
import unittest

from workflow.common.model_backup_sync import sync_snapshot
from workflow.common.model_duplicate_survey import survey_duplicates
from workflow.common.model_catalog import read_duplicate_survey


class DuplicateSurveyTests(unittest.TestCase):
    def test_rejects_repeated_or_invalid_paths_in_saved_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / 'report.json'
            item = {'path': 'model/weights', 'state': 'matches', 'device': 1, 'inode': 2}
            record = {'version': 1, 'root': str(root), 'observed_at': 'then', 'errors': [],
                      'groups': [{'size': 1, 'paths': [item, dict(item)]}]}
            for bad_path in ('model/weights', '../outside', '/absolute', 'model//weights', 'model/../weights', 'model\\weights'):
                with self.subTest(path=bad_path):
                    record['groups'][0]['paths'][1]['path'] = bad_path
                    report.write_text(json.dumps(record))
                    self.assertIsNone(read_duplicate_survey(report, root))

    def test_reports_current_matches_and_changed_files_without_following_external_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'source', root / 'backup'
            for name in ('one', 'two'):
                (source / name).mkdir(parents=True)
                (source / name / 'weight').write_bytes(b'identical')
            backup.mkdir()
            for name, job in (('one', 'a' * 32), ('two', 'b' * 32)):
                sync_snapshot(name, job, roots=(source, backup, None))
            result = survey_duplicates(source, backup, minimum_bytes=0)
            self.assertEqual(len(result['groups']), 1)
            self.assertEqual([p['state'] for p in result['groups'][0]['paths']], ['matches', 'matches'])
            report = root / 'report.json'
            report.write_text(json.dumps(result))
            exposed = read_duplicate_survey(report, source)
            self.assertEqual(len(exposed['groups']), 1)
            self.assertEqual(exposed['groups'][0]['distinct_files'], 2)
            self.assertEqual(exposed['groups'][0]['duplicate_logical_bytes'], len(b'identical'))
            self.assertNotIn('inode', exposed['groups'][0]['paths'][0])
            self.assertIsNone(read_duplicate_survey(report, root / 'wrong-root'))
            (source / 'two' / 'weight').write_bytes(b'different')
            result = survey_duplicates(source, backup, minimum_bytes=0)
            self.assertEqual([p['state'] for p in result['groups'][0]['paths']], ['matches', 'different'])
            report.write_text(json.dumps(result))
            self.assertIsNone(read_duplicate_survey(report, source)['groups'][0]['duplicate_logical_bytes'])
            (source / 'two' / 'weight').unlink()
            (source / 'two' / 'weight').symlink_to(root / 'outside')
            (root / 'outside').write_bytes(b'identical')
            result = survey_duplicates(source, backup, minimum_bytes=0)
            self.assertEqual(result['groups'][0]['paths'][1]['state'], 'unavailable')

    def test_invalid_manifest_does_not_contribute_partial_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'source', root / 'backup'
            for name in ('one', 'two'):
                (source / name).mkdir(parents=True)
                (source / name / 'weight').write_bytes(b'identical')
            backup.mkdir()
            for name, job in (('one', 'a' * 32), ('two', 'b' * 32)):
                sync_snapshot(name, job, roots=(source, backup, None))
            manifest = backup / '.model-backup-snapshots' / 'two' / ('b' * 32) / '.snapshot.json'
            record = json.loads(manifest.read_text())
            record['files'].append({'path': '../invalid', 'size': 9, 'sha256': '0' * 64})
            manifest.write_text(json.dumps(record))
            result = survey_duplicates(source, backup, minimum_bytes=0)
            self.assertEqual(result['groups'], [])
            self.assertEqual(result['errors'][0]['root'], 'two')
