import unittest

from workflow.domains.hermes_agent.flux_chat_submission import image_submission_intent


class ImageSubmissionIntentTests(unittest.TestCase):
    def test_only_standalone_affirmative_requests(self):
        for text in ('생성한다.', '생성해 주세요!', '생성하자', '생성합니다'):
            self.assertEqual(image_submission_intent(text), 'generate')
        for text in ('생성하지 마', '생성할까요?', '생성해도 되나요?', '사과를 생성해', '생성한다. 취소'):
            self.assertIsNone(image_submission_intent(text))
        self.assertEqual(image_submission_intent('GPU 양도에 동의.'), 'consent')
        self.assertIsNone(image_submission_intent('GPU 양도에 동의하지 않음'))
