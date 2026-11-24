import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class AudioNoticeUiTests(unittest.TestCase):
    def test_shared_active_status_renders_loading_error_and_selected_job(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'active.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ActiveGeneratorJob.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Status=require(process.argv[1]).ActiveGeneratorJobStatus;
              const props=[{loading:true,showRetry:true},{error:'실패',showRetry:true},{activeId:'job-a',job:'job-b',showRetry:true},{activeId:'job-a',job:'job-a',showRetry:true}];
              process.stdout.write(JSON.stringify(props.map(p=>server.renderToStaticMarkup(React.createElement(Status,p)))));"""
            import json
            values=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}))
        self.assertIn('role="status"',values[0])
        self.assertNotIn('다시 확인',values[0])
        self.assertIn('role="alert"',values[1])
        self.assertIn('다시 확인',values[1])
        import re
        error_id=re.search(r'<p id="([^"]+)" role="alert"',values[1]).group(1)
        self.assertIn('aria-describedby="'+error_id+'"',values[1])
        self.assertIn('aria-label="job-a 진행 작업 결과 보기"',values[2])
        self.assertNotIn('진행 작업 결과 보기',values[3])

    def test_active_result_button_tracks_selection_and_errors(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Status=require(process.argv[1]).AudioActiveStatus;
              const props=[{activeId:'id',job:'other'},{activeId:'id',job:'id'},{activeId:'id',job:'other',error:'오류'},{activeId:'',job:''}];
              process.stdout.write(JSON.stringify(props.map(p=>server.renderToStaticMarkup(React.createElement(Status,p)))));"""
            import json
            values=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}))
        self.assertIn('aria-label="id 진행 작업 결과 보기"',values[0])
        self.assertNotIn('진행 작업 결과 보기',values[1])
        self.assertNotIn('진행 작업 결과 보기',values[2])
        self.assertIn('진행 작업 다시 확인',values[2])
        self.assertNotIn('<button',values[3])

    def test_review_pending_is_not_repeated_during_submission(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Pending=require(process.argv[1]).AudioReviewPending;
              process.stdout.write(JSON.stringify([[true,null],[true,{}],[false,null]].map(([busy,review])=>server.renderToStaticMarkup(React.createElement(Pending,{busy,review})))));"""
            import json
            values=json.loads(subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}))
        self.assertIn('role="status"',values[0])
        self.assertIn('검토하고 있습니다',values[0])
        self.assertEqual(values[1:],['',''])

    def test_error_and_success_have_distinct_roles(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Notice=require(process.argv[1]).AudioNotice;
              for(const error of [true,false])console.log(server.renderToStaticMarkup(React.createElement(Notice,{notice:'안내',error})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertIn('role="alert"',lines[0])
        self.assertIn('role="status"',lines[1])


if __name__ == '__main__':
    unittest.main()
