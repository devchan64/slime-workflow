import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('준비 상태 재조회 중 이전 관측을 유지하고 실패 시 작업을 잠근다',async()=>{
  const source=readFileSync(new URL('../../gui/WriterActions.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    let active=true,timer,controller;'),end=source.indexOf('  async function submit(mode)',start);
  let cleanup,workspace=null,checkedAt=null,error='',checking=false,revision=0,resolve;const pending={current:true};
  const initial={configured:true,ready:true,trained:true,document_root:'docs',index_path:'index',state_root:'state',jobs:[]};
  const delayed=new Promise(done=>resolve=done);let calls=0;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,revision:0,statePending:pending,useEffect:fn=>cleanup=fn(),setTimeout,clearTimeout,
    setStateChecking:value=>checking=value,setStateError:value=>error=value,setWorkspace:value=>workspace=value,setStateCheckedAt:value=>checkedAt=value,onWorkspace:()=>{},refresh:fn=>revision=fn(revision),
    managementCommand:()=>++calls===1?Promise.resolve(initial):delayed});
  const code=source.slice(start,end);vm.runInContext(code,context);await new Promise(done=>setImmediate(done));assert.equal(workspace,initial);assert.equal(checking,false);const lastCheck=checkedAt;assert.ok(lastCheck);
  context.reload();assert.equal(workspace,initial);assert.equal(checking,true);assert.equal(pending.current,true);assert.equal(revision,1);
  cleanup();vm.runInContext(code.slice(0,code.indexOf('  function reload()')),context);resolve(null);await new Promise(done=>setImmediate(done));
  assert.equal(workspace,initial);assert.equal(checkedAt,lastCheck);assert.match(error,/응답 형식/);assert.equal(checking,false);assert.equal(pending.current,false);cleanup();
});

test('준비 상태 시간 초과 또는 화면 종료 뒤 늦은 응답을 적용하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/WriterActions.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    let active=true,timer,controller;'),end=source.indexOf('  function reload()',start);
  for(const action of ['timeout','close']){
    let cleanup,timer,resolve,error='',checking=false,updates=0;const pending={current:true};
    const response=new Promise(done=>resolve=done);
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,revision:0,statePending:pending,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},
      setStateChecking:value=>checking=value,setStateError:value=>error=value,setWorkspace:()=>updates++,setStateCheckedAt:()=>updates++,onWorkspace:()=>updates++,managementCommand:()=>response});
    vm.runInContext(source.slice(start,end),context);if(action==='timeout')timer();else cleanup();
    await new Promise(done=>setImmediate(done));resolve({configured:false,ready:false,jobs:[]});await new Promise(done=>setImmediate(done));
    assert.equal(updates,0);
    if(action==='timeout'){assert.match(error,/시간이 초과/);assert.equal(checking,false);assert.equal(pending.current,false);cleanup();}
    else assert.equal(error,'');
  }
});
