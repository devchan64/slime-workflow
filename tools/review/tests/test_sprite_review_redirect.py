"""통합 편집기 이전 링크가 다른 정적 검수에 영향을 주지 않음을 검증한다."""
import unittest
from urllib.parse import parse_qs,urlsplit
from tools.review.common.sprite_review_redirect import resolve_sprite_review_redirect


class SpriteReviewRedirectTests(unittest.TestCase):
    def test_registered_document_preserves_action(self):
        current_page_records=[{'id':'animation-1','path':'animation-1/anchors.html','anchorEditor':True,'description':'Gradio · character.rest · assets/rest.animation.json'}]
        for current_request_path,current_query_values in [('/management/frame/static-review/',{'review':['animation-1'],'action':['asset:character.walk']}),('/management/',{'tool':['animation-1'],'action':['asset:character.walk']})]:
            current_redirect_url=resolve_sprite_review_redirect(current_request_path,current_query_values,current_page_records)
            self.assertEqual(parse_qs(urlsplit(current_redirect_url).query)['action'],['asset:character.walk'])
        current_redirect_url=resolve_sprite_review_redirect('/animation-1/anchors.html',{},current_page_records)
        self.assertEqual(parse_qs(urlsplit(current_redirect_url).query)['action'],['asset:character.rest'])
        for current_request_path in ('/management/frame/static-review/gradio_api/run/predict','/map/anchors.html','/management/frame/sprite-sheet-editor/'):
            self.assertIsNone(resolve_sprite_review_redirect(current_request_path,{'review':['animation-1']},current_page_records))
        self.assertIsNone(resolve_sprite_review_redirect('/management/frame/static-review/',{'review':['map-1']},current_page_records))
