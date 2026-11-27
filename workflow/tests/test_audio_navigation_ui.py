import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class AudioNavigationUiTests(unittest.TestCase):
    def test_history_rejects_unregistered_service_names(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'history.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'AudioHistoryPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
              for(const service of ['invalid','constructor','toString','__proto__']){global.location={search:'?service='+service};assert.match(server.renderToStaticMarkup(React.createElement(Page)),/지원하지 않는 생성기/);}"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_music_and_effect_standalone_and_embedded_have_navigation(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),pages=require(process.argv[1]);
              for(const name of ['default','HeartmulaPage'])for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(pages[name],{embedded,session:'s'})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),4)
        for index, markup in enumerate(lines):
            self.assertIn('기본 입력을 불러오는 중입니다.',markup)
            if index % 2:
                self.assertIn('aria-label="생성기 영역 이동"',markup)
                self.assertIn('결과는 이력에서 작업을 선택하면 볼 수 있습니다.',markup)
                self.assertIn('생성 이력</legend>',markup)
            else:
                self.assertIn('aria-label="생성기 페이지 이동"',markup)
                self.assertIn('/management/frame/audio-history/?service=',markup)
                self.assertIn('생성기 생성이력 (새 탭)',markup)



if __name__=='__main__':
    unittest.main()
