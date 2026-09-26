import unittest

from tools.review.collect_tile_reviews import build_tile_review_page


class TileReviewGradioTest(unittest.TestCase):
    def test_keeps_browser_side_tile_preview_for_static_gradio_viewer(self):
        rendered_page_value = build_tile_review_page({'assetId':'sample','tileSize':[32,32],'tileability':'repeat-both','heightSteps':1,'variants':[],'preview':None,'mapPreview':None,'qualityWarnings':[]})

        self.assertIn('"assetId": "sample"', rendered_page_value)
        self.assertNotIn('__TILE_REVIEW_DATA__', rendered_page_value)


if __name__ == '__main__':
    unittest.main()
