import unittest

from tools.review.ui.gradio.map_review_app import build_map_review_interface


class MapReviewGradioTest(unittest.TestCase):
    def test_embeds_existing_map_canvas(self):
        interface_blocks_value = build_map_review_interface(8770)

        configuration_value = interface_blocks_value.get_config_file()

        self.assertIn('/isloon-map-review/map-review.html', str(configuration_value))


if __name__ == '__main__':
    unittest.main()
