"""Render the backup controls without starting model or Samba operations."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class ModelBackupUiTest(unittest.TestCase):
    def test_initial_page_explains_unavailable_actions_and_snapshot_cost(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'backup.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'ModelBackupCompare.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile=' + str(bundle)],
                           cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'), server=require('react-dom/server'), assert=require('node:assert/strict');
                const Page=require(process.argv[1]).default;
                const html=server.renderToStaticMarkup(React.createElement(Page));
                for (const text of ['모델 백업 비교','백업과 비교','SHA-256 검증 시작','선택한 모델 백업',
                                    '디렉터리를 선택하세요','추가 공간이 필요합니다','모델 목록 조회 중']) assert.ok(html.includes(text), text);
                assert.match(html, /<button[^>]*disabled[^>]*>선택한 모델 백업<\\/button>/);
                assert.match(html, /<button[^>]*disabled[^>]*>SHA-256 검증 시작<\\/button>/);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, text=True,
                           env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})


if __name__ == '__main__':
    unittest.main()
