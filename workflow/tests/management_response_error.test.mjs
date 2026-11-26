import {test} from 'node:test';
import assert from 'node:assert/strict';
import {managementCommand} from '../../gui/managementCommand.js';

test('관리 요청의 잘못된 JSON은 재시도 안내로 바꾸고 중단은 보존한다',async()=>{
 const original=globalThis.fetch;
 try{
  for(const ok of [false,true]){
   globalThis.fetch=async()=>({ok,json:async()=>{throw new SyntaxError('Unexpected token');}});
   await assert.rejects(managementCommand('wan22-vace','history-observe'),/서버 응답을 확인할 수 없습니다/);
  }
  const controller=new AbortController();
  globalThis.fetch=async()=>({ok:true,json:async()=>{controller.abort();throw new DOMException('aborted','AbortError');}});
  await assert.rejects(managementCommand('wan22-vace','history-observe',{}, {signal:controller.signal}),error=>error.name==='AbortError');
 }finally{globalThis.fetch=original;}
});

test('관리 요청의 오류 본문이 비어 있거나 문자열이 아니면 기본 안내를 사용한다',async()=>{
 const original=globalThis.fetch;
 try{
  for(const body of [null,{}, {error:{message:'invalid'}}, {detail:[]}]){
   globalThis.fetch=async()=>({ok:false,json:async()=>body});
   await assert.rejects(managementCommand('wan22-vace','history-observe'),{message:'요청을 처리할 수 없습니다.'});
  }
  globalThis.fetch=async()=>({ok:false,json:async()=>({error:{},detail:'다시 확인하세요.'})});
  await assert.rejects(managementCommand('wan22-vace','history-observe'),{message:'다시 확인하세요.'});
 }finally{globalThis.fetch=original;}
});
