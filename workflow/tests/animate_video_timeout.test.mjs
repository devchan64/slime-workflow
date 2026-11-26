import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {generationReady} from '../../gui/generationReady.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('Animate 저장 입력 조회는 이력의 취소 신호를 전달한다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimatePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('async function readJob('),source.indexOf('export default function AnimatePage'));
 let received;const controller=new AbortController();
 const context=vm.createContext({AbortController,DOMException,untilAborted,setTimeout,clearTimeout,fetch:(_url,{signal})=>{received=signal;return new Promise((resolve,reject)=>{if(signal.aborted)reject(new DOMException('취소','AbortError'));else signal.addEventListener('abort',()=>reject(new DOMException('취소','AbortError')),{once:true});});}});
 vm.runInContext(method+'\nthis.readJob=readJob;',context);
 const pending=context.readJob('job',{signal:controller.signal});controller.abort();
 await assert.rejects(pending,{name:'AbortError'});assert.equal(received.aborted,true);
});

test('Animate 저장 입력 조회는 요청이나 본문 읽기가 멈춰도 시간 초과된다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimatePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('async function readJob('),source.indexOf('export default function AnimatePage'));
 for(const stage of ['request','body']){
  let timeout;const never=new Promise(()=>{});
  const context=vm.createContext({AbortController,DOMException,untilAborted,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},fetch:()=>stage==='request'?never:Promise.resolve({ok:true,json:()=>never})});
  vm.runInContext(method+'\nthis.readJob=readJob;',context);const pending=context.readJob('job');await new Promise(resolve=>setImmediate(resolve));timeout();
  await assert.rejects(pending,/저장된 입력 조회 시간이 초과/);
 }
});

test('열린 검토는 모델 재조회 중 생성 요청을 보내지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimateInputs.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function submit(){');
 const code=source.slice(start,source.indexOf('  return (',start));
 for(const state of [{model:null,loraModel:{ready:true},mode:'none'},{model:{ready:true},loraModel:null,mode:'lightx2v'}]){
  let calls=0;const scope={session:'test'},context=vm.createContext({pending:{lora_mode:state.mode},pendingScope:{current:scope},currentReviewScope:{current:scope},sameScope:(a,b)=>a===b,sending:{current:false},model:state.model,loraModel:state.loraModel,generationReady,managementCommand:()=>calls++});
  vm.runInContext(code,context);await context.submit();assert.equal(calls,0);assert.equal(context.sending.current,false);
 }
});

test('영상 정보의 각 읽기 단계가 중단을 무시해도 시간 초과 후 대기를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimateInputs.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    const source=motionFile || saved?.motion;'),source.indexOf('  useEffect(()=>{if(!checkingVideo'));
 for(const stalled of ['source','blob','info','json']){
  let timeout,error='',checking=[],info=null;
  const never=new Promise(()=>{}),file={size:10};
  const fetcher=url=>url==='/saved.mp4' ? (stalled==='source' ? never : Promise.resolve({ok:true,blob:()=>stalled==='blob'?never:Promise.resolve(file)})) :
   (stalled==='info' ? never : Promise.resolve({ok:true,json:()=>stalled==='json'?never:Promise.resolve({})}));
  const context=vm.createContext({AbortController,untilAborted,fetch:fetcher,motionFile:null,saved:{motion:'/saved.mp4'},videoRevision:0,
   useEffect:fn=>fn(),setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setVideoInfo:value=>info=value,setVideoError:value=>error=value,
   updateVideoChecking:value=>checking.push(value),validAnimateVideoInfo:()=>true});
  vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));timeout();await new Promise(resolve=>setImmediate(resolve));
  assert.match(error,/시간이 초과/);assert.equal(checking.at(-1),false);assert.equal(info,null);
 }
});

test('이전 영상 조회가 취소되면 늦은 응답을 적용하거나 다음 조회를 시작하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimateInputs.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    const source=motionFile || saved?.motion;'),source.indexOf('  useEffect(()=>{if(!checkingVideo'));
 let finish,cleanup,fetchCount=0,info='기존',error='';
 const context=vm.createContext({AbortController,untilAborted,motionFile:null,saved:{motion:'/saved.mp4'},videoRevision:0,
  fetch:()=>{fetchCount++;return new Promise(resolve=>finish=resolve);},useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},
  setVideoInfo:value=>info=value,setVideoError:value=>error=value,updateVideoChecking:()=>{},validAnimateVideoInfo:()=>true});
 vm.runInContext(effect,context);cleanup();finish({ok:true,blob:async()=>({size:10})});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(fetchCount,1);assert.equal(info,null);assert.equal(error,'');
});

test('영상 정보의 비정상 응답은 안내 후 정상 재조회로 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/AnimateInputs.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    const source=motionFile || saved?.motion;'),source.indexOf('  useEffect(()=>{if(!checkingVideo'));
 let error='',info=null,checking=false,attempt=0;
 const expected={width:832,height:480,fps:16,frame_count:93,maximum_frames:81};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,motionFile:{size:10},saved:null,videoRevision:0,
  fetch:async()=>++attempt===1?{ok:false,json:async()=>{throw new SyntaxError('Unexpected token');}}:{ok:true,json:async()=>expected},
  useEffect:fn=>fn(),setTimeout,clearTimeout,setVideoInfo:value=>info=value,setVideoError:value=>error=value,updateVideoChecking:value=>checking=value,validAnimateVideoInfo:value=>value===expected});
 vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));assert.match(error,/영상 정보 응답을 확인할 수 없습니다/);assert.equal(checking,false);assert.equal(info,null);
 vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));assert.equal(error,'');assert.equal(info,expected);assert.equal(checking,false);
});
