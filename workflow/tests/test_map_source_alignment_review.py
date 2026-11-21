"""DB 검수 문서와 에셋 원본의 일치 확인."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import yaml


class MapReviewSourceAlignmentTests(unittest.TestCase):
    def test_database_review_rejects_different_asset_source(self):
        from workflow.common.map_asset_sources import validate_review_bundle_map_sources
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)/'slime-assets'
            current_asset_root.mkdir()
            current_source_path=current_asset_root/'map.yaml'
            current_source_document={'managementId':'map.example','data':{'value':True}}
            current_source_path.write_text(yaml.safe_dump(current_source_document))
            current_database_bundle={'documents':{'city_layouts/example.yaml':current_source_document}}
            with patch('workflow.common.map_asset_sources.load_registered_tiles',return_value=(current_asset_root,{})), patch(
                    'workflow.common.map_asset_sources.resolve_registered_asset',return_value=(current_source_path,{'managementId':'map.example'})), patch(
                    'workflow.domains.map_assets.source_consistency.inspect_hermes_map_sources',return_value={'status':'matched'}):
                validate_review_bundle_map_sources(current_database_bundle)
                current_database_bundle['documents']['city_layouts/example.yaml']={'managementId':'map.example','data':{'value':1}}
                with self.assertRaisesRegex(ValueError,'에셋 원본과 다릅니다'):
                    validate_review_bundle_map_sources(current_database_bundle)

    def test_invalid_asset_sources_never_reach_renderer(self):
        from workflow.common.map_asset_sources import load_registered_map_review
        with patch('workflow.domains.map_assets.source_consistency.inspect_hermes_map_sources',return_value={'status':'mismatch'}),patch(
                'workflow.common.map_asset_sources.build_registered_map_review') as current_render_mock:
            with self.assertRaisesRegex(ValueError,'일치를 확인할 수 없습니다'):
                load_registered_map_review('example')
            current_render_mock.assert_not_called()

    def test_review_reads_asset_document_and_rejects_intervening_change(self):
        import os
        from workflow.common.map_asset_sources import CURRENT_REVIEW_DATABASE_BUNDLE, read_registered_map_data
        with TemporaryDirectory() as current_directory_name:
            current_source_path=Path(current_directory_name)/'example.yaml'
            current_source_document={'managementId':'map.example','data':{'name':'원본'}}
            current_source_path.write_text(yaml.safe_dump(current_source_document,allow_unicode=True))
            current_database_bundle={'documents':{'map_names/example.yaml':current_source_document}}
            current_provenance_record={'managementId':'map.example','version':'asset-v1','sha256':'a'*64}
            current_context_token=CURRENT_REVIEW_DATABASE_BUNDLE.set(current_database_bundle)
            try:
                with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                        'workflow.common.map_asset_sources.resolve_registered_asset',return_value=(current_source_path,current_provenance_record)):
                    current_source_records=[]
                    current_map_data=read_registered_map_data('map_names/example.yaml',current_source_records,(Path(current_directory_name),{}))
                    self.assertEqual(current_map_data,{'name':'원본'})
                    self.assertEqual(current_source_records[0]['version'],'asset-v1')
                    current_source_path.write_text(yaml.safe_dump({'managementId':'map.example','data':{'name':'변경'}},allow_unicode=True))
                    with self.assertRaisesRegex(ValueError,'에셋 원본과 다릅니다'):
                        read_registered_map_data('map_names/example.yaml',[],(Path(current_directory_name),{}))
            finally:
                CURRENT_REVIEW_DATABASE_BUNDLE.reset(current_context_token)

    def test_database_review_uses_registered_city_map_provenance(self):
        import hashlib
        import os
        from workflow.common.map_asset_sources import load_registered_map_review
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_map_root=current_asset_root/'assets/maps'
        current_source_paths=['city_layouts/index.yaml','field_tiles/index.yaml','sprite-display-properties.yaml','city_layouts/stonewarm.yaml']
        current_source_paths.extend(current_path.relative_to(current_map_root).as_posix() for current_path in (current_map_root/'map_names').glob('*.yaml'))
        current_document_records={current_relative_name:yaml.safe_load((current_map_root/current_relative_name).read_text()) for current_relative_name in current_source_paths}
        current_database_bundle={'generation':10,'effectProfiles':{},'imageManifest':{},'documents':current_document_records}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')):
            current_review_record=load_registered_map_review('stonewarm')
        current_source_record=next(current_record for current_record in current_review_record['provenance'] if current_record['source']=='assets/maps/city_layouts/stonewarm.yaml')
        self.assertNotEqual(current_source_record['version'],'database')
        self.assertEqual(current_source_record['sha256'],hashlib.sha256((current_map_root/'city_layouts/stonewarm.yaml').read_bytes()).hexdigest())
        self.assertNotIn('contentGeneration',current_review_record)

    def test_database_menu_matches_registered_asset_names(self):
        import os
        from workflow.common.map_asset_sources import load_review_map_menu
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_map_root=current_asset_root/'assets/maps'
        current_source_paths=['city_layouts/index.yaml','field_tiles/index.yaml','sprite-display-properties.yaml']
        current_source_paths.extend(current_path.relative_to(current_map_root).as_posix() for current_path in (current_map_root/'map_names').glob('*.yaml'))
        current_document_records={current_relative_name:yaml.safe_load((current_map_root/current_relative_name).read_text()) for current_relative_name in current_source_paths}
        current_database_bundle={'documents':current_document_records}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')):
            current_menu_rows=load_review_map_menu()
        current_menu_by_id={current_menu_row['id']:current_menu_row for current_menu_row in current_menu_rows}
        self.assertEqual(len(current_menu_rows),30)
        self.assertEqual(current_menu_by_id['stonewarm']['name'],current_document_records['map_names/stonewarm.yaml']['data']['ko'])
        self.assertEqual(current_menu_by_id['stonewarm']['kind'],'town')

    def test_file_field_editor_rejects_source_changed_after_registration_check(self):
        import hashlib
        import os
        import tempfile
        from workflow.domains.map_assets import map_editor
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_asset_root = Path(current_directory_name)
            current_relative_paths = ('assets/maps/field_tiles/test.yaml', 'assets/maps/terrain/maps/test.yaml', 'assets/maps/sprite-display-properties.yaml')
            current_expected_bytes = b'data: {}\n'
            for current_relative_path in current_relative_paths:
                current_file_path = current_asset_root / current_relative_path
                current_file_path.parent.mkdir(parents=True, exist_ok=True)
                current_file_path.write_bytes(current_expected_bytes)
            current_change_switch = [False]
            def resolve_changed_source(current_relative_path, current_root_value, current_records_value, current_prefix_value):
                current_file_path = current_root_value / current_relative_path
                if current_change_switch[0] and current_relative_path == current_relative_paths[0]:
                    current_file_path.write_bytes(b'data: {changed: true}\n')
                return current_file_path, {'sha256': hashlib.sha256(current_expected_bytes).hexdigest()}
            with patch.dict(os.environ, {'SLIME_CONTENT_STORAGE': 'files'}), patch.object(map_editor, 'load_registered_tiles', return_value=(current_asset_root, {})), patch.object(map_editor, 'resolve_registered_asset', side_effect=resolve_changed_source):
                current_result_value = map_editor.read_map_editor_snapshot('test')
                self.assertEqual(current_result_value[2], [{'data': {}}, {'data': {}}])
                self.assertEqual(current_result_value[4], hashlib.sha256(current_expected_bytes * 3).hexdigest())
                current_change_switch[0] = True
                with self.assertRaisesRegex(ValueError, '읽는 중 변경'):
                    map_editor.read_map_editor_snapshot('test')

    def test_database_field_editor_reads_actual_assets_and_hashes(self):
        import hashlib
        import json
        import os
        from workflow.domains.map_assets.map_editor import read_map_editor_snapshot
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_map_root=current_asset_root/'assets/maps'
        current_document_paths=['field_tiles/moss-clearing.yaml','terrain/maps/moss-clearing.yaml','sprite-display-properties.yaml']
        current_documents={current_document_path:yaml.safe_load((current_map_root/current_document_path).read_text()) for current_document_path in current_document_paths}
        current_database_bundle={'generation':12,'revisions':{current_document_path:3 for current_document_path in current_document_paths},'documents':current_documents}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',return_value=current_database_bundle):
            current_root_value,current_source_paths,current_result_documents,current_source_bytes,current_revision_value=read_map_editor_snapshot('moss-clearing')
        self.assertEqual(current_root_value,current_asset_root)
        self.assertEqual(current_result_documents,[current_documents[current_document_path] for current_document_path in current_document_paths[:2]])
        current_revision_record=json.loads(current_revision_value)
        self.assertEqual(current_revision_record['generation'],12)
        for current_document_path in current_document_paths:
            self.assertEqual(current_revision_record['asset_sha256'][current_document_path],hashlib.sha256((current_map_root/current_document_path).read_bytes()).hexdigest())
        self.assertEqual(current_source_bytes[current_source_paths[0]],current_source_paths[0].read_bytes())

    def test_database_city_editor_reads_registered_source(self):
        import os
        from workflow.domains.map_assets.city_editor import read_city_editor_snapshot
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_map_root=current_asset_root/'assets/maps'
        current_document_paths=['city_layouts/stonewarm.yaml','sprite-display-properties.yaml']
        current_documents={current_document_path:yaml.safe_load((current_map_root/current_document_path).read_text()) for current_document_path in current_document_paths}
        current_database_bundle={'generation':12,'revisions':{'city_layouts/stonewarm.yaml':3},'documents':current_documents}
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.city_editor.execute_content_api_request',return_value=current_database_bundle):
            current_snapshot_value=read_city_editor_snapshot({'map':'stonewarm'})
        self.assertEqual(current_snapshot_value['document'],current_documents['city_layouts/stonewarm.yaml'])
        self.assertEqual(current_snapshot_value['properties'],current_documents['sprite-display-properties.yaml']['data'])
        self.assertEqual((current_snapshot_value['generation'],current_snapshot_value['revision']),(12,3))
        current_database_bundle['documents']['city_layouts/stonewarm.yaml']['data']['cityId']='changed'
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.city_editor.execute_content_api_request',return_value=current_database_bundle):
            with self.assertRaisesRegex(ValueError,'에셋 원본과 다릅니다'):
                read_city_editor_snapshot({'map':'stonewarm'})

    def test_database_editor_auxiliary_data_uses_registered_source(self):
        import copy
        import os
        from workflow.domains.map_assets.map_editor import read_map_editor_source_data
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_map_root=current_asset_root/'assets/maps'
        current_relative_path='field_tiles/codes.yaml'
        current_source_document=yaml.safe_load((current_map_root/current_relative_path).read_text())
        current_database_document=copy.deepcopy(current_source_document)
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',return_value=current_database_document):
            self.assertEqual(read_map_editor_source_data(current_asset_root,current_relative_path),current_source_document['data'])
            current_database_document['data']['g']='wrong'
            with self.assertRaisesRegex(ValueError,'에셋 원본과 다릅니다'):
                read_map_editor_source_data(current_asset_root,current_relative_path)

    def test_real_city_preview_plan_reads_registered_files_without_writing(self):
        import copy
        import hashlib
        from workflow.domains.map_assets import city_editor
        current_asset_root=Path(__file__).resolve().parents[3]/'slime-assets'
        current_source_path=current_asset_root/'assets/maps/city_layouts/stonewarm.yaml'
        current_registry_path=current_asset_root/'asset-registry.yaml'
        current_backend_path=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
        current_file_hashes={current_path:hashlib.sha256(current_path.read_bytes()).hexdigest() for current_path in (current_source_path,current_registry_path,current_backend_path)}
        current_document_value=yaml.safe_load(current_source_path.read_bytes())
        current_snapshot_record={'map':'stonewarm','generation':7,'revision':2,'document':current_document_value,'properties':{}}
        current_changed_document=copy.deepcopy(current_document_value)
        current_changed_document['data']['safeTown']=not current_document_value['data']['safeTown']
        with patch.dict('os.environ',{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(city_editor,'read_city_editor_snapshot',return_value=current_snapshot_record):
            current_plan_summary=city_editor.inspect_city_source_plan(current_snapshot_record,current_changed_document,'a'*64)
        self.assertEqual(current_plan_summary['status'],'available')
        self.assertEqual(current_plan_summary['before_sha256'],current_file_hashes[current_source_path])
        self.assertNotEqual(current_plan_summary['after_sha256'],current_plan_summary['before_sha256'])
        for current_path,current_expected_hash in current_file_hashes.items():
            self.assertEqual(hashlib.sha256(current_path.read_bytes()).hexdigest(),current_expected_hash)

    def test_map_update_plan_preserves_files_and_checks_both_manifests(self):
        import hashlib
        from workflow.domains.map_assets.map_editor import prepare_registered_map_update_files
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)/'slime-assets'
            current_source_path=current_asset_root/'assets/maps/city_layouts/example.yaml'
            current_source_path.parent.mkdir(parents=True)
            current_source_bytes=b'managementId: map.example\ndata: {value: 1}\n'
            current_source_path.write_bytes(current_source_bytes)
            current_old_hash=hashlib.sha256(current_source_bytes).hexdigest()
            current_relative_name='assets/maps/city_layouts/example.yaml'
            current_registry_path=current_asset_root/'asset-registry.yaml'
            current_lock_path=Path(current_directory_name)/'map-data.lock.yaml'
            current_registry_path.write_text(yaml.safe_dump({'assets':[{'path':current_relative_name,'sha256':current_old_hash}]}))
            current_lock_path.write_text(yaml.safe_dump({'files':[{'path':current_relative_name,'sha256':current_old_hash}]}))
            current_inputs={current_source_path:current_source_bytes,current_registry_path:current_registry_path.read_bytes(),current_lock_path:current_lock_path.read_bytes()}
            current_pending_files=prepare_registered_map_update_files(current_asset_root,[current_source_path],[{'managementId':'map.example','data':{'value':2}}],current_inputs,[current_registry_path,current_lock_path])
            current_new_hash=hashlib.sha256(current_pending_files[current_source_path]).hexdigest()
            self.assertEqual(yaml.safe_load(current_pending_files[current_registry_path])['assets'][0]['sha256'],current_new_hash)
            self.assertEqual(yaml.safe_load(current_pending_files[current_lock_path])['files'][0]['sha256'],current_new_hash)
            self.assertEqual(current_source_path.read_bytes(),current_source_bytes)
            current_inputs[current_lock_path]=yaml.safe_dump({'files':[{'path':current_relative_name,'sha256':'0'*64}]}).encode()
            with self.assertRaisesRegex(ValueError,'해시 불일치'):
                prepare_registered_map_update_files(current_asset_root,[current_source_path],[{'managementId':'map.example','data':{'value':2}}],current_inputs,[current_registry_path,current_lock_path])
            self.assertEqual(current_source_path.read_bytes(),current_source_bytes)

    def test_map_review_classification_uses_verified_map_record(self):
        from workflow.build_block_map_review import build_registered_map_review
        with patch('workflow.common.map_asset_sources.load_review_map_identifiers',side_effect=AssertionError('별도 인덱스 조회 금지')),patch(
                'workflow.common.map_asset_sources.load_registered_map_review',return_value={'id':'example','safeTown':True}):
            self.assertEqual(build_registered_map_review('example',current_validate_placement=False)['reviewLabel'],'도시맵 검수')
        with patch('workflow.common.map_asset_sources.load_registered_map_review',return_value={'id':'example','safeTown':'true'}):
            with self.assertRaisesRegex(ValueError,'도시 구분'):
                build_registered_map_review('example',current_validate_placement=False)

    def test_database_mode_world_map_uses_asset_sources_without_database(self):
        import os
        from workflow.domains.world_map.catalog import load_world_review_catalog
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')):
            current_world_record=load_world_review_catalog()
        self.assertEqual(len(current_world_record['maps']),30)
        self.assertTrue(any(current_record['source']=='assets/maps/world-map.yaml' for current_record in current_world_record['provenance']))
        self.assertTrue(all(current_record.get('version')!='database' for current_record in current_world_record['provenance']))

    def test_world_map_rejects_lock_changes_during_load(self):
        from workflow.domains.world_map.catalog import load_world_review_catalog
        with TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)/'slime-assets'
            current_backend_root=Path(current_directory_name)/'slime-backend'
            current_asset_root.mkdir()
            current_backend_root.mkdir()
            (current_asset_root/'asset-registry.yaml').write_bytes(b'registry')
            current_lock_path=current_backend_root/'map-data.lock.yaml'
            current_lock_path.write_bytes(b'before')
            def change_map_lock_during_build():
                current_lock_path.write_bytes(b'after')
                return {'maps':[]}
            with patch('workflow.common.map_asset_sources.load_registered_tiles',return_value=(current_asset_root,{})),patch(
                    'workflow.domains.map_assets.source_consistency.inspect_hermes_map_sources',return_value={'status':'matched'}),patch(
                    'workflow.domains.world_map.catalog.build_world_asset_catalog',side_effect=change_map_lock_during_build):
                with self.assertRaisesRegex(ValueError,'조회 중 변경'):
                    load_world_review_catalog()

    def test_database_mode_map_review_http_uses_registered_assets(self):
        import json
        import os
        from workflow.common.map_asset_http import read_map_asset_response
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')):
            for current_map_name,current_expected_town in (('stonewarm',True),('moss-clearing',False)):
                current_response_bytes,current_content_type=read_map_asset_response('/management/map-assets/maps/'+current_map_name)
                current_response_record=json.loads(current_response_bytes)
                self.assertIn('application/json',current_content_type)
                self.assertEqual(current_response_record['id'],current_map_name)
                self.assertIs(current_response_record['safeTown'],current_expected_town)
                self.assertNotIn('imageManifest',current_response_record)
                self.assertTrue(all(current_source_record.get('version')!='database' for current_source_record in current_response_record['provenance']))

    test_database_mode_map_review_http_uses_registered_assets.regression_timeout_seconds=120

    def test_field_region_reads_asset_without_editor_or_database(self):
        import os
        from workflow.domains.hermes_agent.field_map_operations import read_hermes_field_region
        with patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':'database'}),patch(
                'workflow.domains.map_assets.database_client.execute_content_api_request',side_effect=AssertionError('DB 조회 금지')),patch(
                'workflow.domains.hermes_agent.field_map_operations.call_field_map_editor',side_effect=AssertionError('편집기 호출 금지')):
            current_region_value=read_hermes_field_region({'map':'moss-clearing','width':2,'height':2,'limit':1})
            self.assertEqual(len(current_region_value['cells']),4)
            self.assertTrue(current_region_value['revision'].startswith('asset:'))
            self.assertIn('편집 리비전이 아닙니다',current_region_value['note'])
            if current_region_value['object_next_offset'] is not None:
                current_next_value=read_hermes_field_region({'map':'moss-clearing','revision':current_region_value['revision'],'offset':current_region_value['object_next_offset'],'limit':1})
                self.assertEqual(current_next_value['revision'],current_region_value['revision'])
