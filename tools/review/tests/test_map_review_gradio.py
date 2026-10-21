import unittest
from pathlib import Path

from tools.review.ui.gradio.map_review_app import build_map_review_interface, create_map_review_loader
from tools.review.ui.gradio.management_menu_app import create_initial_selection_script, create_page_preview_html


class MapReviewGradioTest(unittest.TestCase):
    def test_billboard_delete_does_not_require_cell_coordinates(self):
        from tools.review.common.gradio_map_editor import change_map_edit_draft
        current_object_record={'id':'test-billboard-1','position':{'column':2,'row':3}}
        current_editor_state={'snapshot':{},'draft':{'objects':[current_object_record],'cells':[]},'history':[]}
        for current_coordinate_value in (None, -100):
            current_changed_state=change_map_edit_draft(current_editor_state,'delete',current_coordinate_value,current_coordinate_value,None,None,False,'test-billboard-1',None)[0]
            self.assertEqual(current_changed_state['draft']['objects'],[])
            self.assertEqual(current_editor_state['draft']['objects'],[current_object_record])
            current_restored_state=change_map_edit_draft(current_changed_state,'undo',None,None,None,None,False,None,None)[0]
            self.assertEqual(current_restored_state['draft']['objects'],[current_object_record])

    def test_editor_missing_cell_returns_guidance_without_component_errors(self):
        from tools.review.common.gradio_map_editor import read_map_edit_cell
        current_empty_result = read_map_edit_cell({}, None, None)
        self.assertIn('편집 원본을 먼저', current_empty_result[3])
        current_loaded_result = read_map_edit_cell({'snapshot': {}}, None, None)
        self.assertIn('선택한 셀이 없습니다', current_loaded_result[3])
        self.assertEqual(current_loaded_result[0], {'__type__': 'update'})
        current_config_record = build_map_review_interface(8770).get_config_file()
        current_pick_events = [current_event_record for current_event_record in current_config_record['dependencies'] if 'const currentSelectedCell=' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_pick_events), 1)
        self.assertNotIn('throw Error', current_pick_events[0]['js'])

    def test_map_initialization_waits_for_explicit_load(self):
        current_config_record = build_map_review_interface(8770).get_config_file()
        current_initial_events = [current_event_record for current_event_record in current_config_record['dependencies'] if 'const currentExplicitLoad=sessionStorage' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_initial_events), 1)
        self.assertIn('맵을 선택한 뒤 맵 불러오기를 누르세요.', current_initial_events[0]['js'])
        current_load_script = create_map_review_loader(8770, 5, manual_load_enabled=True)
        self.assertIn('history.replaceState', current_load_script)
        self.assertIn('map-review-explicit-load', current_load_script)

    def test_loads_existing_map_canvas_without_an_iframe(self):
        interface_blocks_value = build_map_review_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('map-review-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))

    def test_character_review_has_shared_canvas_and_browser_controls(self):
        current_config_record=build_map_review_interface(8770,character_review_enabled=True).get_config_file()
        current_config_text=str(current_config_record)
        self.assertIn('character-baseline-map',current_config_text)
        self.assertIn('data-character-review',current_config_text)
        self.assertIn('접지 그림자',current_config_text)
        for current_event_record in current_config_record['dependencies']:
            if 'characterReview' in (current_event_record.get('js') or ''):
                self.assertFalse(current_event_record['backend_fn'])
                self.assertFalse(current_event_record['queue'])

    def test_camera_actions_use_native_browser_controls(self):
        current_interface_config=build_map_review_interface(8770).get_config_file()
        current_camera_events=[current_event_record for current_event_record in current_interface_config['dependencies'] if 'mapReviewCameraControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_camera_events),4)
        current_camera_ids={current_event_record['targets'][0][0] for current_event_record in current_camera_events}
        for current_component_record in current_interface_config['components']:
            if current_component_record['id'] in current_camera_ids:
                self.assertFalse(current_component_record['props']['interactive'])
        self.assertIn('interactive:true',create_map_review_loader(8770,5))
        self.assertIn('interactive:false',create_map_review_loader(8770,5))
        for current_event_record in current_camera_events:
            self.assertFalse(current_event_record['backend_fn'])
            self.assertFalse(current_event_record['queue'])

    def test_map_inputs_and_capture_wait_for_loader(self):
        for current_character_mode in (False, True):
            current_config_record = build_map_review_interface(8770, character_review_enabled=current_character_mode).get_config_file()
            for current_component_record in current_config_record['components']:
                if current_component_record['props'].get('label') in ('맵 선택','전투필드 선택','건물 선택','기본 캐릭터','메시 경계','타일 경계'):
                    self.assertFalse(current_component_record['props']['interactive'])
                if current_component_record['type'] == 'button' and current_component_record['props']['value'] in ('맵 불러오기', '렌더링 PNG 캡처'):
                    self.assertFalse(current_component_record['props']['interactive'])
            current_loader_events = [current_event_record for current_event_record in current_config_record['dependencies'] if 'const currentControlOptions=window.mapReviewControlOptions()' in (current_event_record.get('js') or '')]
            self.assertEqual(len(current_loader_events), 2)
            self.assertEqual(current_loader_events[0]['outputs'],current_loader_events[1]['outputs'])
            current_output_identifiers=set(current_loader_events[0]['outputs'])
            for current_component_record in current_config_record['components']:
                if current_component_record['props'].get('label')=='맵 선택':
                    self.assertIn(current_component_record['id'],current_output_identifiers)

    def test_loader_uses_the_live_review_bundle_for_scripts_and_assets(self):
        loader_script_value = create_map_review_loader(8770)

        self.assertIn('/isloon-map-review/block-map-review.js', loader_script_value)
        self.assertIn('mapReviewControlOptions', loader_script_value)
        self.assertNotIn('window.fetch=', loader_script_value)
        self.assertNotIn('stylesheet', loader_script_value)
        self.assertNotIn("createElement('style')", loader_script_value)
        self.assertNotIn('<iframe', loader_script_value)

    def test_town_specific_page_reuses_common_map_review_frame(self):
        page_preview_html = create_page_preview_html(
            'map-review-stonewarm',
            [{'id':'map-review-stonewarm','label':'돌온재 · 도시맵 검수','path':'/isloon-map-review/map-review.html?map=stonewarm&amp;townPage=1','category':'tile-review','uiMode':'gradio','frameIdentifier':'map-review','frameQuery':'map=stonewarm&townPage=1','description':'돌온재 전용 검수'}],
            8770,
        )

        self.assertIn('/management/frame/map-review/?map=stonewarm&amp;townPage=1', page_preview_html)

    def test_legacy_whole_map_review_url_redirects_to_iseulon_page(self):
        initial_selection_script = create_initial_selection_script([])

        self.assertIn('"map-review": "map-review-iseulon"', initial_selection_script)


if __name__ == '__main__':
    unittest.main()
