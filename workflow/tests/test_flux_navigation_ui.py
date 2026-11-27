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
              global.location.search='?job=2026-11-26_21-37-53-f56ab55d&session=s';
              for(const service of ['flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless','flux-expression'])console.log(server.renderToStaticMarkup(React.createElement(Page,{serviceOverride:service})));
              global.location.search='?job=invalid&session=s';console.log(server.renderToStaticMarkup(React.createElement(Page,{serviceOverride:'flux-building'})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),28)
        for index, markup in enumerate(lines[:18]):
            if index % 2 == 0:
                self.assertIn('aria-label="생성기 페이지 이동"', markup)
                self.assertIn('생성 이력 새 탭에서 열기', markup)
                self.assertIn('/management/frame/flux-image-history/?service=', markup)
            else:
                self.assertIn('aria-label="생성기 영역 이동"', markup)
                self.assertIn('생성기 설정을 확인해야 이력을 볼 수 있습니다.', markup)
                self.assertIn('생성 입력을 불러오는 중입니다.', markup)
        services=['flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless','flux-expression']
        for service,markup in zip(services,lines[18:27]):
            with self.subTest(service=service):
                self.assertIn('FLUX 이미지 생성이력', markup)
                self.assertIn('결과 선택됨', markup)
                self.assertIn(f'/management/frame/{service}-generator/?session=s', markup)
                self.assertIn(f'<option value="{service}" selected="">', markup)
        self.assertIn('작업 ID를 확인할 수 없습니다.',lines[27])
        self.assertIn('/management/frame/flux-building-generator/?session=s',lines[27])



if __name__=='__main__':
    unittest.main()
