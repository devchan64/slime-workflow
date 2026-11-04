"""발광 명령의 DB 연결과 입력 경계 검증."""
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.effect_editor import execute_effect_editor_command

class EffectEditorTests(unittest.TestCase):
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_list_filters_non_alignment_effects(self,current_api_mock):
        current_api_mock.return_value={'effects':[{'id':'a','name':'A'},{'id':'b','name':'B','alignment':{}}]}
        self.assertEqual(execute_effect_editor_command('effect-list',{}),{'effects':[{'id':'b','name':'B'}]})
    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_waypoint_effect_is_listed_and_loads_six_frames_without_billboard(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        from unittest.mock import Mock
        current_effect_record={'id':'waypoint-guide-v3','name':'웨이포인트 안내','renderer':'waypoint-animation','image':'assets/sprites/effects/waypoint/guide.png','animation':'assets/sprites/effects/waypoint/guide.animation.json','frames':6}
        current_api_mock.return_value={'effects':[current_effect_record]}
        self.assertEqual(execute_effect_editor_command('effect-list',{})['effects'],[{'id':'waypoint-guide-v3','name':'웨이포인트 안내'}])
        current_tiles_mock.return_value=(None,{})
        current_image_path=Mock();current_image_path.read_bytes.return_value=b'png'
        current_animation_path=Mock();current_animation_path.read_text.return_value='{"frames":[{},{},{},{},{},{}]}'
        current_resolver_mock.side_effect=[(current_image_path,{}),(current_animation_path,{})]
        current_detail_record=execute_effect_editor_command('effect-load',{'id':'waypoint-guide-v3'})
        self.assertIsNone(current_detail_record['hostImage'])
        self.assertEqual(len(current_detail_record['animationMetadata']['frames']),6)
        self.assertEqual(current_api_mock.call_count,2)

    def test_waypoint_replacement_requires_same_selection_and_confirmed_input(self):
        import json
        import gradio as gr
        from tools.review.ui.gradio.effect_editor_app import prepare_waypoint_effect_replacement,confirm_waypoint_effect_replacement
        current_detail_record={'document':{'id':'waypoint-guide-v3','renderer':'waypoint-animation'},'revision':'original'}
        current_effect_record={'id':'waypoint-guide-v4','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8,'image':'assets/sprites/effects/waypoint/guide.png','animation':'assets/sprites/effects/waypoint/guide.animation.json'}
        current_effect_json=json.dumps(current_effect_record)
        current_pending_record,_,_=prepare_waypoint_effect_replacement(current_detail_record,current_effect_json)
        with patch('tools.review.ui.gradio.effect_editor_app.execute_remote_management_command',return_value={'id':'waypoint-guide-v4'}) as current_gateway_mock:
            with self.assertRaises(gr.Error):confirm_waypoint_effect_replacement(current_detail_record,current_pending_record,json.dumps({**current_effect_record,'id':'changed'}))
            current_gateway_mock.assert_not_called()
            confirm_waypoint_effect_replacement(current_detail_record,current_pending_record,current_effect_json)
            current_gateway_mock.assert_called_once_with('map-assets','effect-replace',current_pending_record)

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

    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_registration_uses_single_effect_endpoint(self,current_api_mock):
        current_effect_payload={'id':'lake-fog-v1','renderer':'fog'}
        execute_effect_editor_command('effect-register',current_effect_payload)
        current_api_mock.assert_called_once_with('POST','/internal/v1/content/effects',current_effect_payload)

    @patch('tools.review.domains.map_assets.effect_editor.resolve_registered_asset')
    @patch('tools.review.domains.map_assets.effect_editor.load_registered_tiles')
    @patch('tools.review.domains.map_assets.effect_editor.execute_content_api_request')
    def test_image_replacement_checks_registry_before_save(self,current_api_mock,current_tiles_mock,current_resolver_mock):
        current_tiles_mock.return_value=('root',{})
        current_payload={'id':'fog','requestId':'request','expectedRevision':'revision','alignment':{},'image':'assets/sprites/effects/terrain/fog-v2.png'}
        execute_effect_editor_command('effect-save',current_payload)
        current_resolver_mock.assert_called_once_with(current_payload['image'],'root',{},'assets/sprites/effects')
        current_api_mock.assert_called_once_with('PATCH','/internal/v1/content/effects/fog',{k:v for k,v in current_payload.items() if k!='id'})
