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

    def test_city_source_alignment_compares_registered_original_to_database_document(self):
        from tools.review.domains.map_assets.source_consistency import inspect_city_source_alignment
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)
            current_source_path=current_asset_root/'assets/maps/city_layouts/example.yaml'
            current_source_path.parent.mkdir(parents=True)
            current_document_record={'managementId':'config.city-layouts.example','data':{'cityId':'example','version':1}}
            current_source_path.write_text(yaml.safe_dump(current_document_record))
            current_hash_value=hashlib.sha256(current_source_path.read_bytes()).hexdigest()
            current_relative_path='assets/maps/city_layouts/example.yaml'
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':[{'managementId':'config.city-layouts.example','version':'1','path':current_relative_path,'sha256':current_hash_value,'source':{}}]}))
            current_lock_path=current_asset_root/'map-data.lock.yaml'
            current_lock_path.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':[{'path':current_relative_path,'sha256':current_hash_value}]}))
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',current_document_record)['status'],'matched')
            from tools.review.domains.map_assets.source_consistency import read_registered_city_source
            current_source_value=read_registered_city_source(current_asset_root,current_lock_path,'example')
            self.assertEqual(current_source_value['document'],current_document_record)
            self.assertEqual(current_source_value['source_sha256'],current_hash_value)
            self.assertNotIn(str(current_asset_root),str(current_source_value))
            with self.assertRaises(ValueError):read_registered_city_source(current_asset_root,current_lock_path,'../secret')
            current_boolean_record={'managementId':'config.city-layouts.example','data':{'cityId':'example','version':True}}
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',current_boolean_record)['status'],'mismatch')
            current_invalid_record={'managementId':'config.city-layouts.example','data':{'cityId':'example',1:'invalid-key'}}
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',current_invalid_record)['status'],'unavailable')
            current_cyclic_record={'managementId':'config.city-layouts.example','data':{'cityId':'example'}}
            current_cyclic_record['data']['cycle']=current_cyclic_record
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',current_cyclic_record)['status'],'unavailable')
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',{'different':True})['status'],'mismatch')
            current_source_path.write_text('data: {}\n')
            self.assertEqual(inspect_city_source_alignment(current_asset_root,current_lock_path,'example',current_document_record)['status'],'unavailable')
            with self.assertRaises(ValueError):read_registered_city_source(current_asset_root,current_lock_path,'example')

    def test_field_alignment_compares_both_documents_and_detects_invalid_registry(current_test_case):
        from tools.review.domains.map_assets.source_consistency import inspect_field_source_alignment
        with TemporaryDirectory() as current_directory_name:
            current_root=Path(current_directory_name)
            current_paths=['assets/maps/field_tiles/example.yaml','assets/maps/terrain/maps/example.yaml']
            current_values=[{'rows':['KK']},{'columns':2,'blocked':[]}]
            current_entries=[]
            for current_index,(current_path,current_data) in enumerate(zip(current_paths,current_values)):
                current_file=current_root/current_path
                current_file.parent.mkdir(parents=True,exist_ok=True)
                current_file.write_text(yaml.safe_dump({'data':current_data}))
                current_entries.append({'managementId':'field-example-'+str(current_index),'version':'1','path':current_path,'sha256':hashlib.sha256(current_file.read_bytes()).hexdigest(),'source':{}})
            (current_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_entries}))
            current_lock=current_root/'map-data.lock.yaml'
            current_lock.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':[{'path':item['path'],'sha256':item['sha256']} for item in current_entries]}))
            current_test_case.assertEqual(inspect_field_source_alignment(current_root,current_lock,'example',*current_values)['status'],'matched')
            current_test_case.assertEqual(inspect_field_source_alignment(current_root,current_lock,'example',current_values[0],{'columns':3,'blocked':[]})['status'],'mismatch')
            (current_root/current_paths[0]).write_text('data: {}')
            current_test_case.assertEqual(inspect_field_source_alignment(current_root,current_lock,'example',*current_values)['status'],'unavailable')

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
