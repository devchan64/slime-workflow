import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workflow.common import model_catalog
from workflow.common.model_external_survey import EXTERNAL_GROUPS, MINIMUM_BYTES, survey_external_weights


class ExternalSurveyTest(unittest.TestCase):
    def test_records_only_large_regular_files_without_following_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for group in EXTERNAL_GROUPS:
                (root/group).mkdir(parents=True, exist_ok=True)
            target = root/EXTERNAL_GROUPS[0]/'weights.gguf'
            with target.open('wb') as stream:
                stream.truncate(MINIMUM_BYTES + 1)
            (target.parent/'small.gguf').write_bytes(b'small')
            (target.parent/'link.gguf').symlink_to(target)
            report = survey_external_weights(root)
            self.assertEqual([item['path'] for item in report['files']], [f'{EXTERNAL_GROUPS[0]}/weights.gguf'])
            self.assertEqual(report['errors'], [])
            self.assertFalse(report['files'][0]['changed'])

    def test_missing_root_is_reported_and_latest_invalid_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = survey_external_weights(root)
            self.assertEqual(len(report['errors']), len(EXTERNAL_GROUPS))
            old = root/'external-weight-observations-old.json'
            old.write_text(json.dumps(report))
            new = root/'external-weight-observations-new.json'
            new.write_text('{broken')
            os.utime(old, ns=(1_000_000_000, 1_000_000_000))
            os.utime(new, ns=(2_000_000_000, 2_000_000_000))
            with patch.object(model_catalog, 'EXTERNAL_SURVEY_DIR', root):
                self.assertIsNone(model_catalog.read_external_weight_survey())
                new.unlink()
                loaded = model_catalog.read_external_weight_survey()
                self.assertEqual(loaded['error_count'], len(EXTERNAL_GROUPS))
                self.assertTrue(all(item['error_count'] == 1 for item in loaded['groups']))
