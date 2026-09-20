"""프론트엔드 애니메이션 탐색과 원본 좌표·파일 경계 검증."""
import json
import yaml
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from tools.review.build_frontend_review import load_animation_review, load_animation_labels, read_source_metadata, REVIEW_DIRECTION_NAMES
from tools.review.serve import parse_review_arguments, prepare_review_directory
from unittest.mock import patch


class FrontendReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary_asset_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_asset_directory.cleanup)
        self.frontend_asset_root = Path(self.temporary_asset_directory.name)
        self.animation_metadata_path = self.frontend_asset_root/'idle.animation.json'
        Image.new('RGBA', (16, 16)).save(self.frontend_asset_root/'idle.png')
        self.animation_source_data = {'animationId': 'monster.test.idle', 'version': '1', 'sheet': {'width': 16, 'height': 16}, 'frames': [], 'clips': []}
        for current_direction_name in REVIEW_DIRECTION_NAMES:
            current_frame_identifier = current_direction_name+'.0'
            self.animation_source_data['frames'].append({'frameId': current_frame_identifier, 'rect': {'x': 0, 'y': 0, 'width': 16, 'height': 16}, 'anchor': {'x': 7.5, 'y': 12.25}})
            self.animation_source_data['clips'].append({'clipId': 'idle.'+current_direction_name, 'action': 'idle', 'direction': current_direction_name, 'frames': [{'frameId': current_frame_identifier, 'durationMs': 250}], 'loop': True, 'nextClipId': None})
        self.write_source_fixture()

    def write_source_fixture(self):
        self.animation_metadata_path.write_text(json.dumps(self.animation_source_data))

    def test_original_fractional_coordinates_survive(self):
        original_metadata_bytes = self.animation_metadata_path.read_bytes()
        review_frame_records, review_source_metadata, source_image_paths = load_animation_review(self.frontend_asset_root, self.animation_metadata_path)
        self.assertEqual(len(review_frame_records), 4)
        self.assertEqual(review_frame_records[0]['anchor'], {'x': 7.5, 'y': 12.25})
        self.assertEqual(review_source_metadata['frameDurationMs'], 250)
        self.assertEqual(len(source_image_paths), 1)
        self.assertEqual(self.animation_metadata_path.read_bytes(), original_metadata_bytes)

    def test_missing_image_is_explicit_failure(self):
        (self.frontend_asset_root/'idle.png').unlink()
        with self.assertRaisesRegex(ValueError, '파일 누락'):
            load_animation_review(self.frontend_asset_root, self.animation_metadata_path)

    def test_duplicate_and_unknown_fields_fail(self):
        self.animation_metadata_path.write_text('{"version":"1","version":"2"}')
        with self.assertRaisesRegex(ValueError, '중복 필드'):
            read_source_metadata(self.animation_metadata_path)
        self.animation_source_data['unknown'] = True
        self.write_source_fixture()
        with self.assertRaisesRegex(ValueError, '알 수 없는 필드'):
            load_animation_review(self.frontend_asset_root, self.animation_metadata_path)

    def test_invalid_frame_bounds_fail(self):
        self.animation_source_data['frames'][0]['rect']['width'] = 17
        self.write_source_fixture()
        with self.assertRaisesRegex(ValueError, '시트 경계'):
            load_animation_review(self.frontend_asset_root, self.animation_metadata_path)

    def test_external_image_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside_directory_name:
            outside_image_path = Path(outside_directory_name)/'outside.png'
            Image.new('RGBA', (16, 16)).save(outside_image_path)
            (self.frontend_asset_root/'idle.png').unlink()
            (self.frontend_asset_root/'idle.png').symlink_to(outside_image_path)
            with self.assertRaisesRegex(ValueError, '루트 밖'):
                load_animation_review(self.frontend_asset_root, self.animation_metadata_path)

    def test_source_sheet_hash_is_checked(self):
        (self.frontend_asset_root/'source.json').write_text(json.dumps({'sheets': [{'direction': current_direction_name, 'image': 'idle.png', 'sha256': 'incorrect'} for current_direction_name in REVIEW_DIRECTION_NAMES]}))
        with self.assertRaisesRegex(ValueError, '해시 불일치'):
            load_animation_review(self.frontend_asset_root, self.animation_metadata_path)

    def test_korean_labels_are_loaded_from_data(self):
        (self.frontend_asset_root/'animation-labels.yaml').write_text('schemaVersion: 1\nanimations:\n  - animationId: monster.test.idle\n    displayNameKo: 시험 몬스터 · 대기\n')
        self.assertEqual(load_animation_labels(self.frontend_asset_root), {'monster.test.idle': '시험 몬스터 · 대기'})

    def test_invalid_label_records_fail(self):
        for invalid_label_value in ('', '   ', 123, 'English only', ' 줄바꿈', '이름\n두 줄'):
            with self.subTest(label=invalid_label_value):
                (self.frontend_asset_root/'animation-labels.yaml').write_text(yaml.safe_dump({'schemaVersion': 1, 'animations': [{'animationId': 'monster.test.idle', 'displayNameKo': invalid_label_value}]}, allow_unicode=True))
                with self.assertRaisesRegex(ValueError, 'displayNameKo'):
                    load_animation_labels(self.frontend_asset_root)

    def test_duplicate_label_fields_and_ids_fail(self):
        for label_catalog_text in ('schemaVersion: 1\nschemaVersion: 1\nanimations: []', 'schemaVersion: 1\nanimations:\n  - {animationId: monster.test.idle, displayNameKo: 시험}\n  - {animationId: monster.test.idle, displayNameKo: 시험}'):
            (self.frontend_asset_root/'animation-labels.yaml').write_text(label_catalog_text)
            with self.assertRaisesRegex(ValueError, '중복'):
                load_animation_labels(self.frontend_asset_root)

    def test_repository_option_calls_snapshot_builder(self):
        parsed_argument_values = parse_review_arguments(['--frontend-repo', str(self.frontend_asset_root)])
        with patch('tools.review.build_frontend_review.build_frontend_review', return_value=Path('/tmp/review-output')) as snapshot_builder_mock:
            self.assertEqual(prepare_review_directory(parsed_argument_values), Path('/tmp/review-output'))
            snapshot_builder_mock.assert_called_once_with(self.frontend_asset_root)


if __name__ == '__main__':
    unittest.main()
