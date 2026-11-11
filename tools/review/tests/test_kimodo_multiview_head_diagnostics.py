"""코의 전방 관측과 제외 관측 검증을 확인한다."""
import unittest

import numpy as np

from generators.kimodo.multiview_head_diagnostics import calculate_multiview_head_diagnostics


class KimodoMultiviewHeadDiagnosticsTests(unittest.TestCase):
    def test_visible_views_recover_head_and_reject_back_detection(self):
        current_angles = [45, 0, 135, 90, 225, 315, 180, 270]
        current_reference = {'keypoints': [], 'observation_sources': []}
        current_joint_positions = np.zeros((12, 3))
        current_joint_positions[[0, 3], 1] = .4
        current_joint_positions[[6, 9], 1] = .1
        current_views = []
        for current_angle in current_angles:
            current_body = np.zeros((18, 3))
            current_body[:, 2] = .9
            current_body[[8, 11], :2] = [200, 300]
            current_radians = np.deg2rad(current_angle)
            current_body[0, :2] = [200 + 400 * (.03 * np.cos(current_radians) + .08 * np.sin(current_radians)), 300 - 400 * .55]
            if current_angle == 180:
                current_body[0, :2] = [10, 10]
            current_reference['keypoints'].append(current_body.tolist())
            current_reference['observation_sources'].append({'bbox': [0, 0, 400, 400]})
            current_views.append({'fitted_yaw_degrees': current_angle, 'scale': 1, 'offset': [0, 0]})
        current_result = calculate_multiview_head_diagnostics(current_reference, {'views': current_views, 'joint_positions': current_joint_positions.tolist()})
        np.testing.assert_allclose(current_result['head_position'], [.03, .55, .08], atol=1e-10)
        self.assertAlmostEqual(current_result['vertical_nose_shoulder_to_torso'], .5)
        self.assertEqual(current_result['observations'], [1, 2, 6])
        self.assertLess(max(current_row['error_px'] for current_row in current_result['heldout']), 1e-9)
        current_reference['keypoints'][0][0][2] = .1
        with self.assertRaisesRegex(ValueError, '3개 이상'):
            calculate_multiview_head_diagnostics(current_reference, {'views': current_views, 'joint_positions': current_joint_positions.tolist()})


if __name__ == '__main__':
    unittest.main()
