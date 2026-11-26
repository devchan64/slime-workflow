import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('백업 접수 결과 오류에 메시지가 없어도 기존 요청 ID 확인을 안내한다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function submitRequest('),end=source.indexOf('  function beginRequest(',start);
  assert.ok(start>=0 && end>start);
  for(const problem of [null,new Error(''),new TypeError('Failed to fetch')]){
    let error='',busy=false,pending='existing';
    const request={command:'backup-verify',payload:{request_id:'same-request'}};
    const context=vm.createContext({requestInFlight:{current:false},setBusy:value=>busy=value,setError:value=>error=value,
      requestErrorMessage,managementCommand:async()=>{throw problem;},validateBackupReceipt:()=>{throw Error('unexpected');},
      setPendingRequest:value=>pending=value,setShownJobId:()=>{},setJobResult:()=>{}});
    vm.runInContext(source.slice(start,end)+'\nthis.submitRequest=submitRequest;',context);
    await context.submitRequest(request);
    assert.match(error,/같은 요청 ID로 다시 확인/);
    if(problem instanceof TypeError)assert.match(error,/연결 상태를 확인/);
    assert.equal(pending,'existing');assert.equal(busy,false);assert.equal(context.requestInFlight.current,false);
  }
});
