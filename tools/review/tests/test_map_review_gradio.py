import unittest
from pathlib import Path

from tools.review.ui.gradio.map_review_app import build_map_review_interface, create_map_review_loader
from tools.review.ui.gradio.management_menu_app import create_initial_selection_script, create_page_preview_html


class MapReviewGradioTest(unittest.TestCase):
    def test_loads_existing_map_canvas_without_an_iframe(self):
        interface_blocks_value = build_map_review_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('map-review-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))

    def test_loader_uses_the_live_review_bundle_for_scripts_and_assets(self):
        loader_script_value = create_map_review_loader(8770)

        self.assertIn('/isloon-map-review/map-review.html?embedded=1', loader_script_value)
        self.assertIn("['map','townPage']", loader_script_value)
        self.assertIn('mapReviewAssetUrl', loader_script_value)
        self.assertIn('sourceScriptElement', loader_script_value)
        self.assertNotIn('<iframe', loader_script_value)

    def test_town_specific_page_reuses_common_map_review_frame(self):
        page_preview_html = create_page_preview_html(
            'map-review-stonewarm',
            [{'id':'map-review-stonewarm','label':'돌온재 · 마을 맵 검수','path':'/isloon-map-review/map-review.html?map=stonewarm&amp;townPage=1','category':'tile-review','uiMode':'gradio','frameIdentifier':'map-review','frameQuery':'map=stonewarm&townPage=1','description':'돌온재 전용 검수'}],
            8770,
        )

        self.assertIn('/management/frame/map-review/?map=stonewarm&amp;townPage=1', page_preview_html)

    def test_legacy_whole_map_review_url_redirects_to_iseulon_page(self):
        initial_selection_script = create_initial_selection_script([])

        self.assertIn('"map-review": "map-review-iseulon"', initial_selection_script)


if __name__ == '__main__':
    unittest.main()
