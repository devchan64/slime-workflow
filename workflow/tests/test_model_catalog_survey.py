import os
from pathlib import Path
import tempfile
import unittest

from workflow.common.model_catalog_survey import survey_model_root


class SurveyTest(unittest.TestCase):
    def test_nested_installations_are_separate_from_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / 'models' / 'example'
            model.mkdir(parents=True)
            (model / 'weights').write_bytes(b'123')
            report = survey_model_root(root, nested_roots=('models',))
            self.assertEqual(report['surveyed_roots'], ['models'])
            entries = {entry['path']: entry for entry in report['entries']}
            self.assertEqual(entries['models']['logical_bytes'], 3)
            self.assertEqual(entries['models/example']['logical_bytes'], 3)
            with self.assertRaises(ValueError):
                survey_model_root(root, nested_roots=('../outside',))

    def test_empty_nested_root_is_recorded_as_surveyed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'models').mkdir()
            report = survey_model_root(root, nested_roots=('models',))
            self.assertEqual(report['surveyed_roots'], ['models'])
            self.assertEqual([entry['path'] for entry in report['entries']], ['models'])

    def test_shared_files_links_and_service_mapping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'models'
            (root / 'base').mkdir(parents=True)
            (root / 'adapter').mkdir()
            (root / 'base' / 'weight').write_bytes(b'abc')
            os.link(root / 'base' / 'weight', root / 'adapter' / 'same')
            (root / 'adapter' / 'shared').symlink_to('../base', target_is_directory=True)
            (root / 'adapter' / 'broken').symlink_to('../missing')
            outside = Path(temporary) / 'private'
            outside.write_bytes(b'secret')
            (root / 'adapter' / 'outside').symlink_to(outside)
            report = survey_model_root(root, {'one': [root / 'base'], 'two': [root / 'base' / 'weight']})
            entries = {item['path']: item for item in report['entries']}
            self.assertEqual(entries['base']['logical_bytes'], 3)
            self.assertEqual(entries['adapter']['logical_bytes'], 3)
            self.assertEqual(entries['base']['services'], ['one', 'two'])
            self.assertEqual(entries['adapter']['links'], 3)
            self.assertEqual({link['path']: link['status'] for link in report['links']},
                             {'adapter/shared': 'present', 'adapter/broken': 'missing', 'adapter/outside': 'outside'})
            self.assertEqual(len(report['hardlinks']), 1)
            self.assertEqual(set(report['hardlinks'][0]), {'base/weight', 'adapter/same'})
            self.assertFalse(report['errors'])


if __name__ == '__main__':
    unittest.main()
