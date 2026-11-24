"""보관 서비스가 없는 직접 주소의 안내를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class QwenArchiveMissingServiceTests(unittest.TestCase):
    def test_missing_service_has_recovery_link(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'archive.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'QwenArchive.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
global.location={search:'?session=abc'};const Page=require(process.argv[1]).default;
const text=server.renderToStaticMarkup(React.createElement(Page));assert.match(text,/서비스가 지정되지 않았습니다/);assert.match(text,/href="\\/management\\/frame\\/hermes-agent\\/\\?session=abc"/);assert.doesNotMatch(text,/이력 조회/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
