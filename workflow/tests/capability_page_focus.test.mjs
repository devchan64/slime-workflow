import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('관리 기능 페이지 이동은 키보드 초점만 복구하고 이후 이동을 존중한다',()=>{
  const source=readFileSync(new URL('../../gui/CapabilitySearch.jsx',import.meta.url),'utf8');
  const effect=source.match(/useEffect\(\(\)=>\{const origin=focusPage\.current;.*?\},\[safePage\]\);/s)?.[0];
  const change=source.slice(source.indexOf('  function changePage(event,next)'),source.indexOf('  return <section'));
  assert.ok(effect && change);
  for(const scenario of ['lost','retained','moved','pointer']){
    const body={},button={},other={};let focused=0,scrolled=0,runEffect;
    const document={body,activeElement:scenario==='pointer'?other:button};
    const context=vm.createContext({document,focusPage:{current:null},headingRef:{current:{focus:()=>focused++,scrollIntoView:()=>scrolled++}},setPagination:()=>{},query:'',safePage:0,useEffect:fn=>runEffect=fn});
    vm.runInContext(change+';'+effect,context);
    context.changePage({currentTarget:button},1);
    document.activeElement=scenario==='lost'?body:scenario==='retained'?button:other;
    runEffect();
    assert.equal(focused,scenario==='lost'||scenario==='retained'?1:0,scenario);
    assert.equal(scrolled,focused,scenario);
  }
});

test('관리 기능 조회 실패 후 다시 조회하면 오류와 잠금이 해제된다',async()=>{
  const source=readFileSync(new URL('../../gui/CapabilitySearch.jsx',import.meta.url),'utf8');
  const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  }, [revision]);')+'  }, [revision]);'.length);
  let load,fail=true,error='',catalog=null,loading=true;
  const pending={current:true};
  const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,Date,TypeError,revision:0,refreshPending:pending,
    useEffect:fn=>load=fn,setLoading:value=>loading=value,setError:value=>error=value,setCatalog:value=>catalog=value,setReceivedAt:()=>{},
    validCapabilityCatalog:value=>Array.isArray(value.rows),
    fetch:async()=>{if(fail)throw new Error('');return {ok:true,json:async()=>({rows:[],summary:''})};}});
  vm.runInContext(effect,context);const cleanup=load();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(error,/다시 시도/);assert.equal(loading,false);assert.equal(pending.current,false);
  cleanup();fail=false;pending.current=true;load();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(error,'');assert.equal(loading,false);assert.equal(pending.current,false);assert.deepEqual(catalog.rows,[]);
});

test('관리 기능 새로고침은 중복 입력을 막고 버튼에 있던 초점만 복구한다',()=>{
  const source=readFileSync(new URL('../../gui/CapabilitySearch.jsx',import.meta.url),'utf8');
  const handler=source.slice(source.indexOf('  function refreshCatalog(event)'),source.indexOf('  return <section'));
  for(const focused of [true,false]){
    const body={},button={},other={};let requests=0,loading=false;
    const context=vm.createContext({document:{body,activeElement:focused?button:other},refreshPending:{current:false},restoreFocus:{current:false},setLoading:value=>loading=value,refresh:()=>requests++});
    vm.runInContext(handler,context);context.refreshCatalog({currentTarget:button});context.refreshCatalog({currentTarget:button});
    assert.equal(requests,1);assert.equal(loading,true);assert.equal(context.restoreFocus.current,focused);
  }
});
