"""맵 원본 상태 조회는 임시 원장만 사용한다."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import yaml

from tools.review.domains.map_assets.source_consistency import inspect_hermes_map_sources


class HermesMapSourceObserverTests(unittest.TestCase):
    def test_map_source_observation_rejects_concurrent_metadata_changes(self):
        from unittest.mock import patch
        for current_changed_name in ('asset-registry.yaml','map-data.lock.yaml'):
            with self.subTest(current_changed_name=current_changed_name),TemporaryDirectory() as current_directory_name:
                current_root=Path(current_directory_name)
                current_map_path=current_root/'assets/maps/example.yaml'
                current_map_path.parent.mkdir(parents=True)
                current_map_path.write_text('data: {}\n')
                current_hash_value=hashlib.sha256(current_map_path.read_bytes()).hexdigest()
                current_relative_name='assets/maps/example.yaml'
                current_registry_record={'schema_version':1,'assets':[{'managementId':'map-example','version':'1','path':current_relative_name,'sha256':current_hash_value,'source':{}}]}
                (current_root/'asset-registry.yaml').write_text(yaml.safe_dump(current_registry_record))
                current_lock_path=current_root/'map-data.lock.yaml'
                current_lock_path.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':[{'path':current_relative_name,'sha256':current_hash_value}]}))
                current_original_read=Path.read_bytes
                current_read_counts=[]
                def mutate_metadata_after_read(current_read_path):
                    current_read_bytes=current_original_read(current_read_path)
                    if current_read_path.name==current_changed_name:
                        current_read_counts.append(1)
                        if len(current_read_counts)==(2 if current_changed_name=='asset-registry.yaml' else 1):
                            current_read_path.write_bytes(current_read_bytes+b'\n# changed\n')
                    return current_read_bytes
                with patch.object(Path,'read_bytes',mutate_metadata_after_read):
                    self.assertEqual(inspect_hermes_map_sources(current_root,current_lock_path)['status'],'unavailable')

    def test_map_sources_distinguish_match_mismatch_and_unavailable(self):
        with TemporaryDirectory() as current_temporary_directory:
            current_root = Path(current_temporary_directory)
            current_map_path = current_root / 'assets/maps/city_layouts/example.yaml'
            current_map_path.parent.mkdir(parents=True)
            current_map_path.write_text('data: {}\n')
            current_hash = hashlib.sha256(current_map_path.read_bytes()).hexdigest()
            current_relative = 'assets/maps/city_layouts/example.yaml'
            current_registry = {'schema_version':1,'assets':[{'managementId':'map-example','version':'1','path':current_relative,'sha256':current_hash,'source':{}}]}
            (current_root / 'asset-registry.yaml').write_text(yaml.safe_dump(current_registry))
            current_lock = current_root / 'map-data.lock.yaml'
            current_lock.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':[{'path':current_relative,'sha256':current_hash}]}))
            self.assertEqual(inspect_hermes_map_sources(current_root,current_lock)['status'],'matched')
            from unittest.mock import patch
            current_original_read=Path.read_bytes
            current_map_reads=[]
            def mutate_map_after_first_read(current_read_path):
                current_read_value=current_original_read(current_read_path)
                if current_read_path==current_map_path:
                    current_map_reads.append(1)
                    if len(current_map_reads)==1:current_map_path.write_text('data: {raced: true}\n')
                return current_read_value
            with patch.object(Path,'read_bytes',mutate_map_after_first_read):
                self.assertEqual(inspect_hermes_map_sources(current_root,current_lock)['status'],'unavailable')
            current_map_path.write_text('data: {}\n')
            current_registry['schema_version']=True
            (current_root/'asset-registry.yaml').write_text(yaml.safe_dump(current_registry))
            self.assertEqual(inspect_hermes_map_sources(current_root,current_lock)['status'],'unavailable')
            current_registry['schema_version']=1
            (current_root/'asset-registry.yaml').write_text(yaml.safe_dump(current_registry))
            current_map_path.write_text('data: {changed: true}\n')
            current_result = inspect_hermes_map_sources(current_root,current_lock)
            self.assertEqual((current_result['status'],current_result['mismatched_files']),('mismatch',1))
            self.assertEqual(current_result['mismatched_paths'],[current_relative])
            self.assertFalse(current_result['paths_truncated'])
            current_lock.write_text('schema_version: 1\nschema_version: 1\n')
            self.assertEqual(inspect_hermes_map_sources(current_root,current_lock)['status'],'unavailable')
