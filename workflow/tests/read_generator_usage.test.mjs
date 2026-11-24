import test from 'node:test';
import assert from 'node:assert/strict';
import {readGeneratorUsage} from '../../gui/readGeneratorUsage.mjs';

test('사용설명은 대상 경로와 응답 형식을 확인한다',async()=>{
  const controller=new AbortController();let requested;
  const fetcher=async(path,options)=>{requested={path,options};return {ok:true,json:async()=>({content:'설명'})};};
  assert.equal(await readGeneratorUsage('sample/name',controller.signal,fetcher),'설명');
  assert.equal(requested.path,'/management/assistant/usage/sample%2Fname');
  assert.equal(requested.options.signal,controller.signal);
  await assert.rejects(readGeneratorUsage('sample',controller.signal,async()=>({ok:true,json:async()=>null})),/응답/);
  await assert.rejects(readGeneratorUsage('sample',controller.signal,async()=>({ok:false,status:503})),/503/);
});

test('중단 신호를 무시하는 사용설명 조회도 종료된다',async()=>{
  const controller=new AbortController();let finish;
  const read=readGeneratorUsage('sample',controller.signal,()=>new Promise(resolve=>{finish=resolve;}));
  controller.abort();await assert.rejects(read,{name:'AbortError'});
  finish({ok:true,json:async()=>({content:'늦은 설명'})});
});
