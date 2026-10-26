"""발광 명령의 DB 연결과 입력 경계 검증."""
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.effect_editor import execute_effect_editor_command

class EffectEditorTests(unittest.TestCase):
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_list_filters_non_alignment_effects(self,current_api_mock):
        current_api_mock.return_value={'effects':[{'id':'a','name':'A'},{'id':'b','name':'B','alignment':{}}]}
        self.assertEqual(execute_effect_editor_command('effect-list',{}),{'effects':[{'id':'b','name':'B'}]})
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_save_preserves_revision_and_request(self,current_api_mock):
        current_payload={'id':'sample','requestId':'request','expectedRevision':'revision','alignment':{}}
        execute_effect_editor_command('effect-save',current_payload)
        current_api_mock.assert_called_once_with('PATCH','/internal/v1/content/effects/sample',{key:value for key,value in current_payload.items() if key!='id'})
    def test_save_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):execute_effect_editor_command('effect-save',{'path':'/tmp/a'})

    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_swarm_load_does_not_require_billboard(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        from unittest.mock import Mock
        current_api_mock.return_value={'effects':[{'id':'moth-swarm-v1','renderer':'swarm','image':'assets/sprites/effects/terrain/moth-swarm-sheet-v1.png','alignment':{'texture':'moths'}}]}
        current_tiles_mock.return_value=(None,{})
        current_image_path=Mock();current_image_path.read_bytes.return_value=b'png'
        current_resolver_mock.return_value=(current_image_path,{})
        current_result_record=execute_effect_editor_command('effect-load',{'id':'moth-swarm-v1'})
        self.assertIsNone(current_result_record['hostImage'])
        self.assertEqual(current_api_mock.call_count,1)
