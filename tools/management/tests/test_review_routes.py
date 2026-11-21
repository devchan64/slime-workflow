"""공통 검수 서버의 진입 페이지와 파일 제공 경계를 확인한다."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SERVER_MODULE_PATH = Path(__file__).resolve().parents[1] / 'serve.py'
server_module_spec = importlib.util.spec_from_file_location('workflow_review_server', SERVER_MODULE_PATH)
server_module_value = importlib.util.module_from_spec(server_module_spec)
server_module_spec.loader.exec_module(server_module_value)

class ReviewRouteTests(unittest.TestCase):
    def test_custom_entry_and_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_directory_path = Path(temporary_directory_name)
            review_root_directory = temporary_directory_path / 'review'
            review_root_directory.mkdir()
            (review_root_directory / 'overlay-review.html').write_text('<html></html>')
            (review_root_directory / 'execution.log').write_text('log')
            (temporary_directory_path / 'outside.png').write_bytes(b'outside')
            (review_root_directory / 'linked.png').symlink_to(temporary_directory_path / 'outside.png')
            self.assertEqual(server_module_value.resolve_review_request(review_root_directory, '/', 'overlay-review.html'), review_root_directory / 'overlay-review.html')
            for requested_url_path in ('/../outside.png','/%2e%2e/outside.png','/linked.png','/execution.log','/.env','/missing.png','/nested/'):
                with self.subTest(requested_url_path=requested_url_path):
                    with self.assertRaises(ValueError):
                        server_module_value.resolve_review_request(review_root_directory, requested_url_path)

if __name__ == '__main__':
    unittest.main()
