import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validWorkflowView} from '../../gui/workflowViewValidation.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('워크플로우 결과의 실행과 필수 목록 형식을 확인한다',()=>{
 const valid={run_id:'run',steps:[{step_id:'image',state:'completed'}],results:[{step_id:'image',job_id:'job',attempt_id:'attempt',outputs:{preview:'path'}}],choices:[],retries:[]};
 assert.equal(validWorkflowView(valid,'run'),true);
 assert.equal(validWorkflowView(valid,'other'),false);
 for(const damaged of [{...valid,steps:[null]},{...valid,steps:[{step_id:'image'}]},
  {...valid,steps:[{step_id:'image',state:'ready',bindings:{images:null}}]},
  {...valid,steps:[{step_id:'image',state:'blocked',block_reason:{}}]},
  {...valid,results:[{step_id:'image',job_id:'job',attempt_id:'attempt',outputs:null}]},{...valid,choices:null},{...valid,retries:[null]},
  {...valid,choices:[{step_id:{},input_field:'x',source_request:'r',digest:'d',selected:0}]},
  {...valid,retries:[{step_id:'x',source_request:'r',source_run:'a',retry_run:null}]}])
  assert.equal(validWorkflowView(damaged,'run'),false);
});

test('결과 연결과 취소의 손상 응답은 화면 결과를 덮어쓰지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 for(const [start,end,name] of [['  async function select(choice)', '  async function retry(step)', 'select'],['  async function cancelRun()', '  return <section', 'cancelRun']]){
  const code=source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
  let updates=0,error='',busy=false;
  const context=vm.createContext({validWorkflowView,session:'s',run:'r',mutationPending:{current:false},viewPending:{current:false},requiresRefresh:{current:false},call:async()=>({run_id:'r',choices:null}),workflowMutation:(call,...args)=>call(...args),setView:()=>updates++,cancelSubmittedFocus:{current:false},cancelReviewRef:{current:null},document:{activeElement:null},
   setBusy:value=>busy=value,setError:value=>error=value,setConfirmCancel:()=>{},setConnectionNotice:()=>{}});
  vm.runInContext(code,context);await context[name]({step_id:'step',input_field:'image',source_request:'request',digest:'digest'});
  assert.equal(updates,0);assert.equal(busy,false);assert.match(error,/확인할 수 없습니다/);
 }
});

test('결과 연결·재시도·취소는 처리 중 중복 요청을 보내지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 for(const [start,end,name] of [['  async function select(choice)','  async function retry(step)','select'],['  async function retry(step)','  const activeSteps','retry'],['  async function cancelRun()','  return <section','cancelRun']]){
  const code=source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
  let calls=0,resolve;
  const context=vm.createContext({mutationPending:{current:false},viewPending:{current:false},requiresRefresh:{current:false},session:'s',run:'r',call:()=>{},workflowMutation:()=>{calls++;return new Promise(done=>resolve=done);},
   validWorkflowView:()=>false,setBusy:()=>{},setError:()=>{},setView:()=>{},setConnectionNotice:()=>{},setConfirmCancel:()=>{},
   cancelSubmittedFocus:{current:false},cancelReviewRef:{current:null},document:{activeElement:null}});
  vm.runInContext(code,context);context.viewPending.current=true;await context[name]({});assert.equal(calls,0);context.viewPending.current=false;
  const first=context[name]({step_id:'step',request_id:'request'});await context[name]({});
  assert.equal(calls,1);resolve({run_id:'r',retries:[]});await first;assert.equal(context.mutationPending.current,false);
  assert.equal(context.requiresRefresh.current,true);await context[name]({});assert.equal(calls,1);
 }
});

test('출력 메타데이터가 없어도 미리보기 경로가 바뀌면 상태를 분리한다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const expression=source.match(/<MediaPreview key=\{(JSON\.stringify\(\[.*?\]\))\}/)[1];
 const key=preview=>vm.runInNewContext(expression,{result:{job_id:'job',output_metadata:null,outputs:{preview}}});
 assert.notEqual(key('/old.png'),key('/new.png'));
});
