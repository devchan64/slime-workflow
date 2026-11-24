import unittest

from generators.kimodo.form_inputs import load_kimodo_examples
from workflow.domains.hermes_agent.kimodo_example_request import resolve_kimodo_example_request, kimodo_example_response
from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal


class KimodoExampleRequestTests(unittest.TestCase):
    def test_resolves_only_matching_registered_example(self):
        prompt = ('Kimodo 바닥 휴식 예제(male_floor_rest_cycle)를 최신 설정 그대로 사용하여 서기 64프레임, '
                  '휴식 64프레임, 일어서기 64프레임의 총 192프레임 순차 생성 작업을 접수해 주세요. '
                  '예제의 나머지 설정과 참조 이미지도 그대로 사용해 주세요.')
        examples = load_kimodo_examples()
        result = resolve_kimodo_example_request(prompt, examples)
        self.assertEqual(result['segments'], [64, 64, 64])
        self.assertEqual(parse_hermes_kimodo_proposal(kimodo_example_response(result)), {'example_id':'male_floor_rest_cycle'})
        for altered in (prompt.replace('휴식 64', '휴식 63'), prompt.replace('192프레임', '191프레임'),
                        prompt.replace('male_floor_rest_cycle', 'missing'), prompt + ' 시드는 99로 변경해 주세요.'):
            with self.subTest(prompt=altered):
                self.assertIsNone(resolve_kimodo_example_request(altered, examples))


if __name__ == '__main__':
    unittest.main()
