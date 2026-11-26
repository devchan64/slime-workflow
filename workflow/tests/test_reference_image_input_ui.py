"""참조 이미지 입력의 설명 연결을 검증한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ReferenceImageInputUiTests(unittest.TestCase):
    def test_limit_is_connected_to_the_file_input(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'input.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ReferenceImageInput.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Input=require(process.argv[1]).default;
              const html=server.renderToStaticMarkup(React.createElement(Input,{label:'참조',accept:'image/png',maxBytes:3000000,onChange:()=>{}}));
              const id=html.match(/<small id="([^"]+)">PNG/)[1];
              assert.ok(html.includes('aria-describedby="'+id+'"'));assert.match(html,/aria-invalid="false"/);
              const general=server.renderToStaticMarkup(React.createElement(Input,{label:'참조',accept:'image/*',maxBytes:3000000,onChange:()=>{}}));
              assert.doesNotMatch(general,/>PNG · 파일당/);
              const slots=server.renderToStaticMarkup(React.createElement(React.Fragment,null,...['참조 1','참조 2'].map(label=>React.createElement(Input,{key:label,label,onChange:()=>{}}))));
              assert.match(slots,/role="group" aria-label="참조 1"/);assert.match(slots,/role="group" aria-label="참조 2"/);
              const failure=server.renderToStaticMarkup(React.createElement(Input,{label:'참조',source:'data:image/png;base64,AA==',externalError:'이미지 적용 실패 · 기존 이미지는 유지됩니다.',onChange:()=>{}}));
              const failureId=failure.match(/<p id="([^"]+)" role="alert">/)[1];
              assert.match(failure,/aria-invalid="true"/);assert.ok(failure.includes('aria-describedby="'+failureId+'"'));
              assert.equal((failure.match(/기존 이미지는 유지됩니다/g)||[]).length,1);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,text=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
