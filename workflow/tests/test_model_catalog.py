import copy
import unittest

from workflow.common.model_catalog import catalog_overview, read_catalog, read_retained_copy_record, read_survey_report, reconcile_catalog, validate_catalog


class CatalogTest(unittest.TestCase):
    def test_dflash_is_an_optional_separate_model(self):
        from workflow.domains.hermes_agent.resident_worker import DFLASH_MODEL
        item = next(entry for entry in read_catalog()['components'] if entry['id'] == 'qwen3-8-27b-dflash2')
        self.assertEqual(item['path'], DFLASH_MODEL.parent.name)
        self.assertEqual(item['optional_services'], ['hermes-model'])
        self.assertIsNone(item['source'])
        self.assertIsNone(item['revision'])

    def test_audio_models_have_one_declaration_at_current_path(self):
        catalog = read_catalog()
        for identifier, path, repository in (
            ('heartmula', 'heartmula-oss-3b', 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'),
            ('dasheng-audiogen', 'dasheng-audiogen', 'mispeech/Dasheng-AudioGen'),
        ):
            with self.subTest(model=identifier):
                matching = [entry for entry in catalog['components'] if entry.get('source') == repository]
                self.assertEqual(len(matching), 1)
                self.assertEqual((matching[0]['id'], matching[0]['path']), (identifier, path))
                listing = {'models': [{'name': path, 'local_present': True, 'backup_present': False},
                                      {'name': 'catalog-'+identifier, 'relative_path': path,
                                       'local_present': True, 'backup_present': False, 'snapshot_present': True}]}
                result = catalog_overview(catalog, listing, include_manifests=False)
                item = next(entry for entry in result['components'] if entry['declaration']['id'] == identifier)
                self.assertTrue(item['presence']['local_present'])
                self.assertTrue(item['alternate_installations'][0]['snapshot_present'])

    def test_empty_nested_survey_is_available(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from workflow.common.model_catalog_survey import survey_model_root
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'models').mkdir()
            report = root / 'survey.json'
            report.write_text(json.dumps(survey_model_root(root, nested_roots=('models',))))
            survey = read_survey_report(report, root)
            with patch('workflow.common.model_backup_service.list_backup_models', return_value={'models': []}), \
                    patch('workflow.common.model_backup_service.read_model_source', return_value=(root, {})), \
                    patch('workflow.common.model_catalog.read_survey_report', return_value=survey):
                result = catalog_overview(read_catalog(), include_manifests=False)
            self.assertTrue(result['nested_survey_available'])
            self.assertEqual(result['unclassified_nested'], [])

    def test_current_model_children_are_observations_not_unclassified(self):
        from pathlib import Path
        from unittest.mock import patch
        obs = {'files': 1, 'logical_bytes': 10, 'allocated_bytes': 512, 'links': 0, 'errors': 0}
        survey = {'entries': {'animationgpt': obs, 'animationgpt/weights': obs}, 'links': [],
                  'surveyed_roots': ['animationgpt'], 'finished_at': 'then', 'changed': False, 'errors': False}
        with patch('workflow.common.model_backup_service.list_backup_models', return_value={'models': []}), \
                patch('workflow.common.model_backup_service.read_model_source', return_value=(Path('/models'), {})), \
                patch('workflow.common.model_catalog.read_survey_report', return_value=survey):
            result = catalog_overview(read_catalog(), include_manifests=False)
        self.assertEqual(result['surveyed_model_roots'], ['animationgpt'])
        self.assertEqual([x['path'] for x in result['surveyed_model_children']], ['animationgpt/weights'])
        self.assertEqual(result['unclassified_nested'], [])

    def test_nested_survey_reports_unclassified_without_hiding_registered_children(self):
        from pathlib import Path
        from unittest.mock import patch
        obs = {'files': 1, 'logical_bytes': 1, 'allocated_bytes': 512, 'links': 0, 'errors': 0}
        survey = {'entries': {'models': obs, 'models/audio': obs,
                              'models/audio/heartmula': obs, 'models/audio/unknown': obs,
                              'models/mystery': obs}, 'links': [], 'finished_at': 'then',
                  'changed': False, 'errors': False}
        with patch('workflow.common.model_backup_service.list_backup_models', return_value={'models': []}), \
                patch('workflow.common.model_backup_service.read_model_source', return_value=(Path('/models'), {})), \
                patch('workflow.common.model_catalog.read_survey_report', return_value=survey):
            result = catalog_overview(read_catalog(), include_manifests=False)
        self.assertTrue(result['nested_survey_available'])
        self.assertEqual({x['path'] for x in result['unclassified_nested']},
                         {'models/audio/unknown', 'models/mystery'})

    def test_retained_copy_evidence_is_only_a_validated_historical_record(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'transaction.json'
            record = {'source': '.model/example', 'active': '.model/models/example',
                      'retained': '.local/model-catalog/retained/example/original',
                      'verification': 'source-copy-sha256', 'file_count': 3}
            path.write_text(json.dumps(record))
            self.assertEqual(read_retained_copy_record(directory, 'example'),
                             {'kind': 'recorded_source_copy_sha256', 'file_count': 3})
            record['active'] = '.model/models/other'
            path.write_text(json.dumps(record))
            self.assertIsNone(read_retained_copy_record(directory, 'example'))

    def test_unavailable_queue_observation_is_not_reported_as_empty(self):
        from unittest.mock import patch
        from workflow.common.model_catalog import DEFAULT_MODEL_ROOT
        with patch('workflow.common.model_backup_service.list_backup_models', return_value={'models': []}), \
                patch('workflow.common.model_backup_service.read_model_source', return_value=(DEFAULT_MODEL_ROOT, {})), \
                patch('workflow.domains.hermes_agent.management_observer.read_hermes_queue_snapshot', side_effect=OSError('unavailable')):
            result = catalog_overview(read_catalog(), include_manifests=False)
        self.assertEqual(result['activity']['queue']['status'], 'unavailable')
        self.assertEqual(result['activity']['reservations']['status'], 'unavailable')

    def test_retained_original_reports_observation_not_deletion_safety(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            root.mkdir()
            retained = project / '.local/model-catalog/retained/flux-report-vision/original'
            retained.mkdir(parents=True)
            (retained / 'weight').write_bytes(b'model')
            with patch('workflow.common.model_backup_service.list_backup_models', side_effect=ValueError('no config')), \
                    patch('workflow.common.model_catalog.DEFAULT_MODEL_ROOT', root):
                result = catalog_overview(read_catalog(), include_manifests=False)
            item = next(x for x in result['components'] if x['declaration']['id'] == 'flux-report-vision')
            original = next(x for x in item['alternate_installations'] if x.get('retained_original'))
            self.assertEqual(original['storage_observation']['logical_bytes'], 5)
            self.assertNotIn('safe_to_delete', original)
            self.assertIsNone(original['backup_present'])

    def test_survey_requires_matching_root_and_keeps_observation_time(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory) / 'models'
            report_path = Path(directory) / 'survey.json'
            entry = {'path': 'example', 'files': 1, 'logical_bytes': 8,
                     'allocated_bytes': 4096, 'links': 0, 'errors': 0}
            report_path.write_text(json.dumps({'version': 1, 'root': str(root), 'finished_at': 'then',
                                               'entries': [entry], 'changed_paths': ['example']}))
            report = read_survey_report(report_path, root)
            self.assertEqual(report['entries']['example']['allocated_bytes'], 4096)
            self.assertEqual(report['finished_at'], 'then')
            self.assertTrue(report['changed'])
            self.assertIsNone(read_survey_report(report_path, root / 'other'))

    def test_survey_exposes_external_links_without_assuming_their_status(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory) / 'models'
            report_path = Path(directory) / 'survey.json'
            report_path.write_text(json.dumps({'version': 1, 'root': str(root), 'entries': [], 'links': [
                {'path': 'author/stats', 'target': '../base/stats'},
                {'path': 'author/external', 'target': '/etc/passwd'},
                {'path': 'author/escape', 'target': '../../outside'}]}))
            links = read_survey_report(report_path, root)['links']
            self.assertEqual(links, [
                {'path': 'author/stats', 'target': '../base/stats', 'resolved': 'base/stats', 'status': 'unknown'},
                {'path': 'author/external', 'target': '/etc/passwd', 'resolved': '/etc/passwd', 'status': 'unknown'},
                {'path': 'author/escape', 'target': '../../outside', 'resolved': '../outside', 'status': 'unknown'}])

    def test_catalog_keeps_declared_and_unclassified_distinct(self):
        catalog = read_catalog()
        report = {'version': 1, 'finished_at': 'observed', 'entries': [
            {'path': 'kimodo', 'files': 1}, {'path': 'unregistered', 'files': 5}], 'errors': []}
        result = reconcile_catalog(catalog, report)
        kimodo = next(item for item in result['components'] if item['declaration']['id'] == 'kimodo')
        self.assertEqual(kimodo['observation']['files'], 1)
        self.assertEqual(result['unclassified'][0]['path'], 'unregistered')
        self.assertIsNone(next(item for item in result['components'] if item['declaration']['id'] == 'flux-klein')['observation'])

    def test_rejects_duplicate_and_escaping_paths(self):
        base = read_catalog()
        for key, value in [('id', base['components'][0]['id']), ('path', '../outside'), ('path', '/absolute')]:
            data = copy.deepcopy(base)
            data['components'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_catalog(data)

    def test_shared_services_are_preserved(self):
        shared = next(x for x in read_catalog()['components'] if x['id'] == 'wan-fun-pose')
        self.assertIn('kimodo', shared['services'])
        self.assertIn('dwpose', shared['services'])

    def test_optional_service_is_registered_and_must_be_related(self):
        catalog = read_catalog()
        visual = next(item for item in catalog['components'] if item['id'] == 'flux-report-vision')
        self.assertIn('hermes-agent', visual['optional_services'])
        visual['optional_services'] = ['unrelated-service']
        with self.assertRaises(ValueError):
            validate_catalog(catalog)

    def test_ref2va_shared_assets_are_registered(self):
        from workflow.common.model_file_inventory import resolve_model_inventory_paths
        from workflow.generators.minimax_h3_ref2va.assets import REF, FILES
        paths = resolve_model_inventory_paths()['minimax-h3-ref2va']
        self.assertIn(REF, paths)
        self.assertTrue(all(entry[0] in paths for entry in FILES[1:6]))
        components = {item['id']: item for item in read_catalog()['components']}
        for identifier in ('minimax-h3-ref2va', 'minimax-h3-diffusers', 'minimax-h3-i2v', 'minimax-hf-cache'):
            self.assertIn('minimax-h3-ref2va', components[identifier]['services'])

    def test_inventory_counts_overlapping_paths_once_per_service(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from workflow.common.model_file_inventory import list_model_inventory_files
        with TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / '.model/shared'
            shared.mkdir(parents=True)
            weight = shared / 'weight.bin'
            weight.write_bytes(b'12345')
            result = list_model_inventory_files({'first': [shared, weight], 'second': [weight]}, root)
            self.assertEqual((result['first']['count'], result['first']['total_bytes']), (1, 5))
            self.assertEqual((result['second']['count'], result['second']['total_bytes']), (1, 5))

    def test_version_identity_is_declared_separately_from_installation(self):
        result = catalog_overview(read_catalog(), {'models': []}, include_manifests=False)
        flux = next(item for item in result['components'] if item['declaration']['id'] == 'flux-klein')
        version = flux['declared_version']
        self.assertIn(version['source'], version['id'])
        self.assertIn(version['revision'], version['id'])
        self.assertEqual(version['installation_match'], 'unknown')
        unknown = next(item for item in result['components'] if item['declaration']['id'] == 'kimodo')
        self.assertIsNone(unknown['declared_version'])

    def test_declared_pins_match_consumers(self):
        from generators.image.flux_model_prepare import FLUX_MODEL_REPOSITORY, FLUX_MODEL_REVISION
        from workflow.common.hermes_model_download import HERMES_MODEL_REVISION
        components = {item['id']: item for item in read_catalog()['components']}
        self.assertEqual((components['flux-klein']['source'], components['flux-klein']['revision']),
                         (FLUX_MODEL_REPOSITORY, FLUX_MODEL_REVISION))
        self.assertEqual(components['hermes-coding']['revision'], HERMES_MODEL_REVISION)

    def test_overview_keeps_backup_only_and_unknown_unclassified(self):
        listing = {'models': [{'name': 'kimodo', 'local_present': True, 'backup_present': None},
                              {'name': 'old-backup', 'local_present': False, 'backup_present': True}],
                   'backup_error': '연결 확인 실패'}
        result = catalog_overview(read_catalog(), listing, include_manifests=False)
        self.assertEqual(result['unclassified'][0]['name'], 'old-backup')
        self.assertEqual(result['backup_error'], '연결 확인 실패')
        kimodo = next(item for item in result['components'] if item['declaration']['id'] == 'kimodo')
        self.assertIsNone(kimodo['presence']['backup_present'])

    def test_backup_target_identifier_is_not_a_directory(self):
        listing = {'models': [{'name': 'catalog-trellis-image-large', 'local_present': True,
                               'backup_present': False},
                              {'name': 'unclassified-folder', 'local_present': True,
                               'backup_present': None}]}
        result = catalog_overview(read_catalog(), listing, include_manifests=False)
        self.assertEqual([item['name'] for item in result['unclassified']], ['unclassified-folder'])

    def test_alternate_installation_preserves_independent_backup_status(self):
        listing = {'models': [
            {'name': 'trellis-image-large', 'local_present': True, 'backup_present': True},
            {'name': 'catalog-trellis-image-large', 'local_present': False,
             'backup_present': None, 'snapshot_present': True}]}
        result = catalog_overview(read_catalog(), listing, include_manifests=False)
        item = next(x for x in result['components'] if x['declaration']['id'] == 'trellis-image-large')
        self.assertTrue(item['presence']['backup_present'])
        alternate = item['alternate_installations'][0]
        self.assertEqual(alternate['path'], 'models/trellis-image-large')
        self.assertFalse(alternate['local_present'])
        self.assertIsNone(alternate['backup_present'])
        self.assertTrue(alternate['snapshot_present'])

    def test_links_follow_the_relocated_cache_installation(self):
        from pathlib import Path
        from unittest.mock import patch
        listing = {'models': [{'name': 'catalog-minimax-hf-cache', 'local_present': True}]}
        link = {'path': 'cache/huggingface/hub/snapshot/file', 'target': '../blob',
                'resolved': 'cache/huggingface/hub/blob'}
        survey = {'entries': {}, 'links': [link], 'finished_at': 'then', 'changed': False, 'errors': False}
        with patch('workflow.common.model_backup_service.list_backup_models', return_value=listing), \
                patch('workflow.common.model_backup_service.read_model_source', return_value=(Path('/models'), {})), \
                patch('workflow.common.model_catalog.read_survey_report', return_value=survey):
            result = catalog_overview(read_catalog(), include_manifests=False)
        cache = next(item for item in result['components'] if item['declaration']['id'] == 'minimax-hf-cache')
        self.assertEqual(cache['observed_links'], [link])

    def test_manifest_is_declared_evidence_not_verification(self):
        from unittest.mock import patch
        listing = {'models': [{'name': 'kimodo', 'local_present': True, 'backup_present': False}]}
        metadata = {'origin': 'local', 'manifest_state': 'read', 'declared_sources': [],
                    'declared_files': [{'sha256': 'a' * 64}]}
        with patch('workflow.common.model_backup_metadata.model_metadata', return_value=metadata):
            result = catalog_overview(read_catalog(), listing)
        kimodo = next(item for item in result['components'] if item['declaration']['id'] == 'kimodo')
        self.assertEqual(kimodo['installation_metadata']['declared_file_count'], 1)
        self.assertNotIn('verified', kimodo['installation_metadata'])

    def test_relocated_installation_reads_its_own_manifest(self):
        from unittest.mock import patch
        listing = {'models': [{'name': 'hermes-agent', 'local_present': False, 'backup_present': True},
                              {'name': 'catalog-hermes-coding', 'local_present': True, 'backup_present': False}]}
        metadata = {'origin': 'local', 'manifest_state': 'read', 'declared_sources': [],
                    'declared_files': [{'sha256': 'a' * 64}]}
        with patch('workflow.common.model_backup_metadata.model_metadata', return_value=metadata) as read:
            result = catalog_overview(read_catalog(), listing)
        hermes = next(item for item in result['components'] if item['declaration']['id'] == 'hermes-coding')
        self.assertIsNone(hermes['installation_metadata'])
        self.assertEqual(hermes['alternate_installations'][0]['installation_metadata']['declared_file_count'], 1)
        read.assert_called_once_with('catalog-hermes-coding', service_paths={})

    def test_missing_backup_configuration_keeps_local_listing(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as directory:
            (Path(directory) / 'local').mkdir()
            with patch('workflow.common.model_backup_service.list_backup_models', side_effect=ValueError('no config')), \
                    patch('workflow.common.model_catalog.DEFAULT_MODEL_ROOT', Path(directory)):
                result = catalog_overview(read_catalog(), include_manifests=False)
        self.assertEqual(result['unclassified'][0]['name'], 'local')
        self.assertIsNone(result['unclassified'][0]['backup_present'])
        self.assertTrue(result['backup_error'])


if __name__ == '__main__':
    unittest.main()
