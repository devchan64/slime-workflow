import test from 'node:test';
import assert from 'node:assert/strict';
import {readKimodoInput,readKimodoJson} from '../../gui/readKimodoInput.mjs';

test('생성 기본값과 저장 입력 응답 오류를 구분한다',async()=>{
  const controller=new AbortController(),value={inputs:{prompt:'test'}};
  assert.equal(await readKimodoInput('/template',controller.signal,{fetcher:async()=>({ok:true,json:async()=>value})}),value);
  await assert.rejects(readKimodoInput('/saved',controller.signal,{restored:true,fetcher:async()=>({ok:false})}),/이전 작업의 입력/);
});

test('응답과 본문이 중단을 무시해도 조회를 종료한다',async()=>{
  for(const stage of ['response','body']){
    const controller=new AbortController();let finish;
    const pendingPromise=new Promise(resolve=>{finish=resolve;});
    const fetcher=stage==='response' ? ()=>pendingPromise : async()=>({ok:true,json:()=>pendingPromise});
    const pending=readKimodoInput('/input',controller.signal,{fetcher});
    if(stage==='body')await new Promise(resolve=>setImmediate(resolve));
    controller.abort();await assert.rejects(pending,{name:'AbortError'});
    finish(stage==='response' ? {ok:true,json:async()=>({})} : {});
  }
});

test('공통 예시 조회는 중단된 요청을 보내지 않고 화면별 오류를 보존한다',async()=>{
  const controller=new AbortController();controller.abort();let called=false;
  await assert.rejects(readKimodoJson('/example',controller.signal,'예시 오류',()=>{called=true;}),{name:'AbortError'});
  assert.equal(called,false);
  await assert.rejects(readKimodoJson('/example',new AbortController().signal,'예시 오류',async()=>({ok:false})),/예시 오류/);
});
