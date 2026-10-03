"""전달 사본 없이 고정된 원본을 조회하고 해시 오류를 거절한다."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from tools.review.common.sprite_asset_sources import load_locked_sprite_sources, load_review_sprite_sources


class SpriteAssetSourceTests(unittest.TestCase):
    def test_locked_source_resolution(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            source_relative_path = 'assets/characters/test/animations/v1/test.animation.json'
            source_file_path = temporary_root_path/source_relative_path
            source_file_path.parent.mkdir(parents=True)
            source_file_path.write_text('{}')
            source_hash_value = hashlib.sha256(source_file_path.read_bytes()).hexdigest()
            registry_asset_record = {'managementId': 'sprite.test', 'version': 'v1', 'path': source_relative_path, 'sha256': source_hash_value, 'source': {'repository': 'test'}}
            frontend_repository_path = temporary_root_path/'frontend'
            frontend_repository_path.mkdir()
            target_relative_path = 'assets/characters/test/test.animation.json'
            lock_asset_record = {'path': target_relative_path, 'source_path': source_relative_path, 'sha256': source_hash_value}
            lock_file_path = frontend_repository_path/'sprite-assets.lock.yaml'
            def write_lock_document(current_lock_records):
                lock_file_path.write_text(yaml.safe_dump({'schema_version': 1, 'repository': 'slime-assets', 'files': current_lock_records}))
            with patch('tools.review.common.sprite_asset_sources.load_registered_tiles', return_value=(temporary_root_path, {source_relative_path: registry_asset_record})):
                write_lock_document([lock_asset_record])
                _, locked_source_records = load_locked_sprite_sources(frontend_repository_path)
                self.assertEqual(locked_source_records[target_relative_path][0], source_file_path)
                self.assertFalse((frontend_repository_path/target_relative_path).exists())
                write_lock_document([lock_asset_record, lock_asset_record])
                with self.assertRaisesRegex(ValueError, '중복'):
                    load_locked_sprite_sources(frontend_repository_path)
                write_lock_document([{**lock_asset_record, 'sha256': '0'*64}])
                with self.assertRaisesRegex(ValueError, '잠금 해시'):
                    load_locked_sprite_sources(frontend_repository_path)
                write_lock_document([lock_asset_record])
                source_file_path.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError, '원본 해시'):
                    load_locked_sprite_sources(frontend_repository_path)


class RegisteredCharacterSourceTests(unittest.TestCase):
    def test_unlocked_character_included_and_cutins_excluded(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            registered_source_records = {}
            for current_relative_path in ('assets/characters/female/animations/idle/v1.animation.json', 'assets/characters/female/emotion-cutins/happy.png'):
                current_source_path = temporary_root_path/current_relative_path
                current_source_path.parent.mkdir(parents=True, exist_ok=True)
                current_source_path.write_text('{}')
                registered_source_records[current_relative_path] = {'managementId': current_relative_path, 'version': 'v1', 'sha256': hashlib.sha256(b'{}').hexdigest()}
            with patch('tools.review.common.sprite_asset_sources.load_locked_sprite_sources', return_value=(temporary_root_path/'assets', {})), patch('tools.review.common.sprite_asset_sources.load_registered_tiles', return_value=(temporary_root_path, registered_source_records)):
                _, review_source_records = load_review_sprite_sources(temporary_root_path)
                self.assertEqual(list(review_source_records), ['assets/characters/female/animations/idle/v1.animation.json'])
                (temporary_root_path/next(iter(review_source_records))).write_text('changed')
                with self.assertRaisesRegex(ValueError, '해시 불일치'):
                    load_review_sprite_sources(temporary_root_path)
