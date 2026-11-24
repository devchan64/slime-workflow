import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/WriterActions.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function checkProposalReceipt(id){'),source.indexOf('  useEffect(()=>{\n    if(!proposalScope)return;'));
function fixture(command){
 let timeout,checking=false,state,accepted;const context=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},receiptRequest:{current:null},setReceiptChecking:value=>checking=value,proposalScope:{job:'job'},session:'session',managementCommand:command,validateGpuHandoffStatus:()=>{},setError:()=>{},setProposalReceipt:value=>state=value,onAccepted:value=>accepted=value});
 vm.runInContext(code+'\nthis.checkProposalReceipt=checkProposalReceipt;',context);return {context,timeout:()=>timeout(),checking:()=>checking,state:()=>state,accepted:()=>accepted};
}
test('작가 접수 상태 조회 지연은 시간 초과 후 재확인이 가능하다',async()=>{
 let calls=0;const f=fixture(()=>{calls++;return new Promise(()=>{});}),pending=f.context.checkProposalReceipt('id');await f.context.checkProposalReceipt('id');assert.equal(calls,2);assert.equal(f.checking(),true);
 f.timeout();await assert.rejects(pending,/시간이 초과/);assert.equal(f.checking(),false);assert.equal(f.context.receiptRequest.current,null);
});
test('화면 종료 후 늦은 작가 접수 응답은 선택을 변경하지 않는다',async()=>{
 const callbacks=[];const f=fixture(()=>new Promise(resolve=>callbacks.push(resolve))),pending=f.context.checkProposalReceipt('id'),controller=f.context.receiptRequest.current;
 f.context.receiptRequest.current=null;controller.abort();callbacks[0]({request_id:'id',service:'writer-agent',state:'accepted',job_id:'20261124-123456-abcdef12'});callbacks[1]({state:'not_found'});
 await assert.rejects(pending,{name:'AbortError'});assert.equal(f.state(),undefined);assert.equal(f.accepted(),undefined);
});
test('작가 접수와 양도 기록이 모두 없을 때만 입력을 연다',async()=>{
 const f=fixture(async(_service,command)=>command==='hermes-writer-proposal-receipt'?{request_id:'id',service:'writer-agent',state:'not_found'}:{state:'not_found'});
 await f.context.checkProposalReceipt('id');assert.equal(f.state(),'editing');assert.equal(f.checking(),false);
});
