"""도시 맵 접수의 중복과 응답 유실 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent import city_map_operations


class HermesCityMapOperationsTests(unittest.TestCase):
    def test_unknown_response_is_not_retried_and_can_be_recovered(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{'name':'한글'}}
        current_token_value = city_map_operations.validate_hermes_city_draft(current_draft_value)
        def execute_city_command(current_command_name,current_payload_value):
            if current_command_name == 'city-edit-preview':
                return {'token':current_token_value,'changed':True,'cityId':'stonewarm','columns':5,'rows':5,'buildings':1,'objects':0}
            raise OSError('lost response')
        with TemporaryDirectory() as current_root_name, patch.object(city_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(city_map_operations,'call_field_map_editor',side_effect=execute_city_command) as current_gateway_mock:
            with self.assertRaises(OSError):
                city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)
            self.assertEqual(city_map_operations.read_hermes_city_receipt('city_unknown_123')['state'],'unknown')
            self.assertEqual(city_map_operations.list_hermes_city_receipts()['records'][0]['state'],'unknown')
            self.assertTrue(city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,2)
            current_other_draft = {**current_draft_value,'revision':3}
            with self.assertRaises(ValueError):
                city_map_operations.save_hermes_city_map_once('city_unknown_123',current_other_draft,city_map_operations.validate_hermes_city_draft(current_other_draft))
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_delegation_receipts()['records'],[])

    def test_stale_or_invalid_draft_never_saves(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{}}
        with patch.object(city_map_operations,'call_field_map_editor',side_effect=ValueError('도시 원장이 변경되었습니다.')) as current_gateway_mock:
            with self.assertRaises(ValueError):
                city_map_operations.preview_hermes_city_map(current_draft_value)
            self.assertEqual(current_gateway_mock.call_args.args[0],'city-edit-preview')
        with self.assertRaises(ValueError):
            city_map_operations.validate_hermes_city_draft({**current_draft_value,'generation':True})
