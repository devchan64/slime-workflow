"""MiniMax H3 독립·대화 내 화면의 기본 렌더 계약."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MiniMaxH3UiContractTests(unittest.TestCase):
    def test_standalone_and_embedded_render(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'minimax.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'MiniMaxH3Page.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile=' + str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server');
              global.location={search:''};
              const Page=require(process.argv[1]).default;
              for(const embedded of [false,true]){
                const html=server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'session-test'}));
                for(const text of ['MiniMax H3 I2V 영상 생성','생성 입력','첫 프레임 이미지','장면·동작 프롬프트','생성 요청 검토'])
                  if(!html.includes(text))throw Error('missing '+text+' embedded='+embedded);
                if(html.includes('헤르메스 대화로 돌아가기')===embedded)throw Error('return link mismatch');
              }"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, text=True, env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})


if __name__ == '__main__':
    unittest.main()
