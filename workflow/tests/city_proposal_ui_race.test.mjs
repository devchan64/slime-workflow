import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('도시 제안 조회 종료 후 늦은 응답은 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/CityProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  return <section',source.indexOf('  async function inspect()')));
 let resolve,updates=0;const request={current:null};
 const context=vm.createContext({AbortController,request,inspectFocus:{current:false},inspectRef:{current:null},document:{activeElement:null},session:'s',job:'j',snapshot:'h',offset:0,prepareCityProposal:()=>{},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>updates++,setError:()=>updates++,setValue:()=>updates++,readProposalPreview:()=>new Promise(done=>resolve=done),requestErrorMessage});
 vm.runInContext(code,context);const pending=context.inspect();const controller=request.current;request.current=null;controller.abort();const before=updates;resolve({proposal:{}});await pending;assert.equal(updates,before);
});

test('도시 제안 결과·오류는 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/CityProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !inspectFocus\.current\).*?\},\[busy,value,error\]\);/s)?.[0];assert.ok(effect);
 for(const kind of ['result','error'])for(const moved of [false,true]){
  let run,frame,focused='';const body={},other={},document={body,activeElement:moved?other:body},target=name=>({current:{isConnected:true,focus:()=>focused=name}});
  const context=vm.createContext({document,restoreLostFocus,busy:false,value:kind==='result'?{}:null,error:kind==='error'?'오류':'',inspectFocus:{current:true},resultRef:target('result'),errorRef:target('error'),inspectRef:target('inspect'),useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?'':kind);
 }
});
