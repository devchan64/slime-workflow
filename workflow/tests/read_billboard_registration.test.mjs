import test from 'node:test';
import assert from 'node:assert/strict';
import {readBillboardRegistration,confirmedBillboardRegistration} from '../../gui/readBillboardRegistration.mjs';

test('등록 검토 응답의 필수 표시 정보를 확인한다',async()=>{
  const original=globalThis.fetch,controller=new AbortController();
  const payload={requestId:'example',expectedGeneration:3,asset:{assetId:'example',image:{path:'assets/billboards/a.png',width:32,height:64}}};
  try{
    globalThis.fetch=async()=>({ok:true,json:async()=>payload});
    assert.equal(await readBillboardRegistration('file',controller.signal),payload);
    globalThis.fetch=async()=>({ok:true,json:async()=>({...payload,asset:{}})});
    await assert.rejects(readBillboardRegistration('file',controller.signal),/응답을 확인할 수 없습니다/);
    globalThis.fetch=async()=>({ok:false,json:async()=>({error:'파일을 확인하세요'})});
    await assert.rejects(readBillboardRegistration('file',controller.signal),/파일을 확인하세요/);
  }finally{globalThis.fetch=original;}
});

test('저장 완료는 검토한 에셋과 다음 세대가 일치할 때만 인정한다',()=>{
  const review={expectedGeneration:3,asset:{assetId:'example'}};
  assert.equal(confirmedBillboardRegistration(review,{saved:true,asset:'example',generation:4}),true);
  for(const result of [{saved:false,asset:'example',generation:4},{saved:true,asset:'other',generation:4},{saved:true,asset:'example',generation:3},{}])
    assert.equal(confirmedBillboardRegistration(review,result),false);
});

test('중단을 무시하는 조회도 결과를 기다리지 않고 종료한다',async()=>{
  const original=globalThis.fetch,controller=new AbortController();let finish;
  globalThis.fetch=()=>new Promise(resolve=>{finish=resolve;});
  try{
    const pending=readBillboardRegistration('file',controller.signal);
    controller.abort();
    await assert.rejects(pending,{name:'AbortError'});
    finish({ok:true,json:async()=>({})});
  }finally{globalThis.fetch=original;}
});
