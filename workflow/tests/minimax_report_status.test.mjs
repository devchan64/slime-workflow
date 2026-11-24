import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const requireGui=createRequire(new URL('../../gui/package.json',import.meta.url));
const esbuild=requireGui('esbuild'),React=requireGui('react'),{renderToStaticMarkup}=requireGui('react-dom/server');
const source=fileURLToPath(new URL('../../gui/useMinimaxReportReceipt.jsx',import.meta.url));
const bundle=esbuild.buildSync({entryPoints:[source],bundle:true,write:false,platform:'node',format:'cjs',external:['react']});
const moduleRecord={exports:{}};
new Function('require','module','exports',bundle.outputFiles[0].text)(requireGui,moduleRecord,moduleRecord.exports);
const {MinimaxReportStatus,minimaxReceiptText}=moduleRecord.exports;

function render(receipt){return renderToStaticMarkup(React.createElement(MinimaxReportStatus,{receipt:{refresh:()=>{},retry:()=>{},retryState:{busy:false,error:''},...receipt}}));}

test('실패와 관찰 불가만 재분석 가능 상태를 표시한다',()=>{
 const failed=render({state:'accepted',job:'2026-11-24_12-00-00-12345678',report:{state:'failed',error:'작성 실패',retry_available:true}});
 assert.match(failed,/보고 실패/);assert.match(failed,/작성 실패/);assert.match(failed,/재분석 가능/);assert.match(failed,/보고서 재분석/);
 const done=render({state:'accepted',job:'2026-11-24_12-00-00-12345678',report:{state:'completed',retry_available:false}});
 assert.match(done,/대화에 보고 완료/);assert.doesNotMatch(done,/보고서 재분석/);
 assert.match(minimaxReceiptText({state:'unknown'}),/접수 여부를 확인/);
});

test('생성 실패와 취소를 보고서 작성 실패와 구분한다',()=>{
 for(const [generation_state,label] of [['failed','생성 실패'],['cancelled','생성 취소']]){
  const text=minimaxReceiptText({state:'accepted',job:'job',report:{state:'failed',generation_state}});
  assert.match(text,new RegExp(label));assert.doesNotMatch(text,/보고 실패/);
  assert.match(minimaxReceiptText({state:'accepted',job:'job',report:{state:'waiting',generation_state}}),new RegExp(label));
 }
});

test('접수된 작업의 보고 기록을 찾지 못하면 접수 ID와 확인 필요 사유를 표시한다',()=>{
 const text=minimaxReceiptText({state:'accepted',job:'2026-11-24_12-00-00-12345678',report:{state:'unknown',last_error:'보고서 기록을 확인할 수 없습니다.'}});
 assert.match(text,/접수된 작업 2026-11-24_12-00-00-12345678/);
 assert.match(text,/보고 상태 확인 중/);assert.match(text,/보고서 기록을 확인할 수 없습니다/);
});

test('재분석 요청 중에는 중복 버튼을 비활성화하고 오류를 표시한다',()=>{
 const html=render({state:'accepted',job:'2026-11-24_12-00-00-12345678',report:{state:'failed',retry_available:true},retryState:{busy:true,error:'상태 확인 필요'}});
 assert.match(html,/재분석 요청 중/);assert.match(html,/disabled=""/);assert.match(html,/상태 확인 필요/);
});

test('재분석은 조회한 리비전으로 한 번만 요청하고 완료 후 상태를 새로 읽는다',async()=>{
 const {readFileSync}=await import('node:fs');const vm=await import('node:vm');
 const {untilAborted}=await import('../../gui/managementCommand.js');
 const text=readFileSync(source,'utf8');const code=text.slice(text.indexOf('  const retry=useCallback'),text.indexOf('  return {...current'));
 let resolve,calls=0,refreshes=0,sent=null,state;
 const context=vm.createContext({useCallback:fn=>fn,session:'a'.repeat(32),job:'2026-11-24_10-00-00-12345678',service:'minimax-h3-image',current:{id:'flux_'+'b'.repeat(64),report:{retry_available:true,retry_revision:2}},generation:{current:1},retryBusy:{current:false},retryController:{current:null},AbortController,untilAborted,setRetryState:value=>state=value,refresh:()=>refreshes++,setTimeout:()=>1,clearTimeout:()=>{},managementCommand:(_service,_command,payload)=>{calls++;sent=payload;return new Promise(done=>resolve=done);}});
 vm.runInContext(code+'\nthis.trigger=retry;',context);const first=context.trigger();await context.trigger();
 assert.equal(calls,1);assert.equal(sent.expected_revision,2);assert.equal(sent.service,'minimax-h3-image');assert.equal(state.busy,true);
 resolve({state:'waiting',retry_revision:3});await first;
 assert.equal(refreshes,1);assert.equal(state.busy,false);assert.equal(context.retryBusy.current,false);
});

test('재분석 응답이 불확실하면 다시 보내지 않고 상태 조회를 유도한다',async()=>{
 const {readFileSync}=await import('node:fs');const vm=await import('node:vm');
 const {untilAborted}=await import('../../gui/managementCommand.js');
 const text=readFileSync(source,'utf8');const code=text.slice(text.indexOf('  const retry=useCallback'),text.indexOf('  return {...current'));
 let calls=0,refreshes=0,state;
 const context=vm.createContext({useCallback:fn=>fn,session:'a'.repeat(32),job:'2026-11-24_10-00-00-12345678',service:'minimax-h3-image',current:{id:'flux_'+'b'.repeat(64),report:{retry_available:true,retry_revision:0}},generation:{current:1},retryBusy:{current:false},retryController:{current:null},AbortController,untilAborted,setRetryState:value=>state=value,refresh:()=>refreshes++,setTimeout:()=>1,clearTimeout:()=>{},managementCommand:async()=>{calls++;throw new Error('연결 실패');}});
 vm.runInContext(code+'\nthis.trigger=retry;',context);await context.trigger();
 assert.equal(calls,1);assert.equal(refreshes,1);assert.match(state.error,/상태를 다시 확인/);assert.equal(context.retryBusy.current,false);
});

test('보고서 작성 대기와 실행 상태를 구분한다',()=>{
 assert.match(minimaxReceiptText({state:'accepted',job:'job',report:{state:'writing',writer_status:'queued'}}),/보고서 작성 대기/);
 assert.match(minimaxReceiptText({state:'accepted',job:'job',report:{state:'writing',writer_status:'running'}}),/보고서 작성 중/);
 assert.match(minimaxReceiptText({state:'accepted',job:'job',report:{state:'writing',writer_status:'unknown'}}),/상태 확인 중/);
});

test('일시적인 상태 조회 실패 뒤 재조회하여 보고 상태를 복구한다',async()=>{
 const {readFileSync}=await import('node:fs');const vm=await import('node:vm');
 const {untilAborted}=await import('../../gui/managementCommand.js');
 const text=readFileSync(source,'utf8');const code=text.slice(text.indexOf('  useEffect(()=>{'),text.indexOf('  const refresh='));
 const timers=new Map();let nextTimer=0,calls=0,current,cleanup;
 const id='flux_'+'b'.repeat(64),service='minimax-h3-image';
 const context=vm.createContext({useEffect:fn=>cleanup=fn(),generation:{current:0},previousScope:{current:'scope'},scopeKey:'scope',revision:0,session:'a'.repeat(32),job:'2026-11-24_10-00-00-12345678',service,retryBusy:{current:false},retryController:{current:null},setRetryState:()=>{},setValue:value=>current=value,AbortController,untilAborted,fluxProposalRequestId:async()=>id,managementCommand:async()=>{calls++;if(calls===1)throw new Error('연결 실패');return {receipt:{request_id:id,service,state:'accepted',job_id:'2026-11-24_12-00-00-12345678'},report:{state:'completed'}};},setTimeout:(fn,ms)=>{const key=++nextTimer;timers.set(key,{fn,ms});return key;},clearTimeout:key=>timers.delete(key)});
 vm.runInContext(code,context);await new Promise(setImmediate);assert.equal(current.state,'unknown');
 const retry=[...timers.values()].find(timer=>timer.ms===5000);assert.ok(retry);retry.fn();await new Promise(setImmediate);
 assert.equal(calls,2);assert.equal(current.state,'accepted');assert.equal(current.report.state,'completed');cleanup();
});
