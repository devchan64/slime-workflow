import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareFluxPreview} from '../../gui/fluxPreview.mjs';

function options(signal){
  return {service:'flux-image',session:'',receiptScope:null,signal,
    form:{prompt:'안개',translation_source_ko:'',width:'768',height:'512',seed:'42',steps:'16'},files:['image'],
    verifyProposal:async()=>{},readReference:async()=> 'png',
    command:async()=>{throw new Error('unexpected command');},
    fetchPreview:async()=>({ok:true,json:async()=>({prompt:'안개',translation:null})})};
}

test('검토는 숫자·이미지를 준비하고 응답 형식을 확인한다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);
  const result=await prepareFluxPreview(input);
  assert.equal(result.payload.width,768);assert.deepEqual(result.payload.images,['png']);
  assert.equal(result.result.prompt,'안개');assert.equal(result.handoff,null);
  input.fetchPreview=async()=>({ok:true,json:async()=>({prompt:null})});
  await assert.rejects(prepareFluxPreview(input),/응답을 확인/);
});

test('취소된 파일 읽기는 늦게 끝나도 미리보기 요청을 보내지 않는다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);
  let finish,requested=false;
  input.readReference=()=>new Promise(resolve=>{finish=resolve;});
  input.fetchPreview=async()=>{requested=true;throw new Error('unexpected request');};
  const pending=prepareFluxPreview(input);controller.abort();finish('png');
  await assert.rejects(pending,{name:'AbortError'});assert.equal(requested,false);
});

test('상주 상태 조회가 취소되면 늦은 응답으로 양도 검토를 시작하지 않는다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);input.session='session';
  let finish,calls=0;
  input.command=()=>{calls++;return new Promise(resolve=>{finish=resolve;});};
  const pending=prepareFluxPreview(input);
  await new Promise(resolve=>setImmediate(resolve));
  controller.abort();finish({session_id:'session',resident_id:'resident',resident:{state:'ready'}});
  await assert.rejects(pending,{name:'AbortError'});assert.equal(calls,1);
});
