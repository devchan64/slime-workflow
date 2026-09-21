"""UI 검수 빌드의 manifest 검증과 독립 사본 전달을 확인한다."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.review.import_ui_bundle import import_ui_bundle


class UiBundleTests(unittest.TestCase):
    def make_bundle(self, temporary_directory_path):
        bundle_directory_path = temporary_directory_path/'bundle'
        (bundle_directory_path/'review').mkdir(parents=True)
        page_source_bytes = b'<html><body>review</body></html>'
        (bundle_directory_path/'review'/'sample.html').write_bytes(page_source_bytes)
        manifest_value = {
            'schemaVersion': 1, 'kind': 'slime-ui-review', 'sourceCommit': 'a'*40,
            'sourceDirty': False, 'createdAt': '2026-09-21T00:00:00Z',
            'pages': [{'id': 'sample-ui', 'label': 'UI 샘플', 'path': 'review/sample.html'}],
            'files': [{'path': 'review/sample.html', 'sha256': hashlib.sha256(page_source_bytes).hexdigest()}],
        }
        (bundle_directory_path/'manifest.json').write_text(json.dumps(manifest_value))
        return bundle_directory_path

    def test_imports_verified_bundle_as_independent_copy(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_directory_path = Path(temporary_directory_name)
            source_bundle_directory = self.make_bundle(temporary_directory_path)
            review_output_directory = temporary_directory_path/'output'
            review_output_directory.mkdir()
            page_records = import_ui_bundle(source_bundle_directory, review_output_directory, lambda *unused_trace_arguments: None)
            self.assertEqual(len(page_records), 1)
            copied_page_path = review_output_directory/page_records[0]['path']
            self.assertEqual(copied_page_path.read_text(), '<html><body>review</body></html>')
            self.assertIn('커밋 원본', page_records[0]['description'])

    def test_rejects_changed_bundle_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_directory_path = Path(temporary_directory_name)
            source_bundle_directory = self.make_bundle(temporary_directory_path)
            (source_bundle_directory/'review'/'sample.html').write_text('changed')
            review_output_directory = temporary_directory_path/'output'
            review_output_directory.mkdir()
            with self.assertRaisesRegex(ValueError, '해시 불일치'):
                import_ui_bundle(source_bundle_directory, review_output_directory, lambda *unused_trace_arguments: None)


if __name__ == '__main__':
    unittest.main()
