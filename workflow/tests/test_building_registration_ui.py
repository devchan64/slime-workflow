"""건물 등록 입력의 ID와 이미지 제한 안내 연결을 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class BuildingRegistrationUiTests(unittest.TestCase):
    def test_registration_input_descriptions(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'building.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'BuildingEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Form=require(process.argv[1]).BuildingRegistration;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Form,{generation:1,busy:false,setBusy:()=>{},onRegistered:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        for name, text in [('texture', 'town-으로 시작'), ('image', '최대 16MiB')]:
            element = re.search(r'<input[^>]*name="'+name+r'"[^>]*>', markup).group()
            identifier = re.search(r'aria-describedby="([^"]+)"', element).group(1)
            self.assertRegex(markup, r'id="'+re.escape(identifier)+r'">[^<]*'+text)

    def test_asset_list_exposes_selected_state(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'building.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'BuildingEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),List=require(process.argv[1]).BuildingAssetList;
              const assets=[{texture:'town-long-building-v1'},{texture:'town-other-v1'}];
              process.stdout.write(server.renderToStaticMarkup(React.createElement(List,{assets,selected:assets[0].texture,disabled:false,image:id=>'/image/'+id,onSelect:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('aria-label="건물 카드 갤러리"', markup)
        self.assertIn('placeholder="건물 ID 검색"', markup)
        self.assertIn('aria-label="건물 페이지 이동"', markup)
        self.assertEqual(markup.count('aria-pressed="true"'), 1)
        self.assertEqual(markup.count('aria-pressed="false"'), 1)
        self.assertIn('선택한 건물 · town-long-building-v1', markup)


if __name__ == '__main__':
    unittest.main()
