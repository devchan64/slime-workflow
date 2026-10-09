"""공식 포즈 지시와 모델 참조 순서의 대응을 검증한다."""
import unittest
from generators.image.vnccs_profile import build_vnccs_profile
from generators.image.vnccs_runtime import build_vnccs_arguments
from tools.review.domains.image.pose_transfer_generation import load_pose_transfer_prompt


class PoseTransferPromptTests(unittest.TestCase):
    def test_official_prompt_delivery(self):
        current_prompt_text = load_pose_transfer_prompt()
        self.assertEqual(current_prompt_text, 'Replace the pose of <image 2> with the pose of <image 1>. Keep the character of <image 2>.')
        self.assertLess(len(current_prompt_text.split()), 100)
        current_request_record = {'width':512, 'height':512, 'steps':40, 'prompt':current_prompt_text, 'vnccs':build_vnccs_profile()}
        current_argument_record = build_vnccs_arguments(current_request_record, ['identity', 'pose'], None, None)
        self.assertEqual(current_argument_record['prompt'], current_prompt_text)
        self.assertEqual(current_argument_record['image'], ['pose', 'identity'])

    def test_saved_prompt_preservation(self):
        current_saved_prompt = 'Draw character from image2'
        current_request_record = {'width':512, 'height':512, 'steps':40, 'prompt':current_saved_prompt, 'vnccs':build_vnccs_profile()}
        self.assertEqual(build_vnccs_arguments(current_request_record, ['identity', 'pose'], None, None)['prompt'], current_saved_prompt)
