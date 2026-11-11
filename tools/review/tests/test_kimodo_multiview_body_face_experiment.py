"""공통 3D 몸·얼굴 적합과 가려진 관측 제외를 확인한다."""
import unittest

import numpy as np

from generators.kimodo.multiview_body_face_experiment import FACE_LANDMARK_INDICES, fit_multiview_body_face
from tools.review.tests.test_kimodo_multiview_reference_experiment import create_multiview_test_record


class KimodoBodyFaceExperimentTests(unittest.TestCase):
    def test_visible_face_is_fit_and_holdout_does_not_affect_estimate(self):
        current_reference, current_angles = create_multiview_test_record()
        current_body = np.array([[-.18,.7,0],[-.24,.5,.03],[-.27,.3,.06],[.18,.7,0],[.24,.5,.03],[.27,.3,.06],[-.12,.35,0],[-.14,.1,.01],[-.15,-.2,.04],[.12,.35,0],[.14,.1,.01],[.15,-.2,.04]])
        current_body[:, 1] -= .35
        current_faces = np.array([[0,.55,.09],[-.035,.58,.06],[.035,.58,.06],[-.09,.55,0],[.09,.55,0]])
        current_views = []
        for current_index,current_angle in enumerate(current_angles):
            current_radians = np.deg2rad(current_angle)
            for current_face_index,current_joint_index in enumerate(FACE_LANDMARK_INDICES):
                current_position = current_faces[current_face_index]
                current_reference['keypoints'][current_index][current_joint_index] = [float(200+400*(np.cos(current_radians)*current_position[0]+np.sin(current_radians)*current_position[2])),float(160-400*current_position[1]),.95]
            current_views.append({'fitted_yaw_degrees':current_angle,'scale':1.,'offset':[0.,0.]})
        current_initial={'views':current_views,'joint_positions':current_body.tolist()}
        current_visibility=[[current_index in (0,1,5)]*5 for current_index in range(8)]
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':1.,'reason':'검수'} for current_joint in range(18)]} for current_index in range(8)]}
        current_weights['views'][0]['joints'][2]['weight']=.5
        current_weights['views'][0]['joints'][16]['weight']=.5
        current_weights['views'][0]['joints'][3]['weight']=0
        current_weighted=fit_multiview_body_face(current_reference,current_initial,current_visibility,current_joint_weight_table=current_weights)
        self.assertAlmostEqual(current_weighted['views'][0]['body_weights'][0],.475)
        self.assertAlmostEqual(current_weighted['views'][0]['face_weights'][3],.475)
        self.assertEqual(current_weighted['views'][0]['body_weights'][1],0)
        current_weights['views'][0]['joints'][2]['weight']=float('nan')
        with self.assertRaisesRegex(ValueError,'0~1'):
            fit_multiview_body_face(current_reference,current_initial,current_visibility,current_joint_weight_table=current_weights)
        current_weights['views'][0]['joints'][2]['weight']=1
        for current_view in current_weights['views']:
            current_view['joints'][2]['weight']=0
        with self.assertRaisesRegex(ValueError,'몸 관절 2.*관측이 부족'):
            fit_multiview_body_face(current_reference,current_initial,current_visibility,current_joint_weight_table=current_weights)
        current_result=fit_multiview_body_face(current_reference,current_initial,current_visibility)
        np.testing.assert_allclose(current_result['face_joint_positions'],current_faces,atol=.005)
        current_body_holdout=fit_multiview_body_face(current_reference,current_initial,current_visibility,current_excluded_body=(0,2))
        current_reference['keypoints'][0][2][0]+=60
        current_body_changed=fit_multiview_body_face(current_reference,current_initial,current_visibility,current_excluded_body=(0,2))
        np.testing.assert_allclose(current_body_holdout['body_joint_positions'],current_body_changed['body_joint_positions'],atol=1e-9)
        self.assertEqual(current_body_holdout['views'][0]['body_fit_weights'][0],0)
        with self.assertRaisesRegex(ValueError,'골반'):
            fit_multiview_body_face(current_reference,current_initial,current_visibility,current_excluded_body=(0,8))
        current_reference['keypoints'][0][2][0]-=60
        current_holdout=fit_multiview_body_face(current_reference,current_initial,current_visibility,(0,0))
        current_reference['keypoints'][0][0][0]+=100
        current_changed=fit_multiview_body_face(current_reference,current_initial,current_visibility,(0,0))
        np.testing.assert_allclose(current_holdout['face_joint_positions'],current_changed['face_joint_positions'],atol=1e-9)
        with self.assertRaisesRegex(ValueError,'불리언'):
            fit_multiview_body_face(current_reference,current_initial,[[1]*5 for _ in range(8)])


if __name__ == '__main__':
    unittest.main()
