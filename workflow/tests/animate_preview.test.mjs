import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareAnimatePreview} from '../../gui/animatePreview.mjs';

function options(signal){
  return {reference:'image',motion:'video',prompt:'걷기',frames:21,steps:40,seed:42,lora:'none',signal,
    materialize:async value=>value,referencePng:async()=> 'png',videoData:async()=> 'mp4',previewHandoff:async()=>{}};
}

test('검토는 확인한 입력을 하나의 요청으로 조합한다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);let seen;
  input.previewHandoff=async request=>{seen=request;};
  const request=await prepareAnimatePreview(input);
  assert.equal(request,seen);assert.deepEqual(request.images,['png']);assert.equal(request.driving_video,'mp4');
  assert.equal(request.frames,21);assert.equal(request.width,832);
});

test('참조 이미지 읽기 취소 후 영상과 양도 검토를 시작하지 않는다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);let finish,reads=0,handoffs=0;
  input.materialize=()=>{reads++;return new Promise(resolve=>{finish=resolve;});};
  input.previewHandoff=async()=>{handoffs++;};
  const pending=prepareAnimatePreview(input);controller.abort();finish('image');
  await assert.rejects(pending,{name:'AbortError'});assert.equal(reads,1);assert.equal(handoffs,0);
});

test('영상 인코딩 취소 후 양도 검토를 시작하지 않는다',async()=>{
  const controller=new AbortController(),input=options(controller.signal);let finish,handoffs=0;
  input.videoData=()=>new Promise(resolve=>{finish=resolve;});input.previewHandoff=async()=>{handoffs++;};
  const pending=prepareAnimatePreview(input);await new Promise(resolve=>setImmediate(resolve));
  controller.abort();finish('mp4');await assert.rejects(pending,{name:'AbortError'});assert.equal(handoffs,0);
});
