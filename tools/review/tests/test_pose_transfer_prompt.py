"""채택된 전신 포즈 지시와 모델 참조 순서의 대응을 검증한다."""
import unittest
from generators.image.vnccs_profile import build_vnccs_profile
from generators.image.vnccs_runtime import build_vnccs_arguments
from tools.review.domains.image.pose_transfer_generation import load_pose_transfer_prompt, combine_pose_prompt


class PoseTransferPromptTests(unittest.TestCase):
    def test_auxiliary_prompt_combination(self):
        self.assertEqual(combine_pose_prompt(' Base pose. ', '\nKeep feet visible. '), 'Base pose. Keep feet visible.')
        self.assertEqual(combine_pose_prompt('Base pose.', ''), 'Base pose.')
        self.assertEqual(len(combine_pose_prompt('word ' * 98, 'last').split()), 99)
        with self.assertRaises(ValueError):
            combine_pose_prompt('word ' * 99, 'last')
        with self.assertRaises(ValueError):
            combine_pose_prompt('', '')
        with self.assertRaises(ValueError):
            combine_pose_prompt('base', None)

    def test_generalized_prompt_delivery(self):
        current_prompt_text = load_pose_transfer_prompt()
        self.assertEqual(current_prompt_text, 'Replace the pose of <image 2> with the pose of <image 1>. Match relative joint positions and bends, and the orientations of the head, torso, pelvis, palms, and feet. Match heel elevation in <image 1>.')
        for current_removed_phrase in ('full-body', 'entire body', 'Preserve', 'anatomical', 'character’s perspective'):
            self.assertNotIn(current_removed_phrase, current_prompt_text)
        self.assertLessEqual(len(current_prompt_text.split()), 50)
        self.assertLess(len(current_prompt_text.split()), 100)
        current_request_record = {'width':512, 'height':512, 'steps':40, 'prompt':current_prompt_text, 'vnccs':build_vnccs_profile()}
        current_argument_record = build_vnccs_arguments(current_request_record, ['identity', 'pose'], None, None)
        self.assertEqual(current_argument_record['prompt'], current_prompt_text)
        self.assertEqual(current_argument_record['image'], ['pose', 'identity'])

    def test_saved_prompt_preservation(self):
        current_saved_prompt = 'Draw character from image2'
        current_request_record = {'width':512, 'height':512, 'steps':40, 'prompt':current_saved_prompt, 'vnccs':build_vnccs_profile()}
        self.assertEqual(build_vnccs_arguments(current_request_record, ['identity', 'pose'], None, None)['prompt'], current_saved_prompt)
