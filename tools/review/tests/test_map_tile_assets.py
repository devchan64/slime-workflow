"""맵 타일의 에셋 원본 검증과 잘못된 원본 거절."""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_tile, resolve_registered_sprite


class MapTileAssetTests(unittest.TestCase):
    def test_source_hash_and_escape_rejection(self):
        with TemporaryDirectory() as temporary_asset_directory:
            asset_repository_path = Path(temporary_asset_directory)
            source_relative_path = 'assets/tiles/buildings/roof/test.png'
            source_texture_path = asset_repository_path / source_relative_path
            source_texture_path.parent.mkdir(parents=True)
            source_texture_path.write_bytes(b'approved image')
            current_asset_record = {'managementId': 'tile.test.roof', 'version': '1', 'path': source_relative_path, 'sha256': hashlib.sha256(b'approved image').hexdigest(), 'source': {'repository': 'slime-workflow'}}
            (asset_repository_path / 'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version': 1, 'assets': [current_asset_record]}))
            with patch.dict(os.environ, {'SLIME_ASSETS_ROOT': str(asset_repository_path)}):
                loaded_repository_path, registered_tile_records = load_registered_tiles()
            resolved_texture_path, texture_provenance_record = resolve_registered_tile(source_relative_path, loaded_repository_path, registered_tile_records)
            self.assertEqual(resolved_texture_path, source_texture_path)
            self.assertEqual(texture_provenance_record['version'], '1')
            with self.assertRaisesRegex(ValueError, '경로 오류'):
                resolve_registered_tile('assets/tiles/../../secret.png', loaded_repository_path, registered_tile_records)
            with self.assertRaisesRegex(ValueError, '미등록'):
                resolve_registered_tile('assets/tiles/missing.png', loaded_repository_path, registered_tile_records)
            source_texture_path.write_bytes(b'changed image')
            with self.assertRaisesRegex(ValueError, '해시 불일치'):
                resolve_registered_tile(source_relative_path, loaded_repository_path, registered_tile_records)

    def test_duplicate_yaml_key_rejected(self):
        with TemporaryDirectory() as temporary_asset_directory:
            Path(temporary_asset_directory, 'asset-registry.yaml').write_text('schema_version: 1\nschema_version: 1\nassets: []\n')
            with patch.dict(os.environ, {'SLIME_ASSETS_ROOT': temporary_asset_directory}):
                with self.assertRaisesRegex(ValueError, '중복 키'):
                    load_registered_tiles()

    def test_sprite_metadata_hash_and_tile_scope_rejection(self):
        with TemporaryDirectory() as temporary_asset_directory:
            asset_repository_path=Path(temporary_asset_directory)
            sprite_relative_path='assets/sprites/characters/default/idle.animation.json'
            sprite_source_path=asset_repository_path/sprite_relative_path
            sprite_source_path.parent.mkdir(parents=True)
            sprite_source_path.write_bytes(b'{}')
            sprite_registry_record={'managementId':'sprite.test.animation','version':'1','path':sprite_relative_path,'sha256':hashlib.sha256(b'{}').hexdigest(),'source':{'repository':'slime-frontend'}}
            (asset_repository_path/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':[sprite_registry_record]}))
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(asset_repository_path)}):
                resolved_sprite_path,sprite_provenance_record=resolve_registered_sprite(sprite_relative_path)
                self.assertEqual(resolved_sprite_path,sprite_source_path)
                self.assertEqual(sprite_provenance_record['sha256'],sprite_registry_record['sha256'])
                with self.assertRaisesRegex(ValueError,'경로 오류'):
                    resolve_registered_sprite('assets/tiles/test.png')
                with self.assertRaisesRegex(ValueError,'경로 오류'):
                    resolve_registered_sprite('assets/sprites/../../outside.json')
                sprite_source_path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'해시 불일치'):
                    resolve_registered_sprite(sprite_relative_path)
