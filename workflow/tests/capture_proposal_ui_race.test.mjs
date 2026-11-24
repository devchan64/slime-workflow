import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('캡처 조회 오류 후 재조회하고 종료 뒤 늦은 결과를 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/CaptureProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  return <section',source.indexOf('  async function inspect()')));
 let next=()=>Promise.reject({}),error='',value=null,busy=false;const request={current:null};
 const context=vm.createContext({AbortController,request,inspectFocus:{current:false},inspectRef:{current:null},document:{activeElement:null},session:'s',job:'j',snapshot:'h',offset:0,readCaptureProposal:()=>{},setTimeout:()=>1,clearTimeout:()=>{},setBusy:v=>busy=v,setError:v=>error=v,setValue:v=>value=v,readProposalPreview:()=>next(),requestErrorMessage});
 vm.runInContext(code,context);await context.inspect();assert.ok(error);assert.equal(busy,false);assert.equal(request.current,null);
 next=()=>Promise.resolve({proposal:{}});await context.inspect();assert.equal(error,'');assert.ok(value);assert.equal(busy,false);
 let resolve;next=()=>new Promise(done=>resolve=done);const pending=context.inspect(),controller=request.current;request.current=null;controller.abort();const before=value;resolve({late:true});await pending;assert.equal(value,before);
});

test('캡처 조회 결과와 오류는 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/CaptureProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !inspectFocus\.current\).*?\},\[busy,value,error\]\);/s)?.[0];assert.ok(effect);
 for(const kind of ['result','error'])for(const moved of [false,true]){
  let run,frame,focused='';const body={},other={},document={body,activeElement:moved?other:body},target=name=>({current:{isConnected:true,focus:()=>focused=name}});
  const context=vm.createContext({document,restoreLostFocus,busy:false,value:kind==='result'?{}:null,error:kind==='error'?'오류':'',inspectFocus:{current:true},resultRef:target('result'),errorRef:target('error'),inspectRef:target('inspect'),useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?'':kind);
 }
});
