"""건물과 빌보드 원본 이미지가 올바른 URL과 대체 이름을 사용하는지 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class RecoverableImageUiTests(unittest.TestCase):
    def test_image_urls_with_and_without_existing_query(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'image.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'RecoverableImage.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Image=require(process.argv[1]).default,e=React.createElement;
              process.stdout.write(server.renderToStaticMarkup(e(React.Fragment,null,e(Image,{src:'/building/a.png',name:'건물'}),e(Image,{src:'/billboard/b.png?r=2',name:'빌보드'}))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('src="/building/a.png?retry=0"', markup)
        self.assertIn('src="/billboard/b.png?r=2&amp;retry=0"', markup)
        self.assertIn('alt="건물 원본"', markup)
        self.assertIn('alt="빌보드 원본"', markup)


if __name__ == '__main__':
    unittest.main()
