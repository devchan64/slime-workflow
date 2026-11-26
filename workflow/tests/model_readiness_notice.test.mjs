import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('SHA 검증 중에는 다운로드를 보류하고 완료 상태를 자동으로 다시 확인한다',()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('export function modelPrepareReason'),source.indexOf('export function ModelDownloadButton')).replaceAll('export function','function');
 const context=vm.createContext({});vm.runInContext(code,context);
 const status={ready:false,message:'검증 중',can_prepare:false,verification_status:'verifying'};
 assert.match(context.modelPrepareReason(status,'',false),/SHA-256 검증이 진행 중/);
 assert.equal(context.modelReadinessPollDelay(status,false),5000);
 assert.equal(context.validModelReadiness(status),true);
 assert.equal(context.validModelReadiness({...status,verification_status:'unexpected'}),false);
 assert.equal(context.modelReadinessPollDelay({...status,verification_status:'verified'},false),null);
});

test('I2V 파일 검증 상태와 생성 준비 상태를 구분한다',()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('export function modelReadinessText'),source.indexOf('export function ModelReadinessMessage')).replace('export function','function');
 const context=vm.createContext({});vm.runInContext(code,context);
 const status={ready:false,generation_ready:false,verification_status:'verifying',message:'SHA-256 검증 중'};
 assert.match(context.modelReadinessText('wan22-i2v-assets',status,''),/^모델 파일 검증 중/);
 const complete={...status,ready:true,verification_status:'verified',message:'SHA-256 검증 완료 · 생성기와 GPU는 별도'};
 assert.match(context.modelReadinessText('wan22-i2v-assets',complete,''),/^모델 파일 준비 완료/);
 assert.match(context.modelReadinessText('other',complete,''),/^모델 준비 필요/);
});

test('모델 준비 응답 실패는 불확실성을 알리고 성공은 정상 상태로 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 for(const failure of [true,false]){
  let notice='',isError=true,sending=false;
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},sectionRef:{current:null},preparing:{current:false},poller:{current:null},readiness:{current:{status:{prepare_request:{service:'service',command:'prepare',payload:{}}},error:'',checking:false}},modelPrepareReason:()=>'',setTimeout:()=>1,clearTimeout:()=>{},setNotice:value=>notice=value,setNoticeError:value=>isError=value,setSending:value=>sending=value,setStatus:()=>{},setChecking:()=>{},setRevision:()=>{},requestErrorMessage:error=>error.message,managementCommand:async()=>{if(failure)throw Error('연결 오류');return {};}});
  vm.runInContext(code,context);await context.prepare();assert.equal(sending,false);assert.equal(context.preparing.current,false);assert.equal(isError,failure);
  assert.match(notice,failure?/접수 결과를 확인하지 못했습니다/:/준비 요청을 보냈습니다/);
 }
});

test('모델 준비가 제한된 동안 접수 함수를 직접 호출해도 요청하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 const reason=source.slice(source.indexOf('export function modelPrepareReason'),source.indexOf('export function modelReadinessPollDelay')).replace('export function','function');
 let calls=0;const context=vm.createContext({preparing:{current:false},readiness:{current:{status:null,error:'조회 실패',checking:false}},managementCommand:()=>calls++});
 vm.runInContext(reason+code,context);await context.prepare();assert.equal(calls,0);assert.equal(context.preparing.current,false);
});

test('모델 상태 조회 시작은 렌더 전에 중복 조회와 준비 접수를 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 const reason=source.slice(source.indexOf('export function modelPrepareReason'),source.indexOf('export function modelReadinessPollDelay')).replace('export function','function');
 let queries=0,calls=0;const readiness={current:{status:{ready:false,prepare_request:{}},error:'',checking:false}};
 const context=vm.createContext({preparing:{current:false},readiness,setChecking:()=>{},setRevision:()=>queries++,managementCommand:()=>calls++});
 vm.runInContext(reason+code,context);context.refreshReadiness();context.refreshReadiness();await context.prepare();assert.equal(queries,1);assert.equal(calls,0);assert.equal(readiness.current.checking,true);
});

test('자동 모델 상태 조회 시작은 렌더 전 준비 제한에 반영된다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(preparing.current)return;'),source.indexOf('  async function prepare()'));
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 const reason=source.slice(source.indexOf('export function modelPrepareReason'),source.indexOf('export function modelReadinessPollDelay')).replace('export function','function');
 let options,calls=0,parent=null;const readiness={current:{status:null,error:'',checking:true}};
 const context=vm.createContext({readiness,preparing:{current:false},poller:{current:null},manage:true,service:'service',revision:0,onStatus:value=>parent=value,onError:null,useEffect:fn=>fn(),setError:()=>{},setStatus:()=>{},setChecking:()=>{},setCheckedAt:()=>{},validModelReadiness:()=>true,modelReadinessPollDelay:()=>null,startModelReadinessPoller:value=>options=value,managementCommand:()=>calls++});
 vm.runInContext(reason+effect+code,context);options.onSuccess({ready:false,prepare_request:{service:'service',command:'prepare',payload:{}}});options.onFinish();assert.equal(parent.ready,false);options.onStart();await context.prepare();assert.equal(parent,null);assert.equal(calls,0);assert.equal(readiness.current.checking,true);
});

test('재조회 시작 시 표시된 상태는 유지하면서 상위 생성 상태를 잠근다',()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(preparing.current)return;'),source.indexOf('  async function prepare()'));
 let displayed={ready:true},parent={ready:true};const readiness={current:{status:displayed,error:'',checking:false}};
 const context=vm.createContext({preparing:{current:false},readiness,poller:{current:null},manage:true,service:'service',revision:1,onStatus:value=>parent=value,onError:()=>{},useEffect:fn=>fn(),setError:()=>{},setStatus:value=>displayed=value,setChecking:()=>{},setCheckedAt:()=>{},validModelReadiness:()=>true,modelReadinessPollDelay:()=>null,startModelReadinessPoller:options=>{options.onStart();return ()=>{};}});
 vm.runInContext(effect,context);assert.deepEqual(displayed,{ready:true});assert.equal(parent,null);assert.equal(readiness.current.status,null);assert.equal(readiness.current.checking,true);
});

test('모델 상태 재조회 실패 시 관측을 보존하지만 상위와 준비 접수는 잠근다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(preparing.current)return;'),source.indexOf('  async function prepare()'));
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 const reason=source.slice(source.indexOf('export function modelPrepareReason'),source.indexOf('export function modelReadinessPollDelay')).replace('export function','function');
 let options,displayed={ready:false,prepare_request:{}},parent=displayed,error='',calls=0;const readiness={current:{status:displayed,error:'',checking:false}};
 const context=vm.createContext({preparing:{current:false},readiness,poller:{current:null},manage:true,service:'service',revision:1,onStatus:value=>parent=value,onError:()=>{},useEffect:fn=>fn(),setError:value=>error=value,setStatus:value=>displayed=value,setChecking:()=>{},setCheckedAt:()=>{},validModelReadiness:()=>true,modelReadinessPollDelay:()=>null,startModelReadinessPoller:value=>{options=value;return ()=>{};},requestErrorMessage:e=>e.message,managementCommand:()=>calls++});
 vm.runInContext(reason+effect+code,context);options.onFailure(Error('조회 실패'),false);options.onFinish();await context.prepare();assert.equal(displayed.ready,false);assert.equal(parent,null);assert.equal(error,'조회 실패');assert.equal(calls,0);
});

test('모델 준비 접수 중 상위 속성이 바뀌어도 자동 조회를 재시작하지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(preparing.current)return;'),source.indexOf('  async function prepare()'));
 let starts=0;const preparing={current:true};
 const context=vm.createContext({preparing,readiness:{current:{}},poller:{current:null},manage:true,service:'service',revision:0,onStatus:null,onError:null,useEffect:fn=>fn(),setError:()=>{},setStatus:()=>{},validModelReadiness:()=>true,modelReadinessPollDelay:()=>null,startModelReadinessPoller:()=>{starts++;return ()=>{};}});
 vm.runInContext(effect,context);assert.equal(starts,0);
 preparing.current=false;vm.runInContext(effect,context);assert.equal(starts,1);
});

test('모델 준비 접수 중 이전 상태 조회를 정리하고 수동 조회를 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/ModelReadiness.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function prepare()'),source.indexOf('  const prepareReason='));
 let finish,stopped=0,refreshes=0,checking=false;const readiness={current:{status:{ready:false,prepare_request:{service:'service',command:'prepare',payload:{}}},error:'',checking:false}},preparing={current:false};
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},sectionRef:{current:null},preparing,poller:{current:()=>stopped++},readiness,modelPrepareReason:()=>'',setTimeout:()=>1,clearTimeout:()=>{},setNotice:()=>{},setNoticeError:()=>{},setSending:()=>{},setStatus:()=>{},setChecking:value=>checking=value,setRevision:()=>{assert.equal(preparing.current,false);assert.equal(checking,true);refreshes++;},managementCommand:()=>new Promise(resolve=>finish=resolve)});
 vm.runInContext(code,context);const pending=context.prepare();context.refreshReadiness();assert.equal(stopped,1);assert.equal(refreshes,0);assert.equal(context.poller.current,null);
 finish({});await pending;assert.equal(refreshes,1);assert.equal(readiness.current.status,null);assert.equal(readiness.current.checking,true);
});
