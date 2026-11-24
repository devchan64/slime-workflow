import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class TranslationNavigationUiTests(unittest.TestCase):
    def test_standalone_and_embedded_show_input_before_history(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'translation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'TranslationPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1]).default;
              for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'session'})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),2)
        for markup in lines:
            self.assertIn('aria-label="생성기 영역 이동"',markup)
            self.assertIn('aria-label="번역 입력"',markup)
            self.assertIn('aria-label="번역 이력"',markup)
            self.assertLess(markup.index('번역 요청 검토'),markup.index('aria-label="번역 이력"'))


if __name__=='__main__':
    unittest.main()
