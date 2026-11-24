import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function readDiff(cursor,event){'),end=source.indexOf('\n  async function inspectJob',start);
assert.ok(start>=0 && end>start);
test('변경 내역 조회 후 잃은 초점만 결과나 조회 버튼으로 복구한다',()=>{
  const begin=source.indexOf('  useEffect(()=>{if(busy || !diffFocus.current)'),end=source.indexOf('\n',begin);assert.ok(begin>=0 && end>begin);
  for(const success of [true,false])for(const moved of [true,false]){
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({document,restoreLostFocus,busy:false,diffPage:{},diffError:'',diffFocus:{current:{success,trigger:target('button')}},diffText:{current:target('text')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(begin,end),context);assert.deepEqual(focused,moved?[]:[success?'text':'button']);
  }
});
test('변경 내역 조회의 지연·전환은 이전 내용을 보존하고 늦은 응답을 버린다',async()=>{
  for(const stop of ['fetch','json','switch']){
    let timer,finish,error='',busy=false,updates=0,calls=0;const delayed=new Promise(resolve=>finish=resolve),diffRequest={current:null};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},diffFocus:{current:null},diffRequest,detail:{id:'job'},diffPage:{text:'이전'},
      setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setDiffError:value=>error=value,setDiffPage:()=>updates++,
      fetch:()=>{calls++;return stop==='fetch'?delayed:Promise.resolve({ok:true,json:()=>delayed});}});
    vm.runInContext(source.slice(start,end)+'\nthis.readDiff=readDiff;',context);
    const pending=context.readDiff(null);await context.readDiff(null);assert.equal(calls,1);
    if(stop!=='fetch')await new Promise(resolve=>setImmediate(resolve));
    if(stop==='switch')diffRequest.current.abort();else timer();await pending;
    if(stop!=='switch'){assert.equal(busy,false);assert.match(error,/이전 조회 내용을 표시/);}else assert.equal(error,'');
    finish(stop==='fetch'?{ok:true,json:async()=>({})}:{text:'늦음',notice:'끝',cursor:{job_id:'job',next_offset:null}});
    await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,0);
  }
});
test('변경 내역 조회는 크기 변경과 되돌아간 위치를 거부한다',async()=>{
  for(const cursorValue of [{job_id:'job',next_offset:10,size_bytes:30},{job_id:'job',next_offset:21,size_bytes:31}]){
    let error='',updates=0;const cursor={job_id:'job',next_offset:10,size_bytes:30};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},diffFocus:{current:null},diffRequest:{current:null},detail:{id:'job'},diffPage:{text:'이전'},setTimeout,clearTimeout,
      setBusy:()=>{},setDiffError:value=>error=value,setDiffPage:()=>updates++,fetch:async()=>({ok:true,json:async()=>({text:'내용',notice:'안내',cursor:cursorValue})})});
    vm.runInContext(source.slice(start,end)+'\nthis.readDiff=readDiff;',context);await context.readDiff(cursor);
    assert.equal(updates,0);assert.match(error,/변경 내역을 확인할 수 없습니다/);
  }
});
