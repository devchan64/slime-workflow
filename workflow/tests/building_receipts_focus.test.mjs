import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/BuildingSessionReceipts.jsx',import.meta.url),'utf8');
test('대화 접수 조회가 메시지 없이 실패해도 이전 결과와 재시도를 안내한다',async()=>{
 const start=source.indexOf('  async function load('),end=source.indexOf('  return <section',start);
 for(const problem of [null,new Error(''),new Error('서비스를 확인할 수 없습니다.')]){
  let error='',busy=true,stale=false;const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,setTimeout,clearTimeout,document:{activeElement:{}},request:{current:null},focus:{current:null},session:'session',page:{offset:0},managementCommand:()=>{},readBuildingSessionReceipts:async()=>{throw problem;},setBusy:value=>busy=value,setError:value=>error=value,setStale:value=>stale=value});
  vm.runInContext(source.slice(start,end)+'\nthis.load=load;',context);await context.load();
  assert.equal((error.match(/다시/g) || []).length,1);assert.match(error,/이전 조회 결과/);assert.equal(stale,true);assert.equal(busy,false);
 }
});
test('대화 에셋 접수 조회 후 잃은 초점만 결과나 재조회로 복구한다',()=>{
  const start=source.indexOf('  useEffect(()=>{if(busy || !focus.current)'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const success of [true,false])for(const moved of [true,false]){
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({document,restoreLostFocus,busy:false,page:{},error:'',focus:{current:{success}},heading:{current:target('heading')},refresh:{current:target('refresh')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.deepEqual(focused,moved?[]:[success?'heading':'refresh']);assert.equal(context.focus.current,null);
  }
});
