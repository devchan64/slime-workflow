"""Hermes 추론 모델 라우팅 자동 테스트."""
import unittest

from workflow.common.hermes_model_routing import (
    COMPLEX_MODEL, DEFAULT_MODEL, route_hermes_request,
)

CURRENT_REQUEST_MARKER = '\n\n현재 사용자 요청:\n'


class HermesModelRoutingTests(unittest.TestCase):
    def route_prompt(self, prompt_text, **request_fields):
        return route_hermes_request({'prompt': prompt_text, **request_fields})

    def test_route_coding_request_to_complex_model(self):
        self.assertEqual(self.route_prompt('코딩을 해줘'), COMPLEX_MODEL)
        self.assertEqual(self.route_prompt('코딩해줘'), COMPLEX_MODEL)
        self.assertEqual(self.route_prompt('코딩을 도와줘'), COMPLEX_MODEL)

    def test_route_existing_coding_keywords_to_complex_model(self):
        for prompt_text in ('이 코드를 수정해줘', '버그를 수정해줘',
                            '이 기능을 구현해줘', 'fix the bug please'):
            self.assertEqual(self.route_prompt(prompt_text), COMPLEX_MODEL, prompt_text)

    def test_route_english_coding_keyword_to_complex_model(self):
        for prompt_text in ('coding help', 'help me with coding',
                            'please review my Coding plan'):
            self.assertEqual(self.route_prompt(prompt_text), COMPLEX_MODEL, prompt_text)

    def test_route_coding_word_boundary_not_over_matched(self):
        self.assertEqual(self.route_prompt('오늘 날씨 알려줘'), DEFAULT_MODEL)
        self.assertEqual(self.route_prompt('encoding 관련 질문이 있어'), DEFAULT_MODEL)

    def test_route_simple_greeting_to_default_model(self):
        for prompt_text in ('안녕하세요', '안녕', '오늘 날씨 알려줘', '감사합니다'):
            self.assertEqual(self.route_prompt(prompt_text), DEFAULT_MODEL, prompt_text)

    def test_route_uses_current_request_after_history(self):
        history_prompt = '구현에 대해 이야기했습니다.' + CURRENT_REQUEST_MARKER + '안녕하세요'
        self.assertEqual(self.route_prompt(history_prompt), DEFAULT_MODEL)
        coding_prompt = '이전 대화 기록입니다.' + CURRENT_REQUEST_MARKER + '코딩을 해줘'
        self.assertEqual(self.route_prompt(coding_prompt), COMPLEX_MODEL)

    def test_route_verification_module_to_complex_model(self):
        self.assertEqual(self.route_prompt('안녕하세요', verification_modules=['check_a']), COMPLEX_MODEL)


if __name__ == '__main__':
    unittest.main()
