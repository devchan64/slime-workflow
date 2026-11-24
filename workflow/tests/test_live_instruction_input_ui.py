"""실행 중 지시 입력의 접근성 설명 연결을 검사한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class LiveInstructionInputUiTests(unittest.TestCase):
    def test_help_and_error_are_connected_to_the_input(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'input.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'LiveInstructionInput.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');const Input=require(process.argv[1]).default;
              const render=tooLong=>server.renderToStaticMarkup(React.createElement(Input,{text:'지시',busy:false,tooLong,onChange:()=>{}}));
              const normal=render(false),invalid=render(true);
              const help=normal.match(/<small id="([^"]+)">/)[1];assert.ok(normal.includes('aria-describedby="'+help+'"'));assert.doesNotMatch(normal,/aria-invalid="true"/);
              const error=invalid.match(/<p id="([^"]+)" role="alert">/)[1],described=invalid.match(/aria-describedby="([^"]+)"/)[1].split(' ');
              assert.equal(described.length,2);assert.ok(described.includes(error));assert.match(invalid,/aria-invalid="true"/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
