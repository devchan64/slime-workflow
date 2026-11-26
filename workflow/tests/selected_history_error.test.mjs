import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('이력 삭제 전 조회와 삭제 요청 오류의 불확실성을 구분한다',async()=>{
  const source=readFileSync(new URL('../../gui/SelectedHistoryDeletion.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function remove(){'),end=source.indexOf('  return <section',start);
  assert.ok(start>=0 && end>start);
  for(const dispatched of [false,true])for(const network of [false,true]){
    let error='',state='completed',review=true,ack=true,busy=false,calls=0;
    const context=vm.createContext({AbortController,requestErrorMessage,setTimeout,clearTimeout,terminalStates:new Set(['completed']),
      review,ack,state,busy,service:'fixture',id:'fixture',mounted:{current:true},
      readState:async()=>{if(!dispatched)throw network ? new TypeError('Failed to fetch') : null;return 'completed';},managementCommand:async()=>{calls++;throw network ? new TypeError('Failed to fetch') : null;},
      setState:value=>state=value,setError:value=>error=value,setReview:value=>review=value,setAck:value=>ack=value,setBusy:value=>busy=value});
    vm.runInContext(source.slice(start,end)+'\nthis.remove=remove;',context);await context.remove();
    if(network)assert.match(error,/연결 상태를 확인/);
    assert.match(error,dispatched ? /삭제 결과가 불확실/ : /삭제 요청은 전송하지 않았습니다/);
    assert.equal(calls,dispatched?1:0);assert.equal(state,null);assert.equal(review,false);assert.equal(ack,false);assert.equal(busy,false);
  }
});
