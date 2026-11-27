import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('페이지 경계에서 잃은 초점만 복구하고 사용자가 옮긴 초점은 유지한다',()=>{
  const source=readFileSync(new URL('../../gui/CardGallery.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  function movePage('),end=source.indexOf('\n  const failures=',start);
  for(const situation of ['disabled-focused','body','moved']) {
    const document={body:{},activeElement:null};
    const target={disabled:false,isConnected:true,focus(){document.activeElement=this;}};
    const fallback={disabled:false,isConnected:true,focus(){document.activeElement=this;}};
    const other={};document.activeElement=target;
    let frame, page;
    const context=vm.createContext({document,restoreLostFocus,current:5,setPage:value=>page=value,
      focusFrame:{current:null},pagesRef:{current:{querySelector:()=>fallback}},searchRef:{current:null},
      requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
    vm.runInContext(source.slice(start,end)+'\nthis.movePage=movePage;',context);
    context.movePage({currentTarget:target},1);
    assert.equal(page,6);
    target.disabled=true;
    if(situation==='body')document.activeElement=document.body;
    if(situation==='moved')document.activeElement=other;
    frame();
    assert.equal(document.activeElement,situation==='moved' ? other : fallback);
  }
});
