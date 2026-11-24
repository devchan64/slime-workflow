"""키프레임 중복 출력 프레임의 오류 연결을 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class KeyframePlacementUiTests(unittest.TestCase):
    def test_duplicate_frames_are_described_and_block_validation(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'keyframe.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KeyframeCatalog.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Catalog=require(process.argv[1]).default;
              const rows=[{id:'a'.repeat(32),tag:'첫째',frame:'1'},{id:'b'.repeat(32),tag:'둘째',frame:1}];
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Catalog,{query:'',initialFrames:'30',initialRows:rows})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(markup.count('aria-invalid="true"'),2)
        identifier=re.search(r'<p id="([^"]+)" role="alert">출력 프레임은 중복',markup).group(1)
        self.assertEqual(markup.count(f'aria-describedby="{identifier}"'),3)
        self.assertRegex(markup,r'<button[^>]*disabled=""[^>]*>원본과 배치 검증</button>')


if __name__ == '__main__':
    unittest.main()
