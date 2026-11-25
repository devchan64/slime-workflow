import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('Ref2VA 이력 적용은 사용자가 옮긴 초점과 새 검토를 존중한다',()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3Ref2VAPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function restoreSavedInput('),source.indexOf('  return <article',source.indexOf('  function restoreSavedInput(')));
 for(const scenario of ['restore','moved','review','edit']){
  let frame,focused=0;const body={},origin={},other={},document={body,activeElement:origin},card={open:false};
  const context=vm.createContext({document,busy:false,pending:null,activeRead:{current:null},interactionRef:{current:{busy:false,pending:null}},editVersion:{current:0},promptEdited:{current:false},inputRef:{current:card},formRef:{current:{isConnected:true,focus:()=>focused++}},atob,Uint8Array,File,setPrompt:()=>{},setSeed:()=>{},setFile:()=>{},setError:()=>{},setNotice:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(code,context);context.restoreSavedInput({edit_video:'YQ==',prompt:'p',seed:42},{version:0,id:'id',focusAtStart:origin});assert.equal(card.open,true);document.activeElement=scenario==='moved'?other:body;if(scenario==='review')context.interactionRef.current.pending={};if(scenario==='edit')context.editVersion.current++;frame();assert.equal(focused,scenario==='restore'?1:0,scenario);
 }
});
