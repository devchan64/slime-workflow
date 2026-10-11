"""앵커 검수 데이터와 실행 스크립트 분리 계약."""
import json
import unittest
from tools.review.common.animation_review_payload import read_animation_review_payload
from tools.review.ui_assets import read_animation_anchor_template


class AnimationReviewPayloadTests(unittest.TestCase):
    def create_review_document(self, current_payload_record):
        return '<script id="anchor-review-data" type="application/json">'+json.dumps(current_payload_record)+'</script>'

    def test_generated_page_exposes_exact_data_without_script_evaluation(self):
        current_frame_records=[{'frameId':'down_left.0','anchor':{'x':1,'y':2}}]
        current_source_record={'animationId':'example </script> <script>bad()</script>','actionReviews':[]}
        current_page_source=read_animation_anchor_template().replace('__FRAME_RECORDS__',json.dumps(current_frame_records).replace('<','\\u003c')).replace('__SOURCE_METADATA__',json.dumps(current_source_record).replace('<','\\u003c'))
        current_payload_record=read_animation_review_payload(current_page_source)
        self.assertEqual(current_payload_record,{'schemaVersion':1,'sourceMetadata':current_source_record,'frames':current_frame_records})
        self.assertNotIn('<script>bad()',current_page_source)
        self.assertNotIn('__FRAME_RECORDS__',current_page_source)
        self.assertIn('const initialReviewMetadata=currentReviewPayload.sourceMetadata',current_page_source)

    def test_missing_duplicate_unclosed_and_executable_blocks_are_rejected(self):
        current_document_text=self.create_review_document({'schemaVersion':1,'sourceMetadata':{},'frames':[{}]})
        for current_invalid_text in ('<script>throw Error("must not run")</script>',current_document_text*2,current_document_text.replace('</script>',''),current_document_text.replace('application/json','text/javascript')):
            with self.subTest(current_invalid_text=current_invalid_text),self.assertRaises(ValueError):
                read_animation_review_payload(current_invalid_text)

    def test_unknown_fields_versions_and_invalid_data_are_rejected(self):
        current_valid_record={'schemaVersion':1,'sourceMetadata':{},'frames':[{}]}
        for current_invalid_record in ({**current_valid_record,'extra':1},{**current_valid_record,'schemaVersion':True},{**current_valid_record,'schemaVersion':2},{**current_valid_record,'sourceMetadata':[]},{**current_valid_record,'frames':[]},{**current_valid_record,'frames':[1]}):
            with self.subTest(current_invalid_record=current_invalid_record),self.assertRaises(ValueError):
                read_animation_review_payload(self.create_review_document(current_invalid_record))

    def test_duplicate_nested_fields_are_rejected(self):
        current_page_source='<script id="anchor-review-data" type="application/json">{"schemaVersion":1,"sourceMetadata":{"id":1,"id":2},"frames":[{}]}</script>'
        with self.assertRaisesRegex(ValueError,'중복 필드'):
            read_animation_review_payload(current_page_source)
