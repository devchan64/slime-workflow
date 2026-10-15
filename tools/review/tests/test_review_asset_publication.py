"""격리 파일로 검수 이미지의 불변 주소와 원자적 게시를 검증한다."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common.review_asset_publication import publish_review_image_asset


class ReviewAssetPublicationTests(unittest.TestCase):
    def test_republication_preserves_previous_version_and_skips_existing_write(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_source_path=current_root_path/'source.png'
            current_source_path.write_bytes(b'first image')
            current_first_path=publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            with patch.object(Path,'write_bytes',side_effect=AssertionError('기존 파일을 다시 쓰면 안 됩니다.')):
                self.assertEqual(publish_review_image_asset(current_source_path,current_root_path/'public','review-character'),current_first_path)
            current_source_path.write_bytes(b'next image')
            current_next_path=publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            self.assertNotEqual(current_first_path,current_next_path)
            self.assertEqual(current_first_path.read_bytes(),b'first image')
            self.assertEqual(current_next_path.read_bytes(),b'next image')

    def test_failed_publish_leaves_no_partial_final_or_temporary_file(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_source_path=current_root_path/'source.png'
            current_source_path.write_bytes(b'image')
            with patch.object(Path,'replace',side_effect=OSError('게시 실패')),self.assertRaises(OSError):
                publish_review_image_asset(current_source_path,current_root_path/'public','review-character')
            self.assertEqual(list((current_root_path/'public').iterdir()),[])
