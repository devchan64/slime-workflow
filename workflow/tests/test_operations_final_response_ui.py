"""운영 작업 최종 응답의 빈 상태와 오류 표시를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class OperationsFinalResponseUiTests(unittest.TestCase):
    def test_final_response_variants(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'operations.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'OperationsJobs.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const {FinalResponse:Response,OperationsDetailData:Detail,operationStatusLabel}=require(process.argv[1]),render=props=>server.renderToStaticMarkup(React.createElement(Response,props));
assert.equal(operationStatusLabel({completed:'완료'},'completed'),'완료');
for(const status of ['toString','constructor','__proto__'])assert.equal(operationStatusLabel({},status),status);
assert.match(render({text:null}),/기록된 최종 응답이 없습니다/);
assert.match(render({text:{invalid:true}}),/role="alert"[^>]*>최종 응답의 형식을 확인할 수 없습니다/);
const valid=render({text:'첫 줄\\n마지막 줄',truncated:true});
assert.match(valid,/<details/);assert.match(valid,/마지막 줄/);assert.match(valid,/응답 일부만 표시했습니다/);
const bad={id:'job',status:{message:{},error:[],queue_position:{}},request:{prompt:{}},final_response:{},log:{},result:{verification:{status:{},modules:[{}]}}};
const detail=server.renderToStaticMarkup(React.createElement(Detail,{detail:bad,verificationLabels:{}}));
for(const expected of ['작업 상태의 일부 형식','작업 지시 형식','최종 응답의 형식','작업 로그 형식','상태 확인 불가','검증 대상 · 확인 불가'])assert.ok(detail.includes(expected),expected);
const empty=server.renderToStaticMarkup(React.createElement(Detail,{detail:{id:'job',status:{}},verificationLabels:{}}));
assert.ok(empty.includes('기록된 지시가 없습니다.'));assert.ok(empty.includes('기록된 로그가 없습니다.'));
const unusual=server.renderToStaticMarkup(React.createElement(Detail,{detail:{id:'job',status:{},result:{verification:{status:'toString'}}},verificationLabels:{}}));
assert.ok(unusual.includes('toString'));"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
