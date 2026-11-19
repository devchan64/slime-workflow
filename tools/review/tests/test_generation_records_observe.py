"""원본 이력의 비파괴·페이지 관측을 확인한다."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.review.common.generation_records import observe_generation_history_records


class GenerationRecordsObserveTests(unittest.TestCase):
    def test_hidden_records_pagination_and_snapshot_changes(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_jobs_root=current_root_path/'jobs'
            current_history_root.mkdir()
            current_jobs_root.mkdir()
            current_job_identifiers=['2026-11-18_12-00-00-aaaaaaaa','2026-11-18_12-01-00-bbbbbbbb','2026-11-18_12-02-00-cccccccc']
            for current_job_identifier in current_job_identifiers:
                current_job_root=current_jobs_root/current_job_identifier
                current_job_root.mkdir()
                (current_job_root/'request.json').write_text(json.dumps({'prompt':'private'}))
                (current_job_root/'status.json').write_text(json.dumps({'status':'completed','private':'secret'}))
            (current_jobs_root/current_job_identifiers[0]/'.history-deleted').touch()
            current_first_page=observe_generation_history_records(current_history_root,current_jobs_root,{'limit':1})
            self.assertEqual(current_first_page['total'],2)
            self.assertEqual(current_first_page['records'],[{'id':current_job_identifiers[2],'recorded_status':'completed','status_source':'job'}])
            self.assertNotIn('private',str(current_first_page))
            current_next_page=observe_generation_history_records(current_history_root,current_jobs_root,{'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            self.assertEqual(current_next_page['records'][0]['id'],current_job_identifiers[1])
            self.assertIsNone(current_next_page['next_offset'])
            with self.assertRaises(ValueError):
                observe_generation_history_records(current_history_root,current_jobs_root,{'offset':1})
            (current_jobs_root/current_job_identifiers[1]/'.history-deleted').touch()
            with self.assertRaises(ValueError):
                observe_generation_history_records(current_history_root,current_jobs_root,{'offset':1,'snapshot':current_first_page['snapshot']})

    def test_corrupt_unindexed_job_does_not_hide_other_records(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_jobs_root=current_root_path/'jobs'
            current_history_root.mkdir()
            current_job_identifiers=['2026-11-18_12-00-00-aaaaaaaa','2026-11-18_12-01-00-bbbbbbbb']
            for current_job_identifier in current_job_identifiers:
                current_job_root=current_jobs_root/current_job_identifier
                current_job_root.mkdir(parents=True)
                (current_job_root/'request.json').write_text('invalid request')
                (current_job_root/'status.json').write_text('invalid status' if current_job_identifier==current_job_identifiers[1] else json.dumps({'status':'completed'}))
            current_result_value=observe_generation_history_records(current_history_root,current_jobs_root,{})
            self.assertEqual(current_result_value['records'],[{'id':current_job_identifiers[1],'recorded_status':'unknown','status_source':'unavailable'},{'id':current_job_identifiers[0],'recorded_status':'completed','status_source':'job'}])

    def test_unreadable_and_legacy_index_do_not_hide_valid_records(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_history_root.mkdir()
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            (current_history_root/'valid.json').write_text(json.dumps({'id':current_job_identifier}))
            (current_history_root/'legacy.json').write_text(json.dumps({'id':'legacy-id','status':{'status':'completed'}}))
            (current_history_root/'broken.json').write_text('invalid json')
            current_result_value=observe_generation_history_records(current_history_root,current_root_path/'jobs',{})
            self.assertEqual(current_result_value['records'],[{'id':'legacy-id','recorded_status':'completed','status_source':'index'},{'id':current_job_identifier,'recorded_status':'unknown','status_source':'unavailable'}])
            self.assertEqual(current_result_value['unavailable_count'],1)
            (current_history_root/'broken.json').unlink()
            with self.assertRaises(ValueError):
                observe_generation_history_records(current_history_root,current_root_path/'jobs',{'snapshot':current_result_value['snapshot']})

    def test_duplicate_index_ids_are_not_merged_or_restored_from_jobs(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_jobs_root=current_root_path/'jobs'
            current_history_root.mkdir()
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            (current_history_root/'first.json').write_text(json.dumps({'id':current_job_identifier,'status':{'status':'completed'}}))
            (current_history_root/'second.json').write_text(json.dumps({'id':current_job_identifier,'status':{'status':'failed'}}))
            (current_history_root/'third.json').write_text(json.dumps({'id':current_job_identifier}))
            (current_history_root/'other.json').write_text(json.dumps({'id':'other-job'}))
            current_job_path=current_jobs_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            current_result_value=observe_generation_history_records(current_history_root,current_jobs_root,{})
            self.assertEqual([current_item['id'] for current_item in current_result_value['records']],['other-job'])
            self.assertEqual(current_result_value['unavailable_count'],1)
            (current_history_root/'second.json').unlink()
            (current_history_root/'third.json').unlink()
            with self.assertRaisesRegex(ValueError,'변경'):
                observe_generation_history_records(current_history_root,current_jobs_root,{'snapshot':current_result_value['snapshot']})

    def test_search_uses_identifier_and_binds_snapshot_to_query(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_history_root.mkdir()
            for current_identifier in ('alpha-01','alpha-02','beta-01'):
                (current_history_root/(current_identifier+'.json')).write_text(json.dumps({'id':current_identifier,'request':{'prompt':'private'}}))
            current_first_page=observe_generation_history_records(current_history_root,current_root_path/'jobs',{'query':'ALPHA','limit':1})
            self.assertEqual(current_first_page['total'],2)
            current_second_page=observe_generation_history_records(current_history_root,current_root_path/'jobs',{'query':'alpha','limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            self.assertEqual(len(current_second_page['records']),1)
            self.assertNotIn('private',str(current_second_page))
            with self.assertRaises(ValueError):observe_generation_history_records(current_history_root,current_root_path/'jobs',{'query':'beta','offset':1,'snapshot':current_first_page['snapshot']})
            with self.assertRaises(ValueError):observe_generation_history_records(current_history_root,current_root_path/'jobs',{'query':'bad query'})

    def test_bad_current_status_does_not_use_stale_index_status(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_history_root.mkdir()
            current_job_identifier='legacy-id'
            (current_history_root/'legacy.json').write_text(json.dumps({'id':current_job_identifier,'status':{'status':'completed'}}))
            current_job_path=current_root_path/'jobs'/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text('invalid json')
            current_result_value=observe_generation_history_records(current_history_root,current_root_path/'jobs',{})
            self.assertEqual(current_result_value['records'][0]['recorded_status'],'unknown')

    def test_status_ids_must_match_when_present_and_legacy_without_id_remains_valid(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_jobs_root=current_root_path/'jobs'
            current_history_root.mkdir()
            for current_identifier in ('job-a','job-b','job-c'):
                (current_history_root/(current_identifier+'.json')).write_text(json.dumps({'id':current_identifier,'status':{'status':'completed','id':current_identifier}}))
                (current_jobs_root/current_identifier).mkdir(parents=True)
            (current_jobs_root/'job-a'/'status.json').write_text(json.dumps({'status':'completed','id':'job-b'}))
            (current_jobs_root/'job-b'/'status.json').write_text(json.dumps({'status':'failed','id':'job-b'}))
            (current_jobs_root/'job-c'/'status.json').write_text(json.dumps({'status':'completed'}))
            current_results={current_record['id']:current_record for current_record in observe_generation_history_records(current_history_root,current_jobs_root,{})['records']}
            self.assertEqual((current_results['job-a']['recorded_status'],current_results['job-a']['status_source']),('unknown','unavailable'))
            self.assertEqual(current_results['job-b']['recorded_status'],'failed')
            self.assertEqual(current_results['job-c']['recorded_status'],'completed')
            (current_jobs_root/'job-a'/'status.json').unlink()
            (current_history_root/'job-a.json').write_text(json.dumps({'id':'job-a','status':{'status':'completed','id':'job-b'}}))
            current_results={current_record['id']:current_record for current_record in observe_generation_history_records(current_history_root,current_jobs_root,{})['records']}
            self.assertEqual((current_results['job-a']['recorded_status'],current_results['job-a']['status_source']),('unknown','unavailable'))

    def test_missing_status_and_invalid_page(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_history_root.mkdir()
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            (current_history_root/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier,'request':{'prompt':'private'}}))
            current_result_value=observe_generation_history_records(current_history_root,current_root_path/'jobs',{})
            self.assertEqual(current_result_value['records'][0]['recorded_status'],'unknown')
            for current_bad_request in ({'limit':True},{'offset':-1},{'snapshot':'bad'},{'extra':1}):
                with self.subTest(request=current_bad_request),self.assertRaises(ValueError):
                    observe_generation_history_records(current_history_root,current_root_path/'jobs',current_bad_request)

    def test_observed_order_matches_legacy_reset_and_hidden_contract(self):
        import os
        import time
        from tools.review.common.generation_records import load_generation_history_records
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_history_root=current_root_path/'history'
            current_jobs_root=current_root_path/'jobs'
            current_history_root.mkdir()
            current_jobs_root.mkdir()
            current_job_identifiers=[f'2026-11-18_12-{current_index:02d}-00-{current_index:08x}' for current_index in range(45)]
            current_reset_path=current_history_root/'.reset-marker'
            current_reset_path.touch()
            current_now_value=time.time()
            os.utime(current_reset_path,(current_now_value-5,current_now_value-5))
            for current_index,current_job_identifier in enumerate(current_job_identifiers):
                current_job_path=current_jobs_root/current_job_identifier
                current_job_path.mkdir()
                current_request_path=current_job_path/'request.json'
                current_request_path.write_text('{}')
                (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
                if current_index==0:
                    os.utime(current_request_path,(current_now_value-10,current_now_value-10))
                if current_index==1:
                    (current_job_path/'.history-deleted').touch()
                if current_index==2:
                    (current_history_root/'deleted').mkdir(exist_ok=True)
                    (current_history_root/'deleted'/current_job_identifier).touch()
                if current_index==3:
                    (current_history_root/(current_job_identifier+'.json')).write_text(json.dumps({'id':current_job_identifier,'created_at':'2026-11-19T00:00:00+09:00'}))
            current_expected_ids=[current_record['id'] for current_record in load_generation_history_records(current_history_root,current_jobs_root)]
            current_first_page=observe_generation_history_records(current_history_root,current_jobs_root,{'limit':30})
            current_second_page=observe_generation_history_records(current_history_root,current_jobs_root,{'limit':30,'offset':current_first_page['next_offset'],'snapshot':current_first_page['snapshot']})
            current_actual_ids=[current_record['id'] for current_record in current_first_page['records']+current_second_page['records']]
            self.assertEqual(current_actual_ids,current_expected_ids)
            self.assertEqual(len(current_actual_ids),42)

    def test_music_service_exposes_source_records_without_logs(self):
        from unittest.mock import patch
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.common.management_gateway import resolve_management_command
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_manager_value=MusicGenerationManager('music-heartmula')
            current_manager_value.history_storage_root=current_root_path/'history'
            current_manager_value.job_storage_root=current_root_path/'jobs'
            current_manager_value.history_storage_root.mkdir()
            current_job_identifier='2026-11-18_12-00-00-aaaaaaaa'
            current_job_path=current_manager_value.job_storage_root/current_job_identifier
            current_job_path.mkdir(parents=True)
            (current_job_path/'request.json').write_text(json.dumps({'prompt':'secret'}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'running'}))
            with patch.object(current_manager_value,'list_music_history') as current_history_mock,patch.object(current_manager_value,'read_music_status') as current_status_mock:
                current_result_value=current_manager_value.execute_music_command('history-observe',{'limit':10})
                self.assertEqual(current_result_value['records'],[{'id':current_job_identifier,'recorded_status':'running','status_source':'job'}])
                self.assertNotIn('secret',str(current_result_value))
                current_history_mock.assert_not_called()
                current_status_mock.assert_not_called()
            self.assertEqual(resolve_management_command('music-heartmula','history-observe',{}),('POST','/music-heartmula/history/observe'))
            with self.assertRaises(ValueError):
                current_manager_value.execute_music_command('history-observe',{'path':'/tmp'})
