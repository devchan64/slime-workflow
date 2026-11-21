"""참조 얼굴점이 몸 정렬 및 머리 회전을 따르는지 확인한다."""
import unittest
import numpy as np
from generators.kimodo.multiview_face_anchor_experiment import apply_multiview_face_anchors, derive_multiview_face_anchors, create_face_anchor_calibration, validate_face_anchor_calibration


class KimodoFaceAnchorExperimentTests(unittest.TestCase):
    def test_experimental_face_does_not_move_shoulder_axis(self):
        from unittest.mock import patch
        from generators.kimodo.direct_pose_export import adjust_projected_body_axis
        current_basis=np.zeros((1,18,2));current_basis[:,2]=[4,1];current_basis[:,5]=[6,1];current_basis[:,8]=[4,6];current_basis[:,11]=[6,6]
        current_candidate=current_basis.copy();current_candidate[:,0]=[8,9]
        with patch('generators.kimodo.reference_proportions.calculate_reference_torso_gain',side_effect=lambda current_points,current_reference: 1.2 if current_points[0,0,0]==0 else 1.5):
            current_original,_=adjust_projected_body_axis(current_basis,{})
            current_adjusted,_=adjust_projected_body_axis(current_candidate,{},current_basis)
        np.testing.assert_allclose(current_original[:,1:14],current_adjusted[:,1:14])
        np.testing.assert_allclose(current_adjusted[:,0],current_candidate[:,0])

    def test_calibration_records_and_validates_attempt_source(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from generators.kimodo.multiview_face_anchor_experiment import create_face_calibration_from_attempt
        from generators.kimodo.soma_pose import SOMA_BODY_JOINT_NAMES
        current_names=list(dict.fromkeys([current_name for current_name in SOMA_BODY_JOINT_NAMES if current_name]+['Head']))
        current_names.extend(f'joint_{current_index}' for current_index in range(77-len(current_names)))
        current_positions=np.zeros((1,77,3));current_rotations=np.tile(np.eye(3),(1,77,1,1))
        for current_name,current_value in {'RightArm':[-1,2,0],'LeftArm':[1,2,0],'RightLeg':[-.5,0,0],'LeftLeg':[.5,0,0],'Head':[0,2.5,0]}.items():
            current_positions[0,current_names.index(current_name)]=current_value
        current_body=np.zeros((12,3));current_body[0]=[-1,2,0];current_body[3]=[1,2,0];current_body[6]=[-.5,0,0];current_body[9]=[.5,0,0]
        current_reference={'body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'body_joint_positions':current_body.tolist(),'face_joint_positions':[[0,3,.5],[-.2,3.2,.4],[.2,3.2,.4],[-.5,3,0],[.5,3,0]]}
        with tempfile.TemporaryDirectory() as current_temp:
            current_root=Path(current_temp);current_motion=current_root/'motion.npz'
            np.savez(current_motion,posed_joints=current_positions,global_rot_mats=current_rotations)
            (current_root/'skeleton.json').write_text(json.dumps({'joint_names':current_names}))
            (current_root/'soma-render.json').write_text(json.dumps({'source':'motion.npz'}))
            (current_root/'reference-proportions.json').write_text(json.dumps({'weighted_body_face_candidate':current_reference}))
            with patch('generators.kimodo.reference_proportions.apply_reference_proportions',side_effect=lambda current_input,current_ratio:current_input):
                current_result=create_face_calibration_from_attempt(current_root,0)
                self.assertEqual(current_result['source']['motion_sha256'],hashlib.sha256(current_motion.read_bytes()).hexdigest())
                self.assertEqual(current_result['source']['frame'],0)
                with self.assertRaisesRegex(ValueError,'범위'):
                    create_face_calibration_from_attempt(current_root,1)
                (current_root/'soma-render.json').write_text(json.dumps({'source':'../outside.npz'}))
                with self.assertRaisesRegex(ValueError,'경로'):
                    create_face_calibration_from_attempt(current_root,0)

    def test_face_points_follow_head_rotation_and_preserve_body(self):
        current_reference_body=np.zeros((12,3));current_reference_body[0]=[-1,2,0];current_reference_body[3]=[1,2,0];current_reference_body[6]=[-.5,0,0];current_reference_body[9]=[.5,0,0]
        current_reference_face=np.array([[0,3,.5],[-.2,3.2,.4],[.2,3.2,.4],[-.5,3,0],[.5,3,0]])
        current_reference={'body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'body_joint_positions':current_reference_body.tolist(),'face_joint_positions':current_reference_face.tolist()}
        current_body=np.zeros((18,3));current_body[[2,5]]=current_reference_body[[0,3]];current_body[[8,11]]=current_reference_body[[6,9]]
        current_offsets=derive_multiview_face_anchors(current_reference,current_body,np.array([0,2.5,0]),np.eye(3))
        current_rotation=np.array([[0,0,1],[0,1,0],[-1,0,0]])
        current_frames=np.stack([current_body,current_body]);current_heads=np.array([[0,2.5,0],[1,2.5,0]])
        current_output=apply_multiview_face_anchors(current_frames,current_heads,np.array([np.eye(3),current_rotation]),current_offsets)
        np.testing.assert_allclose(current_output[0,[0,14,15,16,17]],current_reference_face)
        np.testing.assert_allclose(current_output[1,0],current_heads[1]+current_rotation@current_offsets[0])
        np.testing.assert_allclose(current_output[:,2],current_frames[:,2])
        current_joint_names=[f'joint_{current_index}' for current_index in range(77)]
        current_source={'frame':0,**{current_key:'a'*64 for current_key in ('motion_sha256','skeleton_sha256','reference_sha256','render_sha256','head_anchors_sha256')}}
        current_traced=create_face_anchor_calibration(current_reference,current_joint_names,current_offsets,current_source)
        self.assertEqual(current_traced['schema'],'kimodo-face-anchor-calibration-v2')
        np.testing.assert_allclose(validate_face_anchor_calibration(current_traced,current_reference,current_joint_names),current_offsets)
        current_traced['source']={**current_source,'frame':-1}
        with self.assertRaisesRegex(ValueError,'출처'):
            validate_face_anchor_calibration(current_traced,current_reference,current_joint_names)
        current_calibration=create_face_anchor_calibration(current_reference,current_joint_names,current_offsets)
        np.testing.assert_allclose(validate_face_anchor_calibration(current_calibration,current_reference,current_joint_names),current_offsets)
        current_changed_names=current_joint_names.copy();current_changed_names[0]='different_joint'
        with self.assertRaisesRegex(ValueError,'일치하지'):
            validate_face_anchor_calibration(current_calibration,current_reference,current_changed_names)
        current_reference['face_joint_positions'][0][0]=99
        with self.assertRaisesRegex(ValueError,'일치하지'):
            validate_face_anchor_calibration(current_calibration,current_reference,current_joint_names)
        with self.assertRaisesRegex(ValueError,'회전행렬'):
            apply_multiview_face_anchors(current_frames,current_heads,np.zeros((2,3,3)),current_offsets)


if __name__=='__main__':
    unittest.main()
