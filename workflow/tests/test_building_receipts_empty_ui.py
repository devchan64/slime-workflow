"""대화 에셋 접수의 초기·페이지 빈 상태를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class BuildingReceiptsEmptyUiTests(unittest.TestCase):
    def test_empty_state_distinguishes_page_and_unqueried(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'receipts.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'BuildingSessionReceipts.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),render=require('react-dom/server').renderToStaticMarkup,assert=require('node:assert/strict');
const Empty=require(process.argv[1]).BuildingReceiptEmptyState;
const show=props=>render(React.createElement(Empty,{session:'session',page:null,busy:false,error:'',rowCount:0,...props}));
assert.match(show({}),/접수 조회를 눌러/);
assert.match(show({page:{offset:0,next_offset:6}}),/현재 조회한 대화 페이지에는/);
assert.match(show({page:{offset:0,next_offset:6}}),/다른 대화 페이지/);
assert.doesNotMatch(show({page:{offset:0,next_offset:null}}),/다른 대화 페이지/);
for(const props of [{session:null},{busy:true},{error:'실패'},{page:{offset:0,next_offset:null},rowCount:1}])assert.equal(show(props),'');"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
