import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class FunNavigationUiTests(unittest.TestCase):
    def test_standalone_and_embedded_offer_navigation_while_input_loads(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'fun.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'FunControlPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1]).default;
              for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'s'})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),2)
        self.assertIn('생성 입력을 불러오는 중입니다.', lines[0])
        self.assertIn('aria-label="생성기 페이지 이동"', lines[0])
        self.assertIn('/management/frame/wan22-fun-control-history/?', lines[0])
        self.assertIn('생성기 생성이력 (새 탭)', lines[0])
        self.assertIn('aria-label="생성기 영역 이동"', lines[1])
        self.assertIn('생성 입력을 불러오는 중입니다.', lines[1])
        self.assertIn('결과는 이력에서 작업을 선택하면 볼 수 있습니다.', lines[1])
        self.assertIn('aria-label="작업 이력"', lines[1])



if __name__=='__main__':
    unittest.main()
