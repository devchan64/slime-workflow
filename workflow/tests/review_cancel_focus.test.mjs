import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('생성 검토 취소는 사라진 초점만 복구하고 사용자가 옮긴 초점은 유지한다',()=>{
 for(const file of ['VacePage.jsx','KimodoGeneration.jsx','FluxImagePage.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const start=source.indexOf('onCancel={()=>{const restore=');
  const end=source.indexOf('}} onConfirm=',start);
  assert.ok(start>=0 && end>start,file);
  const code=source.slice(start+'onCancel={'.length,end+1);
  for(const moved of [false,true]){
   let frame,focused=0;const body={},button={},other={},document={body,activeElement:button};
   const target={isConnected:true,disabled:false,focus:()=>focused++};
   const review={current:{contains:element=>element===button}};
   const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,requestAnimationFrame:fn=>frame=fn,reviewRef:review,reviewSectionRef:review,formRef:{current:{querySelector:()=>target}},inputFormRef:{current:target},textRef:{current:target},reviewButtonRef:{current:target},setPending:()=>{},setReview:()=>{},setHandoffReview:()=>{},handoff:{clearReview:()=>{}}});
   vm.runInContext('('+code+')()',context);document.activeElement=moved?other:body;frame();
   assert.equal(focused,moved?0:1,file);
  }
 }
});

test('Fun Control과 번역 검토 취소는 초점 이동과 새 검토를 존중한다',()=>{
 for(const file of ['FunControlPage.jsx','TranslationPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const start=source.indexOf('  function cancelReview()'),end=source.indexOf('\n  }',start);
  const code=file==='FunControlPage.jsx' ? source.slice(start,source.indexOf('\n',start)) : source.slice(start,end+4);
  assert.ok(start>=0 && code.includes('restoreLostFocus'),file);
  for(const scenario of ['lost','moved','new-review']){
   let frame,focused=0;const body={},button={},other={},document={body,activeElement:button},epoch={current:1};
   const target={isConnected:true,disabled:false,matches:()=>false,focus:()=>focused++};
   const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:node=>node===button}},reviewEpoch:epoch,reviewRequest:{current:null},restoreFrame:{current:null},formRef:{current:{querySelector:()=>target}},textRef:{current:target},setPending:()=>{},setHandoffReview:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
   vm.runInContext(code,context);context.cancelReview();document.activeElement=scenario==='moved'?other:body;if(scenario==='new-review')epoch.current++;frame?.();
   assert.equal(focused,scenario==='lost'?1:0,`${file} ${scenario}`);
  }
 }
});

test('MiniMax 이미지 검토 취소는 초점을 잃었을 때만 프롬프트로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  useEffect(()=>{if(embedded)return;',source.indexOf('  function closeReview()')));
 for(const moved of [false,true]){
  let frame,focused=0;const body={},button={},other={},document={body,activeElement:button};
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:node=>node===button}},promptRef:{current:{isConnected:true,focus:()=>focused++}},setPending:()=>{},setPreview:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(code,context);context.closeReview();document.activeElement=moved?other:body;frame();assert.equal(focused,moved?0:1);
 }
});

test('웨이포인트 검토 취소는 버튼에서 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('onClick={event=>{const restore=document.activeElement===event.currentTarget;setPending(null);');
 const end=source.indexOf('}}>취소</button>',start);
 assert.ok(start>=0 && end>start);
 const code=source.slice(start+'onClick={'.length,end+1);
 for(const scenario of ['lost','moved','pointer']){
  let frame,focused=0;const body={},button={},other={},document={body,activeElement:scenario==='pointer'?other:button};
  const target={isConnected:true,disabled:false,focus:()=>focused++};
  const context=vm.createContext({document,button,restoreLostFocus,details:{current:{open:true}},reviewButton:{current:target},setPending:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext('('+code+')({currentTarget:button})',context);
  document.activeElement=scenario==='lost'?body:other;frame?.();
  assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});

test('음악·효과음 검토 취소는 사라진 초점만 해당 입력으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  async function readJob('));
 for(const preparing of [false,true])for(const scenario of ['lost','moved','outside']){
  let frame,focused='';const body={},button={},other={},document={body,activeElement:scenario==='outside'?other:button};
  const target=name=>({isConnected:true,focus:()=>focused=name});
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,review:{payload:{action:preparing?'prepare':'generate'}},reviewRef:{current:{contains:node=>node===button}},reviewEpoch:{current:0},reviewRequest:{current:null},restoreFrame:{current:null},cancelAnimationFrame:()=>{},prepareRef:{current:target('prepare')},prepareDetails:{current:{open:true}},prepareSummary:{current:target('summary')},promptRef:{current:target('prompt')},confirmation:{current:{cancel:()=>{}}},setReview:()=>{},handoff:{clearReview:()=>{}},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext(code,context);context.closeReview();document.activeElement=scenario==='lost'?body:other;frame?.();
  assert.equal(focused,scenario==='lost'?(preparing?'prepare':'prompt'):'',`${preparing} ${scenario}`);
 }
});

test('접힌 모델 준비 영역의 검토를 취소하면 제목으로 초점을 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  async function readJob('));
 let frame,focused='';const body={},button={},document={body,activeElement:button};
 const target=name=>({isConnected:true,focus:()=>focused=name});
 const summary=target('summary'),prepare=target('button');prepare.parentElement={tagName:'DETAILS',open:false,querySelector:()=>summary};
 const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,review:{payload:{action:'prepare'}},reviewRef:{current:{contains:node=>node===button}},reviewEpoch:{current:0},reviewRequest:{current:null},restoreFrame:{current:null},cancelAnimationFrame:()=>{},prepareDetails:{current:{open:false}},prepareRef:{current:prepare},prepareSummary:{current:summary},promptRef:{current:target('prompt')},confirmation:{current:{cancel:()=>{}}},setReview:()=>{},handoff:{clearReview:()=>{}},requestAnimationFrame:fn=>(frame=fn,1)});
 vm.runInContext(code,context);context.closeReview();document.activeElement=body;frame();assert.equal(focused,'summary');
});

test('오디오 검토 취소 직후 새 검토가 시작되면 이전 초점 복구를 건너뛴다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  async function readJob('));
 let frame,focused=0;const body={},button={},document={body,activeElement:button},reviewEpoch={current:0};
 const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,review:{payload:{action:'generate'}},reviewRef:{current:{contains:node=>node===button}},reviewEpoch,reviewRequest:{current:null},restoreFrame:{current:null},cancelAnimationFrame:()=>{},promptRef:{current:{isConnected:true,focus:()=>focused++}},confirmation:{current:{cancel:()=>{}}},setReview:()=>{},handoff:{clearReview:()=>{}},requestAnimationFrame:fn=>(frame=fn,1)});
 vm.runInContext(code,context);context.closeReview();reviewEpoch.current++;document.activeElement=body;frame();assert.equal(focused,0);
});
