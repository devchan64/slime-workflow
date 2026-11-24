import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('작가 변경 요청이 응답하지 않으면 처리 여부 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('async function writerChange'),source.indexOf('export default function WriterResult'));
 let timer,resolve;const context=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const pending=context.writerChange('writer-apply',{});timer();
 await assert.rejects(pending,/처리 여부/);resolve({});
});

test('작가 적용과 정리는 처리 중 중복 요청을 보내지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 for(const [start,end,name] of [['  async function apply()', '  const canDelete=', 'apply'],['  async function trash()', '  return <section', 'trash']]){
  const code=source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
  let calls=0,resolve,kind='';
  const context=vm.createContext({confirmed:true,canApply:true,busy:false,deleteConfirmed:true,canDelete:true,changePending:{current:false},readPending:{current:false},requiresRead:{current:false},id:'job',hash:'hash',document:{activeElement:null},applyButton:{current:{}},deleteButton:{current:{}},restoreRefreshFocus:{current:false},
   setBusy:()=>{},setChangeKind:value=>kind=value,setChecking:()=>{},setConfirmed:()=>{},setDeleteConfirmed:()=>{},setNotice:()=>{},setNoticeError:()=>{},setDetail:()=>{},refresh:()=>{},onDeleted:()=>{},requestErrorMessage:()=>'',
   writerChange:()=>{calls++;return new Promise(done=>resolve=done);}});
  vm.runInContext(code,context);context.readPending.current=true;await context[name]();assert.equal(calls,0);context.readPending.current=false;
  context.requiresRead.current=true;await context[name]();assert.equal(calls,0);context.requiresRead.current=false;
  const first=context[name]();await context[name]();assert.equal(calls,1);assert.equal(kind,name==='apply'?'apply':'delete');
  resolve({id:'job',status:'deleted',recoverable:true});await first;assert.equal(context.changePending.current,false);assert.equal(kind,'');
 }
});

test('작가 적용 완료는 검토한 경로와 일치하는 응답에서만 알린다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function apply()'),source.indexOf('  const canDelete='));
 for(const valid of [true,false]){
  let notice='',noticeError=false;const context=vm.createContext({confirmed:true,canApply:true,busy:false,changePending:{current:false},readPending:{current:false},requiresRead:{current:false},id:'job',hash:'hash',proposal:{changes:[{path:'a.md'}]},document:{activeElement:null},applyButton:{current:{}},restoreRefreshFocus:{current:false},
   setBusy:()=>{},setChangeKind:()=>{},setChecking:()=>{},setConfirmed:()=>{},setNotice:value=>notice=value,setNoticeError:value=>noticeError=value,setDetail:()=>{},refresh:()=>{},requestErrorMessage:problem=>problem.message,
   writerChange:async()=>({status:'applied',requires_learning:true,paths:[valid?'a.md':'b.md']})});
  vm.runInContext(code,context);await context.apply();assert.match(notice,valid?/변경을 적용했습니다/:/결과를 확인/);assert.equal(noticeError,!valid);
 }
});

test('작가 결과 재조회가 끝난 뒤 사라진 초점만 새로고침으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!checking && restoreRefreshFocus\.current\).*?\},\[checking,busy\]\);/)[0];
 for(const moved of [true,false]){
  const body={},other={};let focused=false;
  const context=vm.createContext({useEffect:fn=>fn(),checking:false,busy:false,restoreRefreshFocus:{current:true},document:{body,activeElement:moved?other:body},refreshButton:{current:{disabled:false,focus:()=>focused=true}}});
  vm.runInContext(effect,context);assert.equal(focused,!moved);assert.equal(context.restoreRefreshFocus.current,false);
 }
});

test('작가 변경 또는 조회 중 예약된 자동 갱신은 중복 조회하지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const body=source.match(/useLiveRefresh\(\(\)=>\{(.*?)\},!busy/)[1];
 for(const [change,reading] of [[true,false],[false,true],[false,false]]){
  let checking=false,revision=0;
  const context=vm.createContext({changePending:{current:change},readPending:{current:reading},setChecking:value=>checking=value,refresh:fn=>revision=fn(revision)});
  vm.runInContext(`function tick(){${body}}`,context);context.tick();
  assert.equal(revision,change||reading?0:1);assert.equal(checking,!(change||reading));
 }
});

test('작가 조회 시간 초과 뒤 정상 재조회가 변경 제한을 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true;');
 const marker='  },[id,revision]);',effect=source.slice(start,source.indexOf(marker,start)+marker.length);
 let timer,first=true,error='',checking=false,detail=null;
 const record={id:'job',status:{stage:'review'},proposal:{changes:[]}};
 const context=vm.createContext({AbortController,untilAborted,id:'job',revision:0,useEffect:fn=>fn(),readPending:{current:false},requiresRead:{current:false},followLog:{current:true},
  setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},managementCommand:()=>first?new Promise(()=>{}):Promise.resolve(record),
  setChecking:value=>checking=value,setConfirmed:()=>{},setDeleteConfirmed:()=>{},setDetail:fn=>detail=fn(detail),setCheckedAt:()=>{},setError:value=>error=value,requestErrorMessage:problem=>problem.message,Date});
 vm.runInContext(effect,context);timer();await new Promise(done=>setImmediate(done));
 assert.match(error,/시간이 초과/);assert.equal(checking,false);assert.equal(context.requiresRead.current,true);
 first=false;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(error,'');assert.equal(checking,false);assert.equal(detail.id,'job');assert.equal(context.requiresRead.current,false);
});

test('작가 기록 정리 성공 시 초점 복구 필요 여부를 부모에 전달한다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterResult.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function trash()'),source.indexOf('  return <section'));
 for(const focused of [true,false]){
  const button={},other={};let options;
  const context=vm.createContext({busy:false,canDelete:true,deleteConfirmed:true,changePending:{current:false},readPending:{current:false},requiresRead:{current:false},id:'job',
   deleteButton:{current:button},document:{activeElement:focused?button:other},restoreRefreshFocus:{current:false},setBusy:()=>{},setChangeKind:()=>{},setDeleteConfirmed:()=>{},
   setNotice:()=>{},setNoticeError:()=>{},setDetail:()=>{},setChecking:()=>{},refresh:()=>{},requestErrorMessage:()=>'',onDeleted:(_id,value)=>options=value,
   writerChange:async()=>({id:'job',status:'deleted',recoverable:true})});
  vm.runInContext(code,context);await context.trash();assert.equal(options.restoreFocus,focused);
 }
});

test('작가 기록 정리 후 각 화면은 사라진 초점만 이력 영역으로 돌린다',()=>{
 for(const [file,marker,end,target] of [
  ['WriterPage.jsx','onDeleted={(id,{restoreFocus}={})=>{','}}/></div>','searchButton'],
  ['QueuePanel.jsx','onDeleted={(_id,{restoreFocus}={})=>{','}}/> : <MediaJobResult','listHeading'],
 ])for(const moved of [true,false]){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const begin=source.indexOf(marker)+marker.length,body=source.slice(begin,source.indexOf(end,begin));
  const docBody={},other={};let focused=false,frame;
  const context=vm.createContext({id:'job',restoreFocus:true,document:{body:docBody,activeElement:moved?other:docBody},
   [target]:{current:{focus:()=>focused=true}},requestAnimationFrame:fn=>frame=fn,select:()=>{},setRecent:()=>{},setMatches:()=>{},setNotice:()=>{},setSelectedDirect:()=>{},refresh:()=>{}});
  vm.runInContext(`function done(){${body}}`,context);context.done();frame();assert.equal(focused,!moved);
 }
});
