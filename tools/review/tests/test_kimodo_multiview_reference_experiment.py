"""다중 시점 참조 실험의 미사용 관측과 입력 검증을 확인한다."""
import unittest
import json
import tempfile
from pathlib import Path
import numpy as np

from generators.kimodo.multiview_reference_experiment import fit_multiview_reference, prepare_multiview_observations, project_multiview_joints


def create_multiview_test_record():
    current_joint_positions=np.array([[-.18,.7,0],[-.24,.5,.03],[-.27,.3,.06],[.18,.7,0],[.24,.5,.03],[.27,.3,.06],[-.12,.35,0],[-.14,.1,.01],[-.15,-.2,.04],[.12,.35,0],[.14,.1,.01],[.15,-.2,.04]])
    current_view_angles=[45,0,135,90,225,315,180,270]
    current_reference_points=[]
    current_source_records=[]
    for current_view_angle in current_view_angles:
        current_angle_radians=np.deg2rad(current_view_angle)
        current_screen_points=np.stack((np.cos(current_angle_radians)*current_joint_positions[:,0]+np.sin(current_angle_radians)*current_joint_positions[:,2],-current_joint_positions[:,1]),axis=1)*400+[200,300]
        current_body_points=np.zeros((18,3))
        current_body_points[2:14,:2]=current_screen_points
        current_body_points[2:14,2]=.95
        current_reference_points.append(current_body_points.tolist())
        current_source_records.append({'bbox':[0,0,400,400]})
    return {'keypoints':current_reference_points,'observation_sources':current_source_records},current_view_angles


class KimodoMultiviewExperimentTests(unittest.TestCase):
    def test_projected_pose_rotation_preserves_projected_limb_lengths(self):
        current_joint_positions=np.arange(36,dtype=float).reshape(12,3)/100
        current_camera_angles=np.linspace(0,2*np.pi,8,endpoint=False)
        current_camera_scales=np.ones(8)
        current_camera_offsets=np.zeros((8,2))
        current_plain_points=project_multiview_joints(current_joint_positions,current_camera_angles,current_camera_scales,current_camera_offsets,np.zeros((8,4)))
        current_rotated_points=project_multiview_joints(current_joint_positions,current_camera_angles,current_camera_scales,current_camera_offsets,np.full((8,4),.2))
        for current_parent_index,current_child_index in ((0,1),(1,2),(3,4),(4,5),(6,7),(7,8),(9,10),(10,11)):
            np.testing.assert_allclose(np.linalg.norm(current_plain_points[:,current_parent_index]-current_plain_points[:,current_child_index],axis=1),np.linalg.norm(current_rotated_points[:,current_parent_index]-current_rotated_points[:,current_child_index],axis=1),atol=1e-12)

    def test_holdout_does_not_affect_fitted_skeleton(self):
        current_reference_record,current_view_angles=create_multiview_test_record()
        current_original_fit=fit_multiview_reference(current_reference_record,current_view_angles)
        current_reference_record['keypoints'][1][6][0]+=30
        current_changed_fit=fit_multiview_reference(current_reference_record,current_view_angles)
        np.testing.assert_allclose(current_original_fit['joint_positions'],current_changed_fit['joint_positions'],atol=1e-9)
        self.assertGreater(current_changed_fit['views'][1]['holdout_error_px'],current_original_fit['views'][1]['holdout_error_px']+10)
        self.assertEqual(current_original_fit['held_out_observations'],8)

    def test_requires_eight_views_and_camera_angles(self):
        current_reference_record,current_view_angles=create_multiview_test_record()
        with self.assertRaisesRegex(ValueError,'8개'):
            prepare_multiview_observations(current_reference_record,current_view_angles[:7])

    def test_comparison_reports_direct_and_dwpose_errors(self):
        from generators.kimodo.multiview_comparison import compare_multiview_outputs
        current_reference_record,_=create_multiview_test_record()
        current_reference_record['evidence']={'upper_arm':{'observations':[]}}
        current_mapping={f'view_{current_index}':current_index for current_index in range(1,9)}
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_roots=[Path(current_temporary_root)/'baseline',Path(current_temporary_root)/'multiview']
            for current_root in current_roots: current_root.mkdir()
            (current_roots[0]/'reference-proportions.json').write_text(json.dumps(current_reference_record))
            for current_method_index,current_root in enumerate(current_roots):
                current_directions={}
                for current_name,current_number in current_mapping.items():
                    current_points=np.asarray(current_reference_record['keypoints'][current_number-1]).copy()
                    if current_method_index==0:
                        current_points[[3,6],1]+=20
                    current_frame_points=current_points.tolist()
                    current_directions[current_name]={'body_points_832x480':[current_frame_points]}
                    current_dwpose_root=current_root/f'dwpose-{current_name}'
                    current_dwpose_root.mkdir()
                    (current_dwpose_root/'pose-keypoints-adjusted.json').write_text(json.dumps([[[[current_frame_points]]]]))
                (current_root/'soma-direct-pose.json').write_text(json.dumps({'directions':current_directions}))
            current_result_record=compare_multiview_outputs(*current_roots,current_mapping)
            for current_kind_name in ('direct_first','direct_median','dwpose_first','dwpose_median'):
                current_metric_record=current_result_record['mean_absolute_error'][current_kind_name]['upper_arm']
                self.assertGreater(current_metric_record['baseline'],0)
                self.assertAlmostEqual(current_metric_record['multiview'],0)
            self.assertEqual(len(current_result_record['views']),8)


if __name__=='__main__':
    unittest.main()
