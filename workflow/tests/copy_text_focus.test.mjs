import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('복사 선택을 닫을 때 사라진 초점만 복사 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/CopyTextButton.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeFallback('),source.indexOf('  return <span className="message-copy">'));
 for(const scenario of ['removed','moved','not-focused']){
  const body={},close={},other={};let callback,focused=0,state='fallback';
  const document={body,activeElement:scenario==='not-focused'?other:close};
  const context=vm.createContext({document,request:{current:0},timer:{current:null},clearTimeout:()=>{},setState:value=>state=value,requestAnimationFrame:fn=>callback=fn,button:{current:{focus:()=>focused++}}});
  vm.runInContext(code,context);context.closeFallback({currentTarget:close});
  assert.equal(state,'');assert.equal(context.request.current,1);
  if(callback){document.activeElement=scenario==='removed'?body:other;callback();}
  assert.equal(focused,scenario==='removed'?1:0);
 }
});

test('복사 내용이 바뀌어 수동 선택이 닫힐 때 해당 영역의 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/CopyTextButton.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{\s*const restore=document\.activeElement===fallback\.current[\s\S]*?\},\[value\]\);/)[0];
 for(const scenario of ['textarea','close','moved','other']){
  const body={},area={},close={},other={};let callback,focused=0,state='fallback';
  const document={body,activeElement:scenario==='close'?close:scenario==='other'?other:area};
  const context=vm.createContext({document,useEffect:fn=>fn(),value:'새 내용',fallback:{current:area},closeButton:{current:close},button:{current:{focus:()=>focused++}},request:{current:0},timer:{current:null},clearTimeout:()=>{},setState:value=>state=value,requestAnimationFrame:fn=>callback=fn});
  vm.runInContext(effect,context);assert.equal(state,'');assert.equal(context.request.current,1);
  if(callback){document.activeElement=scenario==='moved'?other:body;callback();}
  assert.equal(focused,['textarea','close'].includes(scenario)?1:0);
 }
});
