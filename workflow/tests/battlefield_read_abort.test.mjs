import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
const source=readFileSync(new URL('../../gui/BattlefieldReview.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('    async function read(url){'),source.indexOf('    async function mount(){'));
test('전장 목록 요청과 본문이 중단을 무시해도 조회를 종료한다',async()=>{
 for(const stage of ['fetch','json']){
  let finish;const abort=new AbortController(),delayed=new Promise(done=>finish=done),context=vm.createContext({abort,untilAborted,fetch:()=>stage==='fetch'?delayed:Promise.resolve({ok:true,json:()=>delayed})});
  vm.runInContext(code+'\nthis.read=read;',context);const promise=context.read('/catalog');await Promise.resolve();abort.abort();await assert.rejects(promise,{name:'AbortError'});finish(stage==='fetch'?{ok:true,json:async()=>({})}:{});
 }
});
