"""맵 DB 접수 확인의 필수 입력 안내를 검증한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MapReceiptUiTests(unittest.TestCase):
    def test_initial_action_describes_missing_inputs(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'receipt.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapDatabaseReceipt.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Page=require(process.argv[1]).default,html=server.renderToStaticMarkup(React.createElement(Page));
const match=html.match(/<button[^>]*disabled="" aria-describedby="([^"]+)"[^>]*>DB 접수 확인/);
assert.ok(match);assert.ok(html.includes('id="'+match[1]+'"'));assert.match(html,/180자 이내의 DB 요청 ID를 입력하세요/);
assert.match(html,/원본 요청 SHA-256 해시 64자리를 입력하세요/);assert.match(html,/<legend[^>]*>맵 DB 접수 조회 입력<\\/legend>/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
