"""참조 비율의 확대 불변성·이상치 처리·출력 골격 보존 검사."""
import unittest
import numpy as np
from generators.kimodo.reference_proportions import estimate_reference_proportions,apply_reference_proportions


def create_test_reference_points():
    current_pose_points=np.zeros((18,3),dtype=float)
    current_pose_points[:16,2]=.95
    for current_joint_index,current_joint_xy in {0:(200,70),1:(200,100),2:(170,100),5:(230,100),3:(155,150),6:(245,150),4:(140,195),7:(260,195),8:(180,200),11:(220,200),9:(180,270),12:(220,270),10:(180,340),13:(220,340),14:(195,70),15:(205,70)}.items():
        current_pose_points[current_joint_index,:2]=current_joint_xy
    return current_pose_points


class KimodoReferenceProportionTests(unittest.TestCase):
    def test_projected_axis_matches_reference_and_preserves_limb_vectors(self):
        from generators.kimodo.direct_pose_export import adjust_projected_body_axis
        current_points=create_test_reference_points()
        current_positions=np.stack([current_points[:,:2],current_points[:,:2]+[50,20]])
        current_reference_record=estimate_reference_proportions([current_points])
        current_reference_record['body_axis']['nose_shoulder_to_torso']=.6
        current_adjusted,current_gain=adjust_projected_body_axis(current_positions,current_reference_record)
        self.assertAlmostEqual(current_gain,.8125)
        current_shoulders=current_adjusted[:,[2,5]].mean(axis=1)
        current_hips=current_adjusted[:,[8,11]].mean(axis=1)
        np.testing.assert_allclose(np.linalg.norm(current_adjusted[:,0]-current_shoulders,axis=1)/np.linalg.norm(current_shoulders-current_hips,axis=1),.6)
        np.testing.assert_allclose(current_adjusted[:,[0,8,9,10,11,12,13]],current_positions[:,[0,8,9,10,11,12,13]])
        for current_parent_index,current_child_index in ((2,3),(3,4),(5,6),(6,7)):
            np.testing.assert_allclose(current_adjusted[:,current_child_index]-current_adjusted[:,current_parent_index],current_positions[:,current_child_index]-current_positions[:,current_parent_index])
        np.testing.assert_array_equal(current_positions[0],current_points[:,:2])

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

    def test_head_torso_alignment_changes_shoulders_not_head_or_hip(self):
        current_reference_points=create_test_reference_points()
        current_reference_points[0,1]=40
        current_ratio_record=estimate_reference_proportions([current_reference_points])
        current_source_points=create_test_reference_points()
        current_source_positions=np.zeros((1,18,3))
        current_source_positions[0,:,:2]=current_source_points[:,:2]
        current_adjusted_positions=apply_reference_proportions(current_source_positions,current_ratio_record)
        current_shoulder_center=current_adjusted_positions[0,[2,5],:2].mean(0)
        current_hip_center=current_adjusted_positions[0,[8,11],:2].mean(0)
        self.assertAlmostEqual(current_shoulder_center[1],118.75)
        self.assertAlmostEqual(np.linalg.norm(current_adjusted_positions[0,0,:2]-current_shoulder_center)/np.linalg.norm(current_shoulder_center-current_hip_center),.6)
        np.testing.assert_allclose(current_adjusted_positions[0,0],current_source_positions[0,0])
        np.testing.assert_allclose(current_hip_center,current_source_positions[0,[8,11],:2].mean(0))

    def test_missing_face_reference_rejected(self):
        current_pose_points=create_test_reference_points()
        current_pose_points[0,2]=0
        with self.assertRaisesRegex(ValueError,'얼굴'):
            estimate_reference_proportions([current_pose_points])

    def test_legacy_reference_keeps_torso_axis_unchanged(self):
        current_pose_points=create_test_reference_points()
        current_ratio_record=estimate_reference_proportions([current_pose_points])
        current_ratio_record['schema']='body18-reference-ratios-v2'
        del current_ratio_record['body_axis']
        current_positions=np.zeros((1,18,3))
        current_positions[0,:,:2]=current_pose_points[:,:2]
        current_adjusted=apply_reference_proportions(current_positions,current_ratio_record)
        np.testing.assert_allclose(current_adjusted[:,1],current_positions[:,1])
        np.testing.assert_allclose(current_adjusted[:,[2,5]].mean(1),current_positions[:,[2,5]].mean(1))
