import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readArchiveJob} from '../../gui/readArchiveJob.mjs';

test('보관 이력 응답 형식이 잘못되면 조회 오류로 안내한다',async()=>{
  for(const response of [null,{}, {records:null}, {records:[null]}, {records:[{id:4}]}])
    await assert.rejects(readArchiveJob(async()=>response,'qwen','job'),/보관 이력 응답 형식/);
  const record={id:'job',request:{prompt:'저장된 입력'}};
  assert.equal(await readArchiveJob(async()=>({records:[record]}),'qwen','job'),record);
  assert.deepEqual(await readArchiveJob(async()=>({records:[]}),'qwen','job'),{});
});

test('보관 이력 요청에 중단 신호를 전달한다',async()=>{
  const controller=new AbortController();
  const request=readArchiveJob((_service,_operation,_payload,{signal})=>new Promise((_resolve,reject)=>{
    assert.equal(signal,controller.signal);
    signal.addEventListener('abort',()=>reject(new DOMException('중단','AbortError')),{once:true});
  }),'qwen','job',{signal:controller.signal});
  controller.abort();await assert.rejects(request,{name:'AbortError'});
});
