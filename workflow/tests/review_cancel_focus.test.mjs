import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('생성 검토 취소는 사라진 초점만 복구하고 사용자가 옮긴 초점은 유지한다',()=>{
 for(const file of ['FunControlPage.jsx','VacePage.jsx','TranslationPage.jsx','KimodoGeneration.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const start=source.indexOf('onCancel={()=>{const restore=');
  const end=source.indexOf('}} onConfirm=',start);
  assert.ok(start>=0 && end>start,file);
  const code=source.slice(start+'onCancel={'.length,end+1);
  for(const moved of [false,true]){
   let frame,focused=0;const body={},button={},other={},document={body,activeElement:button};
   const target={isConnected:true,disabled:false,focus:()=>focused++};
   const review={current:{contains:element=>element===button}};
   const context=vm.createContext({document,restoreLostFocus,requestAnimationFrame:fn=>frame=fn,reviewRef:review,reviewSectionRef:review,formRef:{current:{querySelector:()=>target}},textRef:{current:target},reviewButtonRef:{current:target},setPending:()=>{},setReview:()=>{},setHandoffReview:()=>{},handoff:{clearReview:()=>{}}});
   vm.runInContext('('+code+')()',context);document.activeElement=moved?other:body;frame();
   assert.equal(focused,moved?0:1,file);
  }
 }
});

test('MiniMax 이미지 검토 취소는 초점을 잃었을 때만 프롬프트로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  async function submit()'));
 for(const moved of [false,true]){
  let frame,focused=0;const body={},button={},other={},document={body,activeElement:button};
  const context=vm.createContext({document,restoreLostFocus,reviewRef:{current:{contains:node=>node===button}},promptRef:{current:{isConnected:true,focus:()=>focused++}},setPending:()=>{},setPreview:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(code,context);context.closeReview();document.activeElement=moved?other:body;frame();assert.equal(focused,moved?0:1);
 }
});
