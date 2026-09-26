import unittest

from tools.review.ui.gradio.management_menu_app import create_page_preview_html


class StaticReviewGradioTest(unittest.TestCase):
    def test_keeps_static_review_in_gradio_workspace(self):
        page_record_values = [{'id':'sample-review','label':'샘플 검수','path':'/ui/review.html?settings=1','category':'game-ui','uiMode':'gradio-static','description':'샘플'}]

        preview_html_value = create_page_preview_html('sample-review', page_record_values, 8770)

        self.assertIn('src="http://127.0.0.1:8770/ui/review.html?settings=1"', preview_html_value)


if __name__ == '__main__':
    unittest.main()
