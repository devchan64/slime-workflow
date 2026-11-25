"""자동 갱신 이름과 상태 설명이 분리되는지 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class LiveRefreshControlUiTests(unittest.TestCase):
    def test_control_name_stays_fixed_and_describes_state(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'live.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'LiveRefresh.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Control=require(process.argv[1]).LiveRefreshControl;
for(const [active,visible,expected] of [[true,true,'30초 간격'],[true,false,'화면에 보이면 갱신'],[false,true,'작업 종료로 중지']]){
  const html=server.renderToStaticMarkup(React.createElement(Control,{label:'결과 자동 갱신',inactiveReason:'작업 종료로 중지',live:{enabled:true,active,visible,interval:30000,setEnabled:()=>{}}}));
  const input=html.match(/<input[^>]*>/)[0],id=input.match(/aria-describedby="([^"]+)"/)[1];
  assert.ok(input.includes('aria-label="결과 자동 갱신"'));assert.ok(html.includes('id="'+id+'"'));assert.ok(html.includes(expected));
}"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})


if __name__=='__main__':
    unittest.main()
