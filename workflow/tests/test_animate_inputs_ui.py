"""동작 전사 입력의 필수 시드와 영상 제한 안내를 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class AnimateInputsUiTests(unittest.TestCase):
    def test_seed_and_video_help_match_input_requirements(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'animate.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'AnimateInputs.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),Form=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Form,{session:'test',model:{},onJob:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        video = re.search(r'<input[^>]*aria-label="RGB 동작 MP4[^>]*>', markup).group()
        help_id = re.search(r'aria-describedby="([^"]+)"', video).group(1)
        self.assertIn(f'id="{help_id}">MP4 · 최대 32MiB', markup)
        seed = re.search(r'<label>시드(<input[^>]*>)', markup).group(1)
        self.assertRegex(seed, r'\brequired=""')
        self.assertNotIn('입력 선택 사항', markup)


if __name__ == '__main__':
    unittest.main()
