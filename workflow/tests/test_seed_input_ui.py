"""시드 입력의 안내와 오류가 입력에 연결되는지 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class SeedInputUiTests(unittest.TestCase):
    def test_range_optional_and_error_descriptions(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'seed.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'SeedInput.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Seed=require(process.argv[1]).default;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Seed,{value:'',max:2147483647,required:false,error:'시드를 확인하세요.',onChange:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('0부터 2,147,483,647까지의 정수 · 입력 선택 사항', markup)
        self.assertIn('aria-invalid="true"', markup)
        described = re.search(r'aria-describedby="([^"]+)"', markup).group(1).split()
        self.assertEqual(len(described), 2)
        for identifier in described:
            self.assertIn(f'id="{identifier}"', markup)


if __name__ == '__main__':
    unittest.main()
