import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function saveForm('),source.indexOf('  useEffect(()=>{\n    const controller=new AbortController();',source.indexOf('  async function submit(){')));
function fixture(){
 let resolveSave,calls=[],saved=0,updates=0;
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,crypto:{randomUUID:()=> '12345678-1234-1234-1234-123456789abc'},requestRef:{current:{}},videoInfo:null,saveAttempt:{current:null},saveRequest:{current:null},session:'s',pending:{frames:21,steps:4,seed:1,flow_shift:5,guidance_scale:1,switch_ratio:.5},sending:{current:false},modelReason:'',embedded:true,handoffReview:null,mounted:{current:true},reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},attachmentProcessing:{current:false},setBusy:()=>updates++,setError:()=>updates++,setNotice:()=>updates++,setJob:()=>updates++,setPending:()=>updates++,setHandoffReview:()=>updates++,onSaved:()=>saved++,managementCommand:(_service,command)=>{calls.push(command);return command==='hermes-video-form-save'?new Promise(done=>resolveSave=done):Promise.resolve({state:'accepted',job_id:'job'});}});
 vm.runInContext(code+'\nthis.submit=submit;this.saveDraft=saveDraft;',context);return {context,finish:()=>resolveSave({}),calls,saved:()=>saved,updates:()=>updates};
}
test('Fun Control 폼 저장 중 화면 종료는 늦은 응답으로 생성을 접수하지 않는다',async()=>{
 const f=fixture(),pending=f.context.submit();f.context.mounted.current=false;const before=f.updates();f.finish();await pending;
 assert.deepEqual(f.calls,['hermes-video-form-save']);assert.equal(f.saved(),0);assert.equal(f.updates(),before);
});
test('Fun Control 폼 저장 후 접수 성공은 완료를 한 번 알린다',async()=>{
 const f=fixture(),pending=f.context.submit();f.finish();await pending;
 assert.deepEqual(f.calls,['hermes-video-form-save','hermes-video-form-submit']);assert.equal(f.saved(),1);
});
test('Fun Control 폼 저장 후 접수 실패도 저장 사실을 한 번 갱신한다',async()=>{
 const f=fixture();let finish;f.context.managementCommand=(_service,command)=>{f.calls.push(command);return command==='hermes-video-form-save'?new Promise(done=>finish=done):Promise.reject(new Error('응답 실패'));};
 const pending=f.context.submit();finish({});await pending;assert.deepEqual(f.calls,['hermes-video-form-save','hermes-video-form-submit']);assert.equal(f.saved(),1);
});
test('Fun Control 폼 저장은 중복을 막고 시간 초과 후 이력 확인을 안내한다',async()=>{
 const f=fixture();let timer,error='';f.context.setTimeout=fn=>(timer=fn,1);f.context.clearTimeout=()=>{};f.context.setError=value=>error=value;
 const pending=f.context.saveDraft();await f.context.saveDraft();assert.deepEqual(f.calls,['hermes-video-form-save']);timer();await pending;
 assert.match(error,/저장 여부를 확인/);assert.equal(f.context.sending.current,false);assert.ok(f.context.saveAttempt.current.id);assert.equal(f.saved(),0);
});
