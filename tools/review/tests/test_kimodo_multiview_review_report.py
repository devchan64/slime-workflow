"""8방향 재투영 검수 기록의 포함·제외 계약을 확인한다."""
import unittest
import tempfile
import json
import hashlib
import os
import gradio as gr
from pathlib import Path
from PIL import Image
from generators.kimodo.multiview_review_report import build_multiview_review_report, render_multiview_review_overlay
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash


class KimodoMultiviewReviewReportTests(unittest.TestCase):
    def test_report_preserves_weights_and_separates_heldout(self):
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':0 if current_joint==0 else 1,'reason':'가림' if current_joint==0 else '사용'} for current_joint in range(18)]} for current_index in range(8)]}
        current_points=[[[float(current_joint),float(current_joint),.9] for current_joint in range(18)] for _ in range(8)]
        current_views=[]
        for current_index in range(8):
            current_views.append({'observation':current_index+1,'fitted_yaw_degrees':current_index*45,'body_xy':[[float(current_joint+3),float(current_joint)] for current_joint in range(2,14)],'face_xy':[[float(current_joint+3),float(current_joint)] for current_joint in (0,14,15,16,17)],'body_fit_weights':[.9]*12,'face_fit_weights':[0,.9,.9,.9,.9]})
        current_skeleton={'schema':'kimodo-multiview-body-face-experiment-v1','body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'joint_weight_table':current_weights,'views':current_views}
        current_reference={'keypoints':current_points,'observation_sources':[{'bbox':[0,0,32,32]} for _ in range(8)]}
        current_skeleton['observation_sha256']=calculate_multiview_observation_hash(current_reference)
        current_heldout={'observation_sha256':current_skeleton['observation_sha256'],'joint_weight_table':current_weights,'excluded_observations':[{'observation':1,'joint':2,'error_px':8.0},{'observation':1,'joint':14,'error_px':4.0}]}
        current_report=build_multiview_review_report(current_reference,current_skeleton,current_heldout)
        current_joints={current_row['joint']:current_row for current_row in current_report['views'][0]['joints']}
        self.assertEqual(current_joints[2]['fitted_error_px'],3.)
        self.assertEqual(current_joints[2]['heldout']['error_px'],8.)
        self.assertEqual(current_joints[14]['heldout']['error_px'],4.)
        self.assertIsNone(current_joints[0]['fitted_error_px'])
        self.assertEqual(current_joints[0]['weight_reason'],'가림')
        self.assertEqual(render_multiview_review_overlay(Image.new('RGB',(32,32)),current_report).size,(32,32))
        from tools.review.ui.gradio.kimodo_app import load_multiview_review_files, select_multiview_review_rows,load_multiview_weight_editor,save_multiview_weight_editor
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_root=Path(current_temporary_root)
            current_image_path=current_root/'reference.png'
            Image.new('RGB',(32,32)).save(current_image_path)
            current_hash=hashlib.sha256(current_image_path.read_bytes()).hexdigest()
            current_skeleton['reference_image_sha256']=[current_hash]
            current_reference['reference_image_sha256']=[current_hash]
            current_reference_path=current_root/'reference.json';current_reference_path.write_text(json.dumps(current_reference))
            current_skeleton_path=current_root/'skeleton.json';current_skeleton_path.write_text(json.dumps(current_skeleton))
            current_heldout_path=current_root/'heldout.json';current_heldout_path.write_text(json.dumps(current_heldout))
            current_loaded=load_multiview_review_files(str(current_reference_path),str(current_skeleton_path),str(current_image_path),str(current_heldout_path),1)
            self.assertEqual(len(current_loaded[3]),17)
            self.assertEqual(len(select_multiview_review_rows(current_loaded[0],8)),17)
            current_rows,current_editor_state,_=load_multiview_weight_editor(current_loaded[0],str(current_reference_path),str(current_skeleton_path),str(current_image_path))
            self.assertEqual(len(current_rows),144)
            current_rows[2][2]='0.25';current_rows[2][3]='측면 검토'
            current_export,_=save_multiview_weight_editor(current_rows,current_editor_state,current_loaded[0],str(current_reference_path),str(current_skeleton_path),str(current_image_path))
            try:
                self.assertEqual(json.loads(Path(current_export).read_text())['views'][0]['joints'][2]['weight'],.25)
            finally:
                os.unlink(current_export)
            current_rows[2][0]=8
            with self.assertRaisesRegex(gr.Error,'관측 번호'):
                save_multiview_weight_editor(current_rows,current_editor_state,current_loaded[0],str(current_reference_path),str(current_skeleton_path),str(current_image_path))
            current_rows[2][0]=1;current_rows[2][2]=2
            with self.assertRaisesRegex(gr.Error,'가중치'):
                save_multiview_weight_editor(current_rows,current_editor_state,current_loaded[0],str(current_reference_path),str(current_skeleton_path),str(current_image_path))
            current_skeleton_path.write_text(json.dumps({**current_skeleton,'changed':True}))
            with self.assertRaisesRegex(gr.Error,'변경'):
                save_multiview_weight_editor(current_rows,current_editor_state,current_loaded[0],str(current_reference_path),str(current_skeleton_path),str(current_image_path))
            current_skeleton_path.write_text(json.dumps(current_skeleton))
            Image.new('RGB',(31,32)).save(current_image_path)
            with self.assertRaisesRegex(ValueError,'해시'):
                load_multiview_review_files(str(current_reference_path),str(current_skeleton_path),str(current_image_path),str(current_heldout_path),1)
        current_skeleton['fit_context_sha256']='a'*64
        current_heldout['fit_context_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'초기 추정'):
            build_multiview_review_report(current_reference,current_skeleton,current_heldout)
        del current_skeleton['fit_context_sha256'];del current_heldout['fit_context_sha256']
        current_points[0][2][0]+=1
        with self.assertRaisesRegex(ValueError,'출처'):
            build_multiview_review_report(current_reference,current_skeleton,current_heldout)
        current_points[0][2][0]-=1
        current_heldout['excluded_observations'].append({'observation':1,'joint':2,'error_px':3.})
        with self.assertRaisesRegex(ValueError,'중복'):
            build_multiview_review_report(current_reference,current_skeleton,current_heldout)


if __name__=='__main__':
    unittest.main()
