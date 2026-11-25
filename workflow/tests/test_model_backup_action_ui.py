"""백업 조작의 비활성 사유가 버튼에 연결되는지 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ModelBackupActionUiTests(unittest.TestCase):
    def test_initial_loading_explains_each_disabled_action(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'backup.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'ModelBackupCompare.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile=' + str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Page=require(process.argv[1]).default;
const html=server.renderToStaticMarkup(React.createElement(Page));
const id=html.match(/<p id="([^"]+)">모델 목록을 불러오는 중입니다[.]<\\/p>/)[1];
for(const label of ['백업과 비교','모델 메타정보','SHA-256 검증 시작','선택한 모델 백업']){
  const tag=html.match(new RegExp('<button[^>]*>'+label+'<\\/button>'))[0];
  assert.match(tag,/disabled=""/);assert.ok(tag.includes('aria-describedby="'+id+'"'));
}
assert.equal((html.match(/모델 목록을 불러오는 중입니다[.]/g)||[]).length,1);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, text=True, env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})


if __name__ == '__main__':
    unittest.main()
