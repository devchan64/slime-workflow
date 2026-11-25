import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WriterNavigationUiTests(unittest.TestCase):
    def test_initial_result_refresh_describes_wait(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'result.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WriterResult.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Result=require(process.argv[1]).default;
const html=server.renderToStaticMarkup(React.createElement(Result,{id:'job',onDeleted:()=>{}}));
const button=html.match(/<button[^>]*>결과 새로고침<\\/button>/)[0],id=button.match(/aria-describedby="([^"]+)"/)[1];
assert.match(button,/disabled=""/);assert.ok(html.includes('id="'+id+'" role="status">작업 결과를 조회하고 있습니다.'));
const Status=require(process.argv[1]).WriterStatus,render=status=>server.renderToStaticMarkup(React.createElement(Status,{status}));
for(const progress of [null,undefined,'  ',false])assert.equal(render({stage:'completed',progress}),'<p role="status">완료</p>');
assert.equal(render({stage:'running',progress:0}),'<p role="status">running · 0</p>');
assert.equal(render({stage:'completed',summary:'결과 있음'}),'<p role="status">완료 · 결과 있음</p>');"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

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
