import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
const source=readFileSync(new URL('../../gui/WorldMap.jsx',import.meta.url),'utf8');
const start=source.indexOf('  useEffect(()=>{\n    document.title="월드맵 검수";'),end=source.indexOf('  },[revision]);',start)+'  },[revision]);'.length,effect=source.slice(start,end);
test('월드맵 요청과 본문 지연은 시간 초과 뒤 늦은 응답을 적용하지 않는다',async()=>{
 for(const stage of ['fetch','json']){
  let stop,timer,finish,error='',loading=false,updates=0,jsonCalls=0;
  const deferred=new Promise(done=>finish=done),c=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{title:''},revision:0,useEffect:fn=>stop=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setMaps:()=>updates++,setImageRevision:()=>updates++,setLoaded:()=>updates++,setCheckedAt:()=>updates++,validWorldMap:()=>true,viewport:{current:null},reloadPending:{current:false},restoreMapFocus:{current:false},restoreReloadFocus:{current:false},fetch:()=>stage==='fetch'?deferred:Promise.resolve({ok:true,json:()=>{jsonCalls++;return deferred;}})});
  vm.runInContext(effect,c);for(let i=0;i<10 && stage==='json' && !jsonCalls;i++)await Promise.resolve();timer();await new Promise(done=>setImmediate(done));assert.match(error,/시간이 초과/);assert.equal(loading,false);
  finish(stage==='fetch'?{ok:true,json:()=>{jsonCalls++;return Promise.resolve({maps:[]});}}:{maps:[]});await new Promise(done=>setImmediate(done));assert.equal(updates,0);if(stage==='fetch')assert.equal(jsonCalls,0);stop();
 }
});
test('월드맵 초기 선택은 재조회 순서 변경이나 조회 중 사용자 선택으로 덮이지 않는다',async()=>{
 let stop,resolve,id=null,maps=[],data={maps:[{id:'first'},{id:'second'}]};
 const c=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{title:'',activeElement:{}},revision:0,useEffect:fn=>stop=fn(),setTimeout,clearTimeout,setLoading:()=>{},setError:()=>{},setMaps:value=>maps=value,setId:fn=>id=fn(id),setImageRevision:()=>{},setLoaded:()=>{},setCheckedAt:()=>{},validWorldMap:()=>true,viewport:{current:null},reloadPending:{current:false},restoreMapFocus:{current:false},restoreReloadFocus:{current:false},fetch:async()=>({ok:true,json:async()=>data})});
 vm.runInContext(effect,c);await new Promise(done=>setImmediate(done));assert.equal(id,'first');stop();
 data={maps:[{id:'second'},{id:'first'}]};c.revision++;vm.runInContext(effect,c);await new Promise(done=>setImmediate(done));assert.equal(id,'first');assert.equal(maps[0].id,'second');stop();
 c.fetch=()=>new Promise(done=>resolve=done);c.revision++;vm.runInContext(effect,c);id='second';resolve({ok:true,json:async()=>data});await new Promise(done=>setImmediate(done));assert.equal(id,'second');stop();
});
test('월드맵 다시 불러오기는 렌더 전 중복 실행을 막고 처리 상태를 표시한다',()=>{
 const start=source.indexOf('onClick={event=>{if(reloadPending.current)return;'),endHandler=source.indexOf('}}>{loading ? "원본 조회 중',start),handler=source.slice(start+'onClick={'.length,endHandler+1);assert.ok(start>=0 && endHandler>start);
 const button={},document={activeElement:button};let revision=0,loading=false;const c=vm.createContext({document,reloadPending:{current:false},restoreReloadFocus:{current:false},setLoading:value=>loading=value,setRevision:fn=>revision=fn(revision)});
 vm.runInContext('this.reload='+handler+';',c);c.reload({currentTarget:button});c.reload({currentTarget:button});assert.equal(revision,1);assert.equal(loading,true);assert.equal(c.restoreReloadFocus.current,true);
});
