import unittest

from tools.review.ui.gradio.map_review_app import build_map_review_interface, create_map_review_loader


class MapReviewGradioTest(unittest.TestCase):
    def test_loads_existing_map_canvas_without_an_iframe(self):
        interface_blocks_value = build_map_review_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('map-review-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))

    def test_loader_uses_the_live_review_bundle_for_scripts_and_assets(self):
        loader_script_value = create_map_review_loader(8770)

        self.assertIn('/isloon-map-review/map-review.html?embedded=1', loader_script_value)
        self.assertIn('mapReviewAssetUrl', loader_script_value)
        self.assertIn('sourceScriptElement', loader_script_value)
        self.assertNotIn('<iframe', loader_script_value)


if __name__ == '__main__':
    unittest.main()
