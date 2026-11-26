import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/KimodoPage.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function cleaned('));
function setup(fetch){return vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRevision:{current:0},imageChecking:{current:false},fetch,encodeURIComponent,setTimeout,clearTimeout});}

test('Kimodo 저장 입력의 잘못된 JSON은 형식 재조회 안내를 표시한다',async()=>{
 const context=setup(async()=>({ok:true,json:async()=>{throw new SyntaxError('Unexpected token');}}));vm.runInContext(code,context);
 await assert.rejects(context.readJob('job'),/저장된 Kimodo 입력 형식을 확인할 수 없습니다/);
});

test('Kimodo 저장 입력 조회는 화면 종료 시 요청과 본문 대기를 중단한다',async()=>{
 for(const stage of ['fetch','body']){
  let observed;const never=new Promise(()=>{}),context=setup((_url,options)=>{observed=options.signal;return stage==='fetch'?never:Promise.resolve({ok:true,json:()=>never});});vm.runInContext(code,context);
  const controller=new AbortController(),waiting=context.readJob('job',{signal:controller.signal});await new Promise(done=>setImmediate(done));controller.abort();await assert.rejects(waiting,error=>error.name==='AbortError');assert.equal(observed.aborted,true);
 }
});
