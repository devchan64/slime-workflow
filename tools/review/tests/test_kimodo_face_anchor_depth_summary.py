"""얼굴 깊이 결과 요약과 오류 기록 표시를 검증한다."""
import copy
import unittest
from tools.review.domains.kimodo.face_anchor_depth import summarize_face_anchor_depth
from tools.review.ui.gradio.kimodo_app import render_face_depth_summary


class KimodoFaceDepthSummaryTests(unittest.TestCase):
    def test_summary_preserves_missing_and_rejects_invalid_depth(self):
        current_frame=[{'joint':current_joint,'pixel_xy':[3.,4.],'anchor_depth':6.,'surface_depth':5.8,'depth_gap':.2} for current_joint in (0,14,15,16,17)]
        current_missing=copy.deepcopy(current_frame)
        current_missing[4]['surface_depth']=None;current_missing[4]['depth_gap']=None
        current_record={'schema':'kimodo-face-anchor-depth-v2','directions':{'front':[current_frame,current_missing]}}
        current_summary=summarize_face_anchor_depth(current_record,2,['front'])
        current_ear=current_summary['rows'][-1]
        self.assertEqual((current_ear['measured'],current_ear['total']),(1,2))
        self.assertAlmostEqual(current_ear['median_gap'],.2)
        self.assertIn('가림 부위는 판정하지',render_face_depth_summary(current_summary))
        current_invalid=summarize_face_anchor_depth({'schema':'kimodo-face-anchor-depth-v1'},2,['front'])
        self.assertEqual(current_invalid['status'],'invalid')
        self.assertIn('사용 불가',render_face_depth_summary(current_invalid))
        current_broken=copy.deepcopy(current_record);current_broken['directions']['front'][0][0]['depth_gap']=9
        with self.assertRaisesRegex(ValueError,'깊이 차이'):
            summarize_face_anchor_depth(current_broken,2,['front'])
        with self.assertRaisesRegex(ValueError,'방향'):
            summarize_face_anchor_depth(current_record,2,['left'])


if __name__=='__main__':
    unittest.main()
