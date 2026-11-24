import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

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
