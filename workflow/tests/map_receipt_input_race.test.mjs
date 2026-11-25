import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/MapDatabaseReceipt.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function lookup(){'),end=source.indexOf('\n  return <details>',start);assert.ok(start>=0 && end>start);
test('맵 DB 접수 조회 중 입력이 바뀌면 이전 입력의 결과나 오류를 표시하지 않는다',async()=>{
  for(const outcome of ['success','failure']){
    let resolve,reject,notice='',busy=false,calls=0;const deferred=new Promise((yes,no)=>{resolve=yes;reject=no;}),inputRevision={current:0};
    const context=vm.createContext({AbortController,untilAborted,request:{current:null},sequence:{current:0},inputRevision,button:{current:{}},document:{activeElement:{}},restoreFocus:{current:false},requestId:'old',requestHash:'a'.repeat(64),setTimeout,clearTimeout,
      setBusy:value=>busy=value,setNotice:value=>notice=value,setNoticeError:()=>{},managementCommand:()=>{calls++;return deferred;}});
    vm.runInContext(source.slice(start,end)+'\nthis.lookup=lookup;',context);const pending=context.lookup();await context.lookup();assert.equal(calls,1);
    inputRevision.current++;if(outcome==='success')resolve({state:'matched',request_sha256:'a'.repeat(64)});else reject(new Error('실패'));
    await pending;assert.equal(notice,'');assert.equal(busy,false);assert.equal(context.request.current,null);
  }
  assert.equal((source.match(/inputRevision\.current\+\+;set(?:Id|Hash)/g) || []).length,2);
});
test('맵 DB 접수 결과는 상태별 의미를 구분하고 손상된 응답은 성공으로 보지 않는다',async()=>{
  for(const [state,hash,expected] of [['matched','a',/파일 동기화 상태는 별도/],['mismatch','a',/기록이 다릅니다/],['not_found','a',/재접수가 안전하다는 뜻은 아닙니다/],['matched','b',/확인할 수 없습니다/],['unknown','a',/확인할 수 없습니다/]]){
    let notice='',isError=false;const context=vm.createContext({AbortController,untilAborted,request:{current:null},sequence:{current:0},inputRevision:{current:0},button:{current:{}},document:{activeElement:{}},restoreFocus:{current:false},requestId:'id',requestHash:'a'.repeat(64),setTimeout,clearTimeout,
      setBusy:()=>{},setNotice:value=>notice=value,setNoticeError:value=>isError=value,managementCommand:async()=>({state,request_sha256:hash.repeat(64)})});
    vm.runInContext(source.slice(start,end)+'\nthis.lookup=lookup;',context);await context.lookup();assert.match(notice,expected);assert.equal(isError,hash==='b'||state==='unknown');
  }
});
test('콘텐츠 서비스 주소 설정 오류는 입력 오류와 구분해 안내한다',async()=>{
  let notice='',isError=false;const context=vm.createContext({AbortController,untilAborted,request:{current:null},sequence:{current:0},inputRevision:{current:0},button:{current:{}},document:{activeElement:{}},restoreFocus:{current:false},requestId:'id',requestHash:'a'.repeat(64),setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:value=>notice=value,setNoticeError:value=>isError=value,managementCommand:async()=>{throw Error('SLIME_CONTENT_SERVICE_ORIGIN에 콘텐츠 API origin을 지정하세요.');}});
  vm.runInContext(source.slice(start,end)+'\nthis.lookup=lookup;',context);await context.lookup();assert.equal(isError,true);assert.match(notice,/콘텐츠 서비스 주소.*서비스 설정/);assert.doesNotMatch(notice,/SLIME_CONTENT_SERVICE_ORIGIN/);
});
