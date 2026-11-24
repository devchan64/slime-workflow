import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class TranslationNavigationUiTests(unittest.TestCase):
    def test_notice_distinguishes_errors_from_status(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'translation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'TranslationPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Notice=require(process.argv[1]).TranslationNotice;
              for(const error of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Notice,{message:'안내',error})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertIn('role="status"',lines[0])
        self.assertIn('role="alert"',lines[1])

    def test_standalone_and_embedded_show_input_before_history(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'translation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'TranslationPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1]).default;
              for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'session'})));
              global.location.search='?job=sample';console.log(server.renderToStaticMarkup(React.createElement(Page)));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),3)
        for markup in lines[:2]:
            self.assertIn('aria-label="생성기 영역 이동"',markup)
            self.assertIn('aria-label="번역 입력"',markup)
            self.assertIn('class="translation-input"',markup)
            self.assertIn('aria-label="번역 이력"',markup)
            self.assertLess(markup.index('번역 요청 검토'),markup.index('aria-label="번역 이력"'))
            self.assertNotIn('선택한 번역 작업 이력 보기',markup)
        self.assertIn('선택한 번역 작업 이력 보기',lines[2])


if __name__=='__main__':
    unittest.main()
