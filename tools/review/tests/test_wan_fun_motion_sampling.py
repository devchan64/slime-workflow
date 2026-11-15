"""앉기·일어서기 구간의 65프레임 선택 계약."""
import unittest

import numpy as np

from generators.wan_fun.motion_frame_sampling import analyze_fun_pose_frames, select_fun_motion_segment


class FunMotionSamplingTests(unittest.TestCase):
    def test_sitting_pivot_and_both_motion_endpoints_are_preserved(self):
        current_frames = []
        for current_index in range(113):
            current_head = 4 + min(current_index, 25, 112 - current_index) * 2
            current_frame = np.zeros((100, 120, 3), dtype=np.uint8)
            current_frame[current_head:90, 55:60] = (0, 255, 255)
            current_frames.append(current_frame)
        current_record = analyze_fun_pose_frames(current_frames)
        current_selected = current_record['selected_indices']
        self.assertEqual(len(current_selected), 65)
        self.assertEqual(current_selected[0], 0)
        self.assertEqual(current_selected[-1], 112)
        self.assertEqual(current_selected[32], current_record['sitting_pivot'])
        self.assertTrue(all(current_left < current_right for current_left, current_right in zip(current_selected, current_selected[1:])))
        self.assertTrue(current_record['sitting_range'][0] <= current_selected[32] <= current_record['sitting_range'][1])

    def test_segment_rejects_insufficient_source_frames(self):
        with self.assertRaisesRegex(ValueError, '33개'):
            select_fun_motion_segment([0.0] * 32, 0, 31, 33)

    def test_static_pose_is_not_treated_as_a_sitting_motion(self):
        current_frame = np.zeros((100, 120, 3), dtype=np.uint8)
        current_frame[10:90, 50:55] = (0, 255, 255)
        with self.assertRaisesRegex(ValueError, '높이 변화'):
            analyze_fun_pose_frames([current_frame] * 65)


if __name__ == '__main__':
    unittest.main()
