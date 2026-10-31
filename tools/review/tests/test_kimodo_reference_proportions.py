"""참조 비율의 확대 불변성·이상치 처리·출력 골격 보존 검사."""
import unittest
import numpy as np
from generators.kimodo.reference_proportions import estimate_reference_proportions,apply_reference_proportions


def create_test_reference_points():
    current_pose_points=np.zeros((18,3),dtype=float)
    current_pose_points[1:16,2]=.95
    for current_joint_index,current_joint_xy in {1:(200,100),2:(170,100),5:(230,100),3:(155,150),6:(245,150),4:(140,195),7:(260,195),8:(180,200),11:(220,200),9:(180,270),12:(220,270),10:(180,340),13:(220,340),14:(195,70),15:(205,70)}.items():
        current_pose_points[current_joint_index,:2]=current_joint_xy
    return current_pose_points


class KimodoReferenceProportionTests(unittest.TestCase):
    def test_heatmap_scores_are_bounded_without_changing_coordinates(self):
        from generators.kimodo.reference_extraction import normalize_reference_keypoints
        current_raw_points=create_test_reference_points()
        current_raw_points[2,2]=1.2
        current_raw_points[3,2]=-.1
        current_normalized_points=normalize_reference_keypoints(current_raw_points)
        np.testing.assert_array_equal(current_normalized_points[:,:2],current_raw_points[:,:2])
        self.assertEqual(current_normalized_points[2,2],1)
        self.assertEqual(current_normalized_points[3,2],0)
        self.assertEqual(current_raw_points[2,2],1.2)
        current_raw_points[4,2]=np.nan
        with self.assertRaises(ValueError):
            normalize_reference_keypoints(current_raw_points)

    def test_scale_invariance_and_outlier_rejection(self):
        current_pose_points=create_test_reference_points()
        current_scaled_points=current_pose_points.copy()
        current_scaled_points[:,:2]*=2
        current_outlier_points=current_pose_points.copy()
        current_outlier_points[[9,10,12,13],1]+=[140,280,140,280]
        current_ratio_record=estimate_reference_proportions([current_pose_points,current_scaled_points,current_outlier_points])
        self.assertAlmostEqual(current_ratio_record['ratios']['thigh'],.7)
        self.assertEqual(current_ratio_record['evidence']['thigh']['accepted_images'],[1,2])
        self.assertAlmostEqual(current_ratio_record['ratios']['shoulder_width'],.6)

    def test_low_confidence_and_asymmetric_observations_reject(self):
        current_pose_points=create_test_reference_points()
        current_pose_points[[9,12],2]=.1
        with self.assertRaisesRegex(ValueError,'thigh'):
            estimate_reference_proportions([current_pose_points])
        current_pose_points=create_test_reference_points()
        current_pose_points[3,:2]=[170,110]
        with self.assertRaisesRegex(ValueError,'upper_arm'):
            estimate_reference_proportions([current_pose_points])

    def test_rotated_short_observations_do_not_shorten_full_length(self):
        current_reference_points=create_test_reference_points()
        current_reference_records=[]
        for current_projection_factor in (.45,.55,.65,.75,1.,1.):
            current_projected_points=current_reference_points.copy()
            for current_hip_index,current_knee_index,current_ankle_index in ((8,9,10),(11,12,13)):
                current_projected_points[current_knee_index,:2]=current_reference_points[current_hip_index,:2]+current_projection_factor*(current_reference_points[current_knee_index,:2]-current_reference_points[current_hip_index,:2])
                current_projected_points[current_ankle_index,:2]=current_projected_points[current_knee_index,:2]+current_projection_factor*(current_reference_points[current_ankle_index,:2]-current_reference_points[current_knee_index,:2])
            current_reference_records.append(current_projected_points)
        current_ratio_record=estimate_reference_proportions(current_reference_records)
        self.assertAlmostEqual(current_ratio_record['ratios']['thigh'],.7)
        self.assertAlmostEqual(current_ratio_record['ratios']['shin'],.7)
        self.assertEqual(current_ratio_record['evidence']['thigh']['accepted_images'],[5,6])

    def test_adjustment_preserves_bone_directions_root_motion_and_source(self):
        current_pose_points=create_test_reference_points()
        current_ratio_record=estimate_reference_proportions([current_pose_points])
        current_body_positions=np.zeros((2,18,3))
        current_body_positions[:,:,:2]=current_pose_points[:,:2]
        current_body_positions[1,:,0]+=100
        current_original_copy=current_body_positions.copy()
        current_ratio_record['ratios']['forearm']*=1.3
        current_adjusted_positions=apply_reference_proportions(current_body_positions,current_ratio_record)
        np.testing.assert_array_equal(current_body_positions,current_original_copy)
        np.testing.assert_allclose(current_adjusted_positions[:,[8,11]].mean(1),current_body_positions[:,[8,11]].mean(1))
        np.testing.assert_allclose(current_adjusted_positions[:,4]-current_adjusted_positions[:,3],1.3*(current_body_positions[:,4]-current_body_positions[:,3]))
        np.testing.assert_allclose(current_adjusted_positions[1,1:16]-current_adjusted_positions[0,1:16],np.tile([100,0,0],(15,1)))
