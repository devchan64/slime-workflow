import tempfile
import unittest
from pathlib import Path
from tools.review.build_frontend_review import clear_generated_review_files


class HistoryPreservationTests(unittest.TestCase):
    def test_rebuild_preserves_both_generator_histories(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_review_directory=Path(current_temp_directory)
            for current_generator_name in ('qwen-2511','qwen-2512'):
                current_history_directory=current_review_directory/current_generator_name
                current_history_directory.mkdir()
                (current_history_directory/'record.json').write_text('preserved')
            (current_review_directory/'preview.html').write_text('old')
            (current_review_directory/'animation-1').mkdir()
            clear_generated_review_files(current_review_directory)
            clear_generated_review_files(current_review_directory)
            self.assertFalse((current_review_directory/'preview.html').exists())
            self.assertFalse((current_review_directory/'animation-1').exists())
            for current_generator_name in ('qwen-2511','qwen-2512'):
                self.assertEqual((current_review_directory/current_generator_name/'record.json').read_text(),'preserved')
