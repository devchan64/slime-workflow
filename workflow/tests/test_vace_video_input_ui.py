"""VACE 영상 입력의 제한과 오류 설명 연결을 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class VaceVideoInputUiTests(unittest.TestCase):
    def test_multiple_inputs_have_independent_descriptions(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'video.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'VaceVideoInput.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Input=require(process.argv[1]).default,e=React.createElement;
              process.stdout.write(server.renderToStaticMarkup(e(React.Fragment,null,e(Input,{label:'원본',visible:true,error:'영상 오류',file:{name:'old.mp4'}}),e(Input,{label:'마스크',visible:true,checking:true}))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        inputs = re.findall(r'<input\b[^>]*>', markup)
        self.assertEqual(len(inputs), 2)
        descriptions = [re.search(r'aria-describedby="([^"]+)"', item).group(1).split() for item in inputs]
        self.assertEqual([len(ids) for ids in descriptions], [2, 1])
        self.assertEqual(len(set(sum(descriptions, []))), 3)
        for identifier in sum(descriptions, []):
            self.assertIn(f'id="{identifier}"', markup)
        self.assertIn('aria-invalid="true"', inputs[0])
        self.assertIn('기존 영상은 유지됩니다.', markup)
        self.assertIn('원본 · 영상 오류', markup)
        self.assertIn('마스크 영상 정보 확인 중…', markup)
        self.assertIn('MP4 · 파일당 최대 32MiB', markup)


if __name__ == '__main__':
    unittest.main()
