import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
const source=readFileSync(new URL('../../gui/BattlefieldReview.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('    async function read(url){'),source.indexOf('    async function mount(){'));
test('전장 목록 요청과 본문이 중단을 무시해도 조회를 종료한다',async()=>{
 for(const stage of ['fetch','json']){
  let finish;const abort=new AbortController(),delayed=new Promise(done=>finish=done),context=vm.createContext({abort,untilAborted,fetch:()=>stage==='fetch'?delayed:Promise.resolve({ok:true,json:()=>delayed})});
  vm.runInContext(code+'\nthis.read=read;',context);const promise=context.read('/catalog');await Promise.resolve();abort.abort();await assert.rejects(promise,{name:'AbortError'});finish(stage==='fetch'?{ok:true,json:async()=>({})}:{});
 }
});
test('전장 검수 재시도는 렌더 전 중복을 막고 로딩 상태를 표시한다',()=>{
 const begin=source.indexOf('onRetry={event=>{if(retryPending.current)return;'),end=source.indexOf('}}/>}',begin);
 assert.ok(begin>=0 && end>begin);
 const handler=source.slice(begin+'onRetry={'.length,end+1);
 const button={};let revision=0,error='조회 실패';
 const context=vm.createContext({document:{activeElement:button},retryPending:{current:false},restoreFocus:{current:false},setError:value=>error=value,retry:fn=>revision=fn(revision)});
 vm.runInContext('this.run='+handler,context);context.run({currentTarget:button});context.run({currentTarget:button});
 assert.equal(revision,1);assert.equal(error,'');assert.equal(context.restoreFocus.current,true);
 assert.match(source,/finally\(\(\)=>\{clearTimeout\(timeout\);if\(active\)retryPending\.current=false;\}\)/);
});
test('전장 검수 재시도 결과는 잃은 초점만 성공·오류 위치로 복구한다',()=>{
 const begin=source.indexOf('  useEffect(()=>{\n    if(!restoreFocus.current || (!state && !error))return;');
 const end=source.indexOf('  },[state,error]);',begin)+'  },[state,error]);'.length;
 assert.ok(begin>=0 && end>begin);const effect=source.slice(begin,end);
 for(const outcome of ['success','failure','moved']){
  const body={},other={},focused=[],document={body,activeElement:outcome==='moved'?other:body};
  const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);document.activeElement=this;}});
  const context=vm.createContext({document,restoreLostFocus,restoreFocus:{current:true},state:outcome==='failure'?null:{},error:outcome==='failure'?'오류':'',selectRef:{current:target('select')},retryRef:{current:target('retry')},useEffect:fn=>fn()});
  vm.runInContext(effect,context);
  assert.deepEqual(focused,outcome==='moved'?[]:[outcome==='failure'?'retry':'select']);
  assert.equal(context.restoreFocus.current,false);
 }
});
