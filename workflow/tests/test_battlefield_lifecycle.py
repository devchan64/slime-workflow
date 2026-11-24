"""전투필드 오류 처리 시 렌더러 정리와 안내를 검증한다."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class BattlefieldLifecycleTests(unittest.TestCase):
    def test_selected_field_must_match_before_url_changes(self):
        source=(Path(__file__).resolve().parents[2]/'gui/BattlefieldReview.jsx').read_text()
        refresh='function refresh(expectedField){'+source.split('function refresh(expectedField){',1)[1].split('\n  useEffect(',1)[0]
        select='function select(field){'+source.split('function select(field){',1)[1].split('\n  const back=',1)[0]
        script=r"""
const assert=require('node:assert/strict');let result={field:'old'},changed='',failure='',state;
const controller={current:{selectField(){},readState:()=>result}},validBattlefieldState=()=>true,sameBattlefieldState=()=>false,setState=fn=>state=fn(null);
const location={href:'http://localhost/battle?field=old'},history={replaceState:(_a,_b,url)=>changed=url.href},fail=e=>failure=e.message;
REFRESH
SELECT
select('new');assert.equal(changed,'');assert.match(failure,/선택한 전장/);
result={field:'new'};failure='';select('new');assert.equal(new URL(changed).searchParams.get('field'),'new');assert.equal(state.field,'new');
""".replace('REFRESH',refresh).replace('SELECT',select)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_controls_distinguish_loading_failure_and_ready(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'battle.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BattlefieldReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Controls=require(process.argv[1]).BattlefieldControls;
const state={choices:[['전장','field-a']],field:'field-a',status:'준비 중',cameraReady:false,spawnRegionsVisible:false};
const render=s=>server.renderToStaticMarkup(React.createElement(Controls,{state:s,cameraReasonId:'reason'}));
const waiting=render(state);assert.match(waiting,/<fieldset disabled="" aria-describedby="reason"/);assert.doesNotMatch(waiting,/현재 전장 다시 불러오기/);
const failed=render({...state,status:'전장 로드 실패: 오류'});assert.match(failed,/현재 전장 다시 불러오기/);assert.match(failed,/<p role="alert">전장 로드 실패/);
const ready=render({...state,status:'완료',cameraReady:true});assert.doesNotMatch(ready,/<fieldset disabled/);assert.doesNotMatch(ready,/현재 전장 다시 불러오기/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,text=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_cleanup_failure_still_reports_error_and_stops_polling(self):
        source=(Path(__file__).resolve().parents[2]/'gui/BattlefieldReview.jsx').read_text()
        methods='function dispose(){'+source.split('function dispose(){',1)[1].split('\n  function refresh(',1)[0]
        script=r"""
const assert=require('node:assert/strict');let cleared=false,failed=false,error='',state='old',calls=0;
const pollTimer={current:1},controller={current:{dispose(){calls++;throw Error('정리 실패')}}};
const controls={current:null},restoreFocus={current:false},document={activeElement:null};
const clearInterval=()=>cleared=true,setCleanupFailed=value=>failed=value,setState=value=>state=value,setError=value=>error=value,requestErrorMessage=e=>e.message;
SOURCE
fail(Error('조회 실패'));assert.equal(cleared,true);assert.equal(pollTimer.current,null);assert.equal(controller.current,null);assert.equal(state,null);assert.equal(failed,true);assert.match(error,/조회 실패/);assert.match(error,/정리/);assert.equal(calls,1);
failed=false;error='';fail(Error('시작 실패'),true);assert.equal(failed,true);assert.match(error,/정리 여부를 확인할 수 없습니다/);assert.equal(calls,1);
""".replace('SOURCE',methods)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
