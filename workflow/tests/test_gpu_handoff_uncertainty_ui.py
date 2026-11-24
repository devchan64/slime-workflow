"""양도 결과 미확인 상태의 버튼과 안내를 렌더링한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class GpuHandoffUncertaintyUiTests(unittest.TestCase):
    def test_uncertainty_blocks_mutations_and_keeps_status_check(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'handoff.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'GpuHandoffStatus.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Page=require(process.argv[1]).default;
              const render=()=>server.renderToStaticMarkup(React.createElement(Page,{session:'s',id:'request',service:'kimodo',status:{state:'running'},onUpdate:()=>{}}));
              global.sessionStorage={getItem:()=> 'pending'};
              let html=render();assert.match(html,/결과가 확인되지 않았습니다/);
              assert.match(html,/<button type="button" disabled=""[^>]*>생성 중지/);
              assert.match(html,/<button type="button" aria-disabled="false"[^>]*>GPU 양도 상태 확인/);
              global.sessionStorage={getItem:()=>null};html=render();
              assert.match(html,/<button type="button">생성 중지/);
              global.sessionStorage={getItem:()=>{throw Error('denied');}};html=render();
              assert.match(html,/브라우저 저장소를 사용할 수 없습니다/);
              assert.match(html,/<button type="button" disabled=""[^>]*>생성 중지/);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True,
                           capture_output=True, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})


if __name__ == '__main__':
    unittest.main()
