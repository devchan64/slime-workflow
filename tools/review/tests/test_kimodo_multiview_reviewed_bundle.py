"""검수 골격 묶음의 이미지와 관측 출처 검증."""
import base64
import copy
import hashlib
import io
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash
from generators.kimodo.multiview_reviewed_bundle import validate_reviewed_multiview_bundle, apply_reviewed_multiview_bundle
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS


class KimodoReviewedBundleTests(unittest.TestCase):
    def test_review_bundle_rejects_image_and_observation_changes(self):
        current_buffer=io.BytesIO();Image.new('RGB',(64,64),'white').save(current_buffer,format='PNG')
        current_image=current_buffer.getvalue();current_hash=hashlib.sha256(current_image).hexdigest()
        current_reference={'keypoints':[[[float(current_joint),float(current_joint),.9] for current_joint in range(18)] for _ in range(8)],'observation_sources':[{'bbox':[0,0,32,32]} for _ in range(8)],'reference_image_sha256':[current_hash]}
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':1.,'reason':'검수'} for current_joint in range(18)]} for current_index in range(8)]}
        current_views=[{'observation':current_index+1,'fitted_yaw_degrees':current_index*45,'body_xy':[[float(current_joint),float(current_joint)] for current_joint in range(2,14)],'face_xy':[[float(current_joint),float(current_joint)] for current_joint in (0,14,15,16,17)],'body_fit_weights':[.9]*12,'face_fit_weights':[.9]*5} for current_index in range(8)]
        current_body=[[-.2,.5,0],[-.3,.3,0],[-.3,.1,0],[.2,.5,0],[.3,.3,0],[.3,.1,0],[-.1,0,0],[-.1,-.3,0],[-.1,-.6,0],[.1,0,0],[.1,-.3,0],[.1,-.6,0]]
        current_skeleton={'schema':'kimodo-multiview-body-face-experiment-v1','body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'body_joint_positions':current_body,'face_joint_positions':[[0,.75,.1],[-.03,.8,.1],[.03,.8,.1],[-.1,.8,0],[.1,.8,0]],'joint_weight_table':current_weights,'observation_sha256':calculate_multiview_observation_hash(current_reference),'reference_image_sha256':[current_hash],'views':current_views}
        current_bundle={'schema':'kimodo-reviewed-multiview-bundle-v1','reference_observations':current_reference,'skeleton':current_skeleton}
        current_result=validate_reviewed_multiview_bundle(current_bundle,[current_hash])
        self.assertEqual(current_result,current_bundle)
        self.assertIsNot(current_result,current_bundle)
        current_request={current_name:current_value for current_name,current_value in KIMODO_DEFAULT_SETTINGS.items() if current_name!='schema_version'}
        current_request.update(action='generate',proportion_images=[base64.b64encode(current_image).decode()],proportion_reviewed_multiview=current_bundle)
        self.assertEqual(validate_kimodo_request(current_request)['proportion_reviewed_multiview'],current_bundle)
        with self.assertRaisesRegex(ValueError,'동시에'):
            validate_kimodo_request({**current_request,'proportion_multiview_angles':[45,0,135,90,225,315,180,270]})
        current_ratio={'schema':'body18-reference-ratios-v4','ratios':{current_name:1. for current_name in REFERENCE_SEGMENT_GROUPS},'body_axis':{},'reference_image_sha256':[current_hash]}
        current_candidate=apply_reviewed_multiview_bundle(current_ratio,current_bundle,[current_hash])
        self.assertAlmostEqual(current_candidate['ratios']['shoulder_width'],.8)
        self.assertEqual(current_candidate['weighted_reference_observations'],current_reference)
        self.assertEqual(current_ratio['ratios']['shoulder_width'],1.)
        from tools.review.ui.gradio.kimodo_app import load_reviewed_multiview_bundle,build_kimodo_payload,restore_kimodo_inputs,load_multiview_review_files,build_reviewed_bundle_from_review
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root=Path(current_root_name);current_job=current_root/'trial';current_job.mkdir()
            current_image_path=current_job/'reference-1.png';current_image_path.write_bytes(current_image)
            current_bundle_path=current_root/'bundle.json';current_bundle_path.write_text(json.dumps(current_bundle))
            current_reference_path=current_root/'observations.json';current_reference_path.write_text(json.dumps(current_reference))
            current_skeleton_path=current_root/'skeleton.json';current_skeleton_path.write_text(json.dumps(current_skeleton))
            current_review=load_multiview_review_files(str(current_reference_path),str(current_skeleton_path),str(current_image_path),None,1)[0]
            current_from_review=build_reviewed_bundle_from_review(current_review,str(current_reference_path),str(current_skeleton_path),str(current_image_path),[str(current_image_path)])
            self.assertEqual(current_from_review,current_bundle)
            current_changed=copy.deepcopy(current_skeleton);current_changed['body_joint_positions'][0][0]+=1
            current_skeleton_path.write_text(json.dumps(current_changed))
            with self.assertRaisesRegex(ValueError,'변경'):
                build_reviewed_bundle_from_review(current_review,str(current_reference_path),str(current_skeleton_path),str(current_image_path),[str(current_image_path)])
            current_skeleton_path.write_text(json.dumps(current_skeleton))
            current_selected=load_reviewed_multiview_bundle(str(current_bundle_path),[str(current_image_path)])
            current_inputs=('stand still',90,10,42,2,0,True,['front'],False,True,[str(current_image_path)],85,False,False,'',None,[],0,'',current_selected)
            current_payload=build_kimodo_payload(*current_inputs)
            self.assertEqual(current_payload['proportion_reviewed_multiview'],current_bundle)
            from generators.kimodo.multiview_face_anchor_experiment import create_face_anchor_calibration
            current_source={'frame':0,**{current_key:'a'*64 for current_key in ('motion_sha256','skeleton_sha256','reference_sha256','render_sha256','head_anchors_sha256')}}
            current_calibration=create_face_anchor_calibration(current_skeleton,[f'joint_{current_index}' for current_index in range(77)],[[0.,0.,0.]]*5,current_source)
            current_payload=build_kimodo_payload(*current_inputs,True,current_calibration)
            self.assertTrue(current_payload['proportion_projected_hip'])
            self.assertEqual(current_payload['proportion_face_anchor_calibration'],current_calibration)
            with self.assertRaisesRegex(ValueError,'검수'):
                validate_kimodo_request({**{current_key:current_value for current_key,current_value in current_request.items() if current_key!='proportion_reviewed_multiview'},'proportion_face_anchor_calibration':current_calibration})
            current_legacy=create_face_anchor_calibration(current_skeleton,[f'joint_{current_index}' for current_index in range(77)],[[0.,0.,0.]]*5)
            with self.assertRaisesRegex(ValueError,'교정'):
                validate_kimodo_request({**current_request,'proportion_face_anchor_calibration':current_legacy})
            with self.assertRaisesRegex(ValueError,'검수'):
                validate_kimodo_request({**{current_key:current_value for current_key,current_value in current_request.items() if current_key!='proportion_reviewed_multiview'},'proportion_projected_hip':True})
            current_saved={**current_payload,'references':['reference-1.png']};current_saved.pop('proportion_images')
            with patch('tools.review.ui.gradio.kimodo_app.KIMODO_JOB_STORAGE',current_root):
                current_restored=restore_kimodo_inputs({'id':'trial','request':current_saved})
            self.assertEqual(build_kimodo_payload(*current_restored[:-1])['proportion_reviewed_multiview'],current_bundle)
            self.assertTrue(build_kimodo_payload(*current_restored[:-1])['proportion_projected_hip'])
            self.assertEqual(build_kimodo_payload(*current_restored[:-1])['proportion_face_anchor_calibration'],current_calibration)
            Image.new('RGB',(64,64),'black').save(current_image_path)
            with self.assertRaisesRegex(ValueError,'이미지'):
                load_reviewed_multiview_bundle(str(current_bundle_path),[str(current_image_path)])
        with self.assertRaisesRegex(ValueError,'이미지'):
            validate_reviewed_multiview_bundle(current_bundle,['b'*64])
        current_changed=copy.deepcopy(current_bundle);current_changed['reference_observations']['keypoints'][0][2][0]+=1
        with self.assertRaisesRegex(ValueError,'관측'):
            validate_reviewed_multiview_bundle(current_changed,[current_hash])
        current_changed=copy.deepcopy(current_bundle);current_changed['skeleton']['excluded_body']=[0,2]
        with self.assertRaisesRegex(ValueError,'최종 골격'):
            validate_reviewed_multiview_bundle(current_changed,[current_hash])


if __name__=='__main__':
    unittest.main()
