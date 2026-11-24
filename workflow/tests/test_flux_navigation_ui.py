import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class FluxNavigationUiTests(unittest.TestCase):
    def test_all_profiles_offer_navigation_in_both_contexts(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'flux.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'FluxImagePage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1]).default;
              for(const service of ['flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless','flux-expression'])for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Page,{serviceOverride:service,embedded,session:'s'})));
              global.location.search='?job=sample';console.log(server.renderToStaticMarkup(React.createElement(Page,{serviceOverride:'flux-image'})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),19)
        for markup in lines[:18]:
            self.assertIn('aria-label="생성기 영역 이동"',markup)
            self.assertIn('생성기 설정을 확인해야 이력을 볼 수 있습니다.',markup)
            self.assertIn('생성 입력을 불러오는 중입니다.',markup)
        self.assertIn('생성기 설정을 확인해야 작업 결과를 볼 수 있습니다.',lines[18])


if __name__=='__main__':
    unittest.main()
