import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WriterNavigationUiTests(unittest.TestCase):
    def test_standalone_and_embedded_have_named_navigation_regions(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'writer.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WriterPage.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1]).default;
              for(const embedded of [false,true])console.log(server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'session'})));"""
            lines = subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),2)
        for markup in lines:
            self.assertIn('aria-label="생성기 영역 이동"',markup)
            self.assertIn('aria-label="작가 작업 입력"',markup)
            self.assertIn('aria-label="작가 작업 이력"',markup)
            self.assertIn('결과는 이력에서 작업을 선택하면 볼 수 있습니다.',markup)
            self.assertLess(markup.index('aria-label="작가 작업 입력"'),markup.index('aria-label="작가 작업 이력"'))


if __name__ == '__main__':
    unittest.main()
