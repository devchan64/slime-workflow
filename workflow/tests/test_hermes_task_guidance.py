import tempfile
import unittest
from pathlib import Path

from workflow.domains.hermes_agent.worker import prepare_task_guidance


class TaskGuidanceTests(unittest.TestCase):
    def test_specific_image_request_keeps_user_text_and_excludes_old_coding_subject(self):
        prompt = '참조 이미지로 새로운 480p 이미지를 만들고 싶다.'
        request = {'prompt': prompt, 'context': {'messages': [{'role': 'user', 'content': '코드 수정'}]}}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            prepare_task_guidance(directory, Path(__file__).resolve().parents[2], request)
            query = (directory / 'query.txt').read_text()
            guidance = (directory / 'task-guidance.txt').read_text()
            self.assertEqual(query.split('[사용자 원문]\n', 1)[1], prompt)
            self.assertNotIn(prompt, guidance)
            self.assertIn('/control/task-guides/flux.txt', guidance)
            self.assertIn('generation-request/SKILL.md', guidance)
            self.assertNotIn('generator-development', guidance)
            self.assertNotIn('[음악·효과음 위임 제안]', query)
            self.assertIn('HERMES_IMAGE_PROPOSAL', (directory / 'task-guides/flux.txt').read_text())
            self.assertIn('HERMES_QUESTION_FORM', guidance)
            self.assertIn('별도 GPU 양도 동의를 묻지 마세요', guidance)
