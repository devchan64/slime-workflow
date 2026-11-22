"""얼굴 깊이 결과 요약과 오류 기록 표시를 검증한다."""
import copy
import unittest
from workflow.domains.kimodo.face_anchor_depth import summarize_face_anchor_depth
import json
import os
from pathlib import Path
import subprocess
import tempfile


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
        current_invalid=summarize_face_anchor_depth({'schema':'kimodo-face-anchor-depth-v1'},2,['front'])
        self.assertEqual(current_invalid['status'],'invalid')
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'media.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KimodoMedia.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');const {FaceDepthSummary}=require(process.argv[1]);const values=JSON.parse(process.argv[2]);
              for(const value of values)process.stdout.write(server.renderToStaticMarkup(React.createElement(FaceDepthSummary,{summary:value}))+'\\n');"""
            markup=subprocess.check_output(['node','-e',script,str(bundle),json.dumps([current_summary,current_invalid],ensure_ascii=False)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('가림 부위는 판정하지',markup)
        self.assertIn('사용 불가',markup)
        self.assertIn('1 / 2',markup)
        current_broken=copy.deepcopy(current_record);current_broken['directions']['front'][0][0]['depth_gap']=9
        with self.assertRaisesRegex(ValueError,'깊이 차이'):
            summarize_face_anchor_depth(current_broken,2,['front'])
        with self.assertRaisesRegex(ValueError,'방향'):
            summarize_face_anchor_depth(current_record,2,['left'])


if __name__=='__main__':
    unittest.main()
