"""건물 관리의 DB 세대·입력 계약을 검증한다."""
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets.building_editor import load_building_editor_catalog, save_building_editor_anchor
from tools.review.common.management_gateway import resolve_management_command


class BuildingEditorTest(unittest.TestCase):
    def test_building_editor_is_separate_map_review_page(self):
        from tools.review.ui.gradio.management_menu_app import DEFAULT_PAGE_RECORDS, NATIVE_MANAGEMENT_APPLICATIONS, resolve_management_page_path
        from tools.review.common.management_asgi import MANAGEMENT_INTERFACE_BUILDERS
        current_records=[row for row in DEFAULT_PAGE_RECORDS if row['id']=='building-editor']
        self.assertEqual(len(current_records),1)
        self.assertEqual(current_records[0]['category'],'map-review')
        self.assertIn('building-editor',NATIVE_MANAGEMENT_APPLICATIONS)
        self.assertIn('building-editor',MANAGEMENT_INTERFACE_BUILDERS)
        self.assertIn('/management/frame/building-editor/',resolve_management_page_path(current_records[0]))

    def test_gateway_routes_building_commands(self):
        self.assertEqual(resolve_management_command('map-assets','building-list',{}),('POST','/map-assets/editor-building-list'))
        self.assertEqual(resolve_management_command('map-assets','building-save',{}),('POST','/map-assets/editor-building-save'))

    def test_save_rejects_invalid_values_before_network(self):
        for values in ({'anchorX':16.1,'anchorY':0.5},{'anchorX':True,'anchorY':0.5},{'anchorX':0.5}):
            with self.subTest(values=values),patch('tools.review.domains.map_assets.building_editor.execute_content_api_request') as current_remote:
                with self.assertRaises(ValueError):save_building_editor_anchor({'texture':'town-iseulon-guild-v2','generation':1,'expected':{'anchorX':0.5,'anchorY':1.0},'properties':values})
                current_remote.assert_not_called()

    def test_save_preserves_generation_and_expected(self):
        current_request={'texture':'town-iseulon-guild-v2','generation':12,'expected':{'anchorX':0.5,'anchorY':1.0},'properties':{'anchorX':1.1,'anchorY':1.2}}
        with patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',return_value={'saved':True}) as current_remote:
            self.assertTrue(save_building_editor_anchor(current_request)['saved'])
        current_method,current_path,current_payload=current_remote.call_args.args
        self.assertEqual((current_method,current_path),('POST','/internal/v1/content/buildings/town-iseulon-guild-v2/anchor'))
        self.assertEqual(current_payload['expectedGeneration'],12)
        self.assertEqual(current_payload['expected'],current_request['expected'])
        self.assertEqual(current_payload['properties'],current_request['properties'])

    def test_size_adjustment_is_sent_with_anchor(self):
        current_request={'texture':'town-iseulon-guild-v2','generation':12,'expected':{'anchorX':0.5,'anchorY':1.0,'displayWidthAdjustment':0,'displayHeightAdjustment':0},'properties':{'anchorX':0.5,'anchorY':1.0,'displayWidthAdjustment':15,'displayHeightAdjustment':-7}}
        with patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',return_value={'saved':True}) as current_remote:
            self.assertTrue(save_building_editor_anchor(current_request)['saved'])
        self.assertEqual(current_remote.call_args.args[2]['properties'],current_request['properties'])

    def test_rejects_partial_and_fractional_size(self):
        for current_size in ({'displayWidthAdjustment':1}, {'displayWidthAdjustment':0.5,'displayHeightAdjustment':0}):
            with self.subTest(current_size=current_size):
                with self.assertRaises(ValueError):
                    save_building_editor_anchor({'texture':'town-iseulon-guild-v2','generation':1,'expected':{'anchorX':0.5,'anchorY':1.0},'properties':{'anchorX':0.5,'anchorY':1.0,**current_size}})

    def test_shared_size_flows_to_map(self):
        from tools.review.common.sprite_display_properties import validate_sprite_display_properties, apply_sprite_display_properties
        current_properties={'town-iseulon-guild-v2':{'anchorX':0.5,'anchorY':1.1,'displayWidthAdjustment':15,'displayHeightAdjustment':-7}}
        current_map={'buildings':[{'sprite':{'textureKey':'town-iseulon-guild-v2'}}]}
        validate_sprite_display_properties(current_properties)
        apply_sprite_display_properties(current_map,current_properties)
        self.assertEqual(current_map['buildings'][0]['sprite']['displayWidthAdjustment'],15)
        self.assertEqual(current_map['buildings'][0]['sprite']['displayHeightAdjustment'],-7)

    def test_catalog_rejects_changed_generation(self):
        current_bundle={'generation':1,'documents':{'sprite-display-properties.yaml':{'data':{}},'city_layouts/index.yaml':{'data':{'includes':{'layouts':{'iseulon':'iseulon.yaml'}}}}}}
        with patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',side_effect=[current_bundle,{'generation':2}]):
            with self.assertRaisesRegex(ValueError,'조회 중 콘텐츠가 변경'):load_building_editor_catalog({})

    def test_unchanged_anchor_does_not_write(self):
        from tools.review.ui.gradio.building_editor_panel import save_building_editor_panel
        current_selected_record={'texture':'town-iseulon-guild-v2','properties':{'anchorX':0.52,'anchorY':0.97},'preview':'preview'}
        with patch('tools.review.ui.gradio.building_editor_panel.execute_remote_management_command') as current_remote:
            current_result=save_building_editor_panel({'generation':10},current_selected_record,0.5199999809265137,0.9700000286102295)
        self.assertIn('변경된 앵커 값이 없습니다',current_result[2])
        current_remote.assert_not_called()


if __name__=='__main__':unittest.main()
