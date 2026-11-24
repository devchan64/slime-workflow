import test from 'node:test';
import assert from 'node:assert/strict';
import {readProposalPreview,verifyProposalWithDeadline} from '../../gui/readProposalPreview.mjs';

test('검토 중단 후 늦은 응답은 후속 조회를 시작하지 않는다',async()=>{
  const original=globalThis.fetch,controller=new AbortController();let finish,calls=0;
  globalThis.fetch=()=>{calls++;return new Promise(resolve=>{finish=resolve;});};
  try{
    const preview=readProposalPreview(async command=>{await command('hermes-agent','first',{});await command('hermes-agent','second',{});},[],controller.signal);
    controller.abort();
    await assert.rejects(preview,{name:'AbortError'});
    finish({ok:true,json:async()=>({})});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(calls,1);
  }finally{globalThis.fetch=original;}
});

test('저장 전 확인 시간 초과는 저장 단계에 도달하지 않는다',async()=>{
  const originalFetch=globalThis.fetch,originalSetTimeout=globalThis.setTimeout,originalClearTimeout=globalThis.clearTimeout;
  const controller=new AbortController();let finish,calls=0,dispatched=false;
  globalThis.fetch=()=>{calls++;return new Promise(resolve=>{finish=resolve;});};
  globalThis.setTimeout=(callback)=>setImmediate(callback);
  globalThis.clearTimeout=handle=>clearImmediate(handle);
  try{
    const attempt=(async()=>{await verifyProposalWithDeadline(async command=>{await command('hermes-agent','verify',{});},[],controller);dispatched=true;})();
    await assert.rejects(attempt,/저장 전 확인 시간이 초과/);
    finish({ok:true,json:async()=>({})});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(calls,1);assert.equal(dispatched,false);
  }finally{globalThis.fetch=originalFetch;globalThis.setTimeout=originalSetTimeout;globalThis.clearTimeout=originalClearTimeout;}
});
