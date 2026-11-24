import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from workflow.common.model_catalog import read_catalog
from workflow.common.model_catalog_migration import assess_relocation


class MigrationAssessmentTest(unittest.TestCase):
    def test_links_and_unknown_safety_are_reported(self):
        report = {'version': 1, 'root': '/nonexistent', 'entries': [{'path': 'animationgpt', 'files': 1}],
                  'links': [{'path': 'animationgpt-author/shared', 'target': '../animationgpt/assets'}]}
        plan = assess_relocation(read_catalog(), report, 'animationgpt', 'models/animationgpt')
        self.assertFalse(plan['ready_to_move'])
        self.assertEqual(len(plan['related_links']), 1)
        self.assertIn('animationgpt', plan['declared_services'])

    def test_rejects_overlapping_and_escaping_destinations(self):
        report = {'version': 1, 'root': '/nonexistent', 'entries': [], 'links': []}
        for destination in ('../outside', 'animationgpt/sub', '/absolute', 'animationgpt'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                assess_relocation(read_catalog(), report, 'animationgpt', destination)

    def test_destination_parent_symlink_is_flagged(self):
        with TemporaryDirectory() as root, TemporaryDirectory() as outside:
            (Path(root) / 'models').symlink_to(outside, target_is_directory=True)
            report = {'version': 1, 'root': root, 'entries': [], 'links': []}
            plan = assess_relocation(read_catalog(), report, 'animationgpt', 'models/animationgpt')
            self.assertEqual(plan['destination_ancestor'], 'unsafe')
            self.assertFalse(plan['ready_to_move'])
