"""모션 프리셋의 참조 무결성과 이력 문구 선택을 검증한다."""
import unittest
from tools.review.domains.image.pose_motion_reference import load_motion_reference, find_matching_auxiliary
from tools.review.domains.image.pose_transfer_generation import combine_pose_prompt, load_pose_transfer_prompt


class PoseMotionReferenceTests(unittest.TestCase):
    def test_registered_supporting_contact_prompt(self):
        selected_pose_image, selected_prompt_text, selected_source_text = load_motion_reference('down_left', 30)
        self.assertEqual(selected_prompt_text, 'Keep the supporting foot grounded as in <image 1>. Keep the non-contact foot off the ground, matching its position in the reference. Walking pose.')
        self.assertIn('등록 보조 문구 적용: 사용자 지정', selected_source_text)
        self.assertNotEqual(load_motion_reference('down_left', 29)[1], selected_prompt_text)
        self.assertNotEqual(load_motion_reference('down_right', 30)[1], selected_prompt_text)

    def test_registered_frames_and_word_limit(self):
        for selected_direction_value in ('down_left','down_right','up_left','up_right'):
            for selected_frame_number in range(1,36):
                selected_pose_image, selected_prompt_text, selected_source_text = load_motion_reference(selected_direction_value,selected_frame_number)
                expected_walking_count = 0 if selected_direction_value == 'down_left' and selected_frame_number in (13, 14, 15, 16, 17, 32) else 1
                self.assertEqual(selected_prompt_text.count('Walking pose.'), expected_walking_count)
                self.assertGreater(selected_pose_image.width,0)
                self.assertIn(f'{selected_frame_number}/35',selected_source_text)
                combine_pose_prompt(load_pose_transfer_prompt(),selected_prompt_text)

    def test_frames_without_auxiliary_prompt(self):
        for selected_direction_value in ('down_left','down_right','up_left','up_right'):
            for selected_frame_number in (*range(2,11),35):
                self.assertEqual(load_motion_reference(selected_direction_value,selected_frame_number)[1], 'Walking pose.')
            if selected_direction_value == 'down_left':
                for selected_frame_number in (*range(1,13), *range(18,23)):
                    self.assertEqual(load_motion_reference(selected_direction_value,selected_frame_number)[1], 'Walking pose.')
                for selected_frame_number in (13,14,15,16):
                    self.assertEqual(load_motion_reference(selected_direction_value,selected_frame_number)[1], 'Keep the right foot grounded and the left foot slightly above the ground beneath the pelvis, matching <image 1>.')
            else:
                self.assertTrue(load_motion_reference(selected_direction_value,1)[1])

    def test_invalid_selection_rejected(self):
        for selected_frame_number in (0,36,1.5,True,None):
            with self.assertRaises(ValueError):
                load_motion_reference('down_left',selected_frame_number)
        with self.assertRaises(ValueError):
            load_motion_reference('../',1)

    def test_retired_heel_history_excluded(self):
        current_base_prompt = load_pose_transfer_prompt()
        current_history_record = {'id': '1', 'status': {'status': 'completed'}, 'request': {
            'prompt': current_base_prompt + ' Match heel elevation in <image 1>. Keep foot grounded.',
            'reference_snapshots': [{'sha256': 'identity'}, {'sha256': 'pose'}]}}
        self.assertIsNone(find_matching_auxiliary([current_history_record], 'pose', current_base_prompt))
        current_history_record['request']['prompt'] = current_base_prompt + ' Keep foot grounded.'
        self.assertEqual(find_matching_auxiliary([current_history_record], 'pose', current_base_prompt), ('Keep foot grounded.', '1'))

    def test_history_requires_same_pose_completed_and_prefix(self):
        current_history_record={'id':'1','status':{'status':'completed'},'request':{'prompt':'Base. Bend knee.','reference_snapshots':[{'sha256':'identity'},{'sha256':'pose'}]}}
        self.assertEqual(find_matching_auxiliary([current_history_record],'pose','Base.'),('Bend knee.','1'))
        self.assertIsNone(find_matching_auxiliary([current_history_record],'different','Base.'))
        self.assertIsNone(find_matching_auxiliary([current_history_record],'pose','Other.'))
        current_history_record['status']['status']='failed'
        self.assertIsNone(find_matching_auxiliary([current_history_record],'pose','Base.'))
