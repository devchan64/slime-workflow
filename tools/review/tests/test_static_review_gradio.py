import unittest

from tools.review.ui.gradio.management_menu_app import create_page_preview_html
from tools.review.ui.gradio.static_review_app import build_static_review_interface


class StaticReviewGradioTest(unittest.TestCase):
    def test_embeds_selected_static_review_path(self):
        interface_blocks_value = build_static_review_interface()

        self.assertIn('static-review-frame', str(interface_blocks_value.get_config_file()))

    def test_builds_encoded_static_review_frame_url(self):
        page_record_values = [{'id':'sample-review','label':'샘플 검수','path':'/ui/review.html?settings=1','category':'game-ui','uiMode':'gradio-static','description':'샘플'}]

        preview_html_value = create_page_preview_html('sample-review', page_record_values, 8770)

        self.assertIn('/management/frame/static-review/?path=%2Fui%2Freview.html%3Fsettings%3D1', preview_html_value)


if __name__ == '__main__':
    unittest.main()
