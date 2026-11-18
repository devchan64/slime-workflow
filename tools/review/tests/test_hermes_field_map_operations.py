"""Hermes 야외 맵 초안 검증과 중복 방지 저장 검사."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent import field_map_operations


class HermesFieldMapOperationsTests(unittest.TestCase):
    def test_preview_and_concurrent_save_reuses_receipt(self):
        current_draft_value = {'map':'moss-clearing','revision':'old-revision','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        current_calls_list = []
        def execute_field_command(current_command_name,current_payload_value):
            current_calls_list.append(current_command_name)
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0,'render':{'secret':'private'}}
            return {'saved':True,'backup':'private'}
        with TemporaryDirectory() as current_root_name:
            current_store_value = HermesDelegationStore(Path(current_root_name))
            with patch.object(field_map_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command):
                current_preview_value = field_map_operations.preview_hermes_field_map(current_draft_value)
                self.assertNotIn('private',str(current_preview_value))
                with ThreadPoolExecutor(max_workers=4) as current_executor_value:
                    current_results_list = list(current_executor_value.map(lambda unused_value:field_map_operations.save_hermes_field_map_once('field_request_123',current_draft_value,current_token_value),range(4)))
                self.assertEqual(current_calls_list.count('map-edit-save'),1)
                self.assertEqual(sum(not item['duplicate'] for item in current_results_list),1)
                with self.assertRaises(ValueError):
                    field_map_operations.save_hermes_field_map_once('field_request_123',{**current_draft_value,'map':'another'},field_map_operations.validate_field_map_draft({**current_draft_value,'map':'another'}))
                self.assertEqual(current_store_value.list_delegation_receipts()['records'],[])

    def test_lost_save_response_is_not_retried(self):
        current_draft_value = {'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        def execute_field_command(current_command_name,current_payload_value):
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0}
            raise OSError('lost response')
        with TemporaryDirectory() as current_root_name, patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command) as current_gateway_mock:
            with self.assertRaises(OSError):
                field_map_operations.save_hermes_field_map_once('field_request_456',current_draft_value,current_token_value)
            self.assertEqual(field_map_operations.save_hermes_field_map_once('field_request_456',current_draft_value,current_token_value)['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,2)

    def test_receipts_recover_unknown_and_filter_corruption(self):
        current_draft_value = {'map':'moss-clearing','revision':'r','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        def execute_field_command(current_command_name,current_payload_value):
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0}
            raise OSError('lost')
        with TemporaryDirectory() as current_root_name, patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command):
            with self.assertRaises(OSError):
                field_map_operations.save_hermes_field_map_once('field_unknown_123',current_draft_value,current_token_value)
            (Path(current_root_name)/'bad_record_123.json').write_text('{')
            current_receipt_value = field_map_operations.read_hermes_field_receipt('field_unknown_123')
            self.assertEqual(current_receipt_value['state'],'unknown')
            self.assertEqual(field_map_operations.list_hermes_field_receipts()['records'],[{**current_receipt_value,'updated_at':field_map_operations.list_hermes_field_receipts()['records'][0]['updated_at']}])
            self.assertEqual(field_map_operations.read_hermes_field_receipt('missing_123')['state'],'not_found')
            with self.assertRaises(ValueError):
                field_map_operations.read_hermes_field_receipt('../private')

    def test_region_limits_paging_and_revision(self):
        current_map_value = {'map':'sample','revision':'abc','tiles':{'rows':['ab','ba'],'objects':[{'id':'tower','kind':'ward-tower','position':{'column':0,'row':0}},{'id':'tree','kind':'decoration','position':{'column':1,'row':1},'textureKey':'tree-v1','tileAnchor':'center','private':'secret'}]},'terrain':{'columns':2,'rows':2,'elevations':[[0,1],[2,3]],'blocked':[[1,0]]},'codes':{'a':'grass','b':'road'},'textures':[]}
        with patch.object(field_map_operations,'load_hermes_field_map',return_value=current_map_value):
            current_page_value = field_map_operations.read_hermes_field_region({'map':'sample','width':2,'height':2,'limit':1})
            self.assertEqual(len(current_page_value['cells']),4)
            self.assertEqual(current_page_value['summary'],{'cell_count':4,'terrain_counts':{'grass':2,'road':2},'height_counts':{'0':1,'1':1,'2':1,'3':1},'source_blocked_count':1})
            self.assertTrue(current_page_value['cells'][1]['blocked'])
            self.assertEqual(current_page_value['object_next_offset'],1)
            current_next_value = field_map_operations.read_hermes_field_region({'map':'sample','revision':'abc','offset':1,'limit':1})
            self.assertEqual(current_next_value['objects'][0]['id'],'tree')
            self.assertNotIn('secret',str(current_next_value))
            with self.assertRaises(ValueError):
                field_map_operations.read_hermes_field_region({'map':'sample','revision':'stale'})
            for current_invalid_value in ({'map':'sample','width':17},{'map':'sample','column':True},{'map':'sample','offset':-1},{'map':'sample','command':'save'}):
                with self.assertRaises(ValueError):
                    field_map_operations.read_hermes_field_region(current_invalid_value)

    def test_invalid_token_and_unverified_preview_do_not_save(self):
        current_draft_value = {'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        with patch.object(field_map_operations,'call_field_map_editor',return_value={'token':'bad'}) as current_gateway_mock:
            with self.assertRaises(ValueError):
                field_map_operations.save_hermes_field_map_once('field_request_789',current_draft_value,'a'*64)
            current_gateway_mock.assert_not_called()
            with self.assertRaises(ValueError):
                field_map_operations.preview_hermes_field_map(current_draft_value)
