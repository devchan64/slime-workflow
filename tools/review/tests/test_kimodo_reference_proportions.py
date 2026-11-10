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
    def test_manual_joint_edit_preserves_original_and_rejects_stale_point(self):
        from generators.kimodo.reference_joint_edits import apply_reference_joint_edits
        current_source_points=create_test_reference_points()
        current_edit_records=[{'joint':2,'original':[170,100],'edited':[170,108]}]
        current_adjusted_points,current_evidence_records=apply_reference_joint_edits(current_source_points,current_edit_records,(400,400))
        np.testing.assert_array_equal(current_source_points[2,:2],[170,100])
        np.testing.assert_array_equal(current_adjusted_points[2,:2],[170,108])
        self.assertEqual(current_evidence_records[0]['source_confidence'],.95)
        with self.assertRaisesRegex(ValueError,'원본이 변경'):
            apply_reference_joint_edits(current_source_points,[{'joint':2,'original':[170,101],'edited':[170,108]}],(400,400))
        with self.assertRaisesRegex(ValueError,'중복'):
            apply_reference_joint_edits(current_source_points,current_edit_records*2,(400,400))
        with self.assertRaisesRegex(ValueError,'이미지 범위'):
            apply_reference_joint_edits(current_source_points,[{'joint':2,'original':[170,100],'edited':[400,108]}],(400,400))

    def test_overlapping_arms_select_segment_score_before_longest(self):
        current_pose_points=create_test_reference_points()
        current_pose_points[[2,5],:2]=[[197,100],[203,100]]
        current_pose_points[[3,6],:2]=[[197,150],[203,155]]
        current_pose_points[[2,3],2]=.95
        current_pose_points[[5,6],2]=.7
        current_ratio_record=estimate_reference_proportions([current_pose_points])
        current_observation_record=current_ratio_record['evidence']['upper_arm']['observations'][0]
        self.assertEqual(current_observation_record['joint_pair'],[2,3])
        self.assertIn('겹친',current_observation_record['candidates'][0]['selection_reason'])
        self.assertFalse(current_observation_record['candidates'][1]['selected_for_observation'])

    def test_separate_arms_keep_longest_despite_lower_score(self):
        current_pose_points=create_test_reference_points()
        current_pose_points[6,1]=160
        current_pose_points[[5,6],2]=.7
        current_ratio_record=estimate_reference_proportions([current_pose_points])
        self.assertEqual(current_ratio_record['evidence']['upper_arm']['observations'][0]['joint_pair'],[5,6])

    def test_projected_axis_matches_reference_and_preserves_limb_vectors(self):
        from generators.kimodo.direct_pose_export import adjust_projected_body_axis
        current_points=create_test_reference_points()
        current_positions=np.stack([current_points[:,:2],current_points[:,:2]+[50,20]])
        current_reference_record=estimate_reference_proportions([current_points])
        current_reference_record['body_axis']['vertical_nose_shoulder_to_torso']=.6
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
        self.assertEqual(current_ratio_record['evidence']['thigh']['accepted_images'],[1])
        self.assertAlmostEqual(current_ratio_record['ratios']['shoulder_width'],.6)

    def test_low_confidence_and_asymmetric_observations_reject(self):
        current_pose_points=create_test_reference_points()
        current_pose_points[[9,12],2]=.1
        with self.assertRaisesRegex(ValueError,'thigh'):
            estimate_reference_proportions([current_pose_points])
        current_pose_points=create_test_reference_points()
        current_pose_points[3,:2]=[170,110]
        current_ratio_record=estimate_reference_proportions([current_pose_points])
        self.assertAlmostEqual(current_ratio_record['ratios']['upper_arm'],np.linalg.norm([15,50])/100)

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
        self.assertEqual(current_ratio_record['evidence']['thigh']['accepted_images'],[5])

    def test_head_axis_is_selected_independently_of_shoulder_width(self):
        current_front_points=create_test_reference_points()
        current_side_points=current_front_points.copy()
        current_side_points[[2,5],0]=[185,215]
        current_side_points[0,1]=40
        current_ratio_record=estimate_reference_proportions([current_front_points,current_side_points])
        self.assertEqual(current_ratio_record['evidence']['shoulder_width']['accepted_images'],[1])
        self.assertEqual(current_ratio_record['body_axis']['accepted_observations'],[2])
        self.assertAlmostEqual(current_ratio_record['body_axis']['nose_shoulder_to_torso'],.6)
        self.assertAlmostEqual(current_ratio_record['body_axis']['observations'][1]['vertical_ratio'],.6)

    def test_vertical_axis_ignores_horizontal_nose_projection(self):
        current_front_points=create_test_reference_points()
        current_side_points=current_front_points.copy()
        current_side_points[0,0]+=80
        current_ratio_record=estimate_reference_proportions([current_front_points,current_side_points],[400.,400.])
        self.assertAlmostEqual(current_ratio_record['body_axis']['vertical_nose_shoulder_to_torso'],.3)
        self.assertEqual(current_ratio_record['body_axis']['accepted_observations'],[1])
        self.assertGreater(current_ratio_record['body_axis']['observations'][1]['ratio'],.3)

    def test_common_height_normalization_resists_shorter_torso(self):
        current_normal_points=create_test_reference_points()
        current_short_points=current_normal_points.copy()
        current_short_points[[8,11],1]=180
        current_ratio_record=estimate_reference_proportions([current_normal_points,current_short_points],[400.,400.])
        self.assertAlmostEqual(current_ratio_record['ratios']['shoulder_width'],60/90)
        self.assertEqual(current_ratio_record['normalization']['method'],'bbox_height_common_torso')

    def test_box_height_evidence_does_not_require_face_for_limb(self):
        current_front_points=create_test_reference_points()
        current_back_points=current_front_points.copy()
        current_back_points[0,2]=0
        current_back_points[[2,5],0]=[160,240]
        current_ratio_record=estimate_reference_proportions([current_front_points,current_back_points],[400.0,400.0])
        self.assertEqual(current_ratio_record['evidence']['shoulder_width']['accepted_images'],[2])
        current_sample_record=current_ratio_record['evidence']['shoulder_width']['observations'][1]['candidates'][0]
        self.assertAlmostEqual(current_sample_record['length_px'],80)
        self.assertAlmostEqual(current_sample_record['height_ratio'],.2)
        self.assertNotIn(2,current_ratio_record['body_axis']['accepted_observations'])
        with self.assertRaisesRegex(ValueError,'높이'):
            estimate_reference_proportions([current_front_points],[0])

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
