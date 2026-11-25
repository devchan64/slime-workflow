import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('사용설명 재시도는 빠른 중복 입력을 막고 초점 복구를 예약한다',()=>{
  const source=readFileSync(new URL('../../gui/GeneratorUsage.jsx',import.meta.url),'utf8');
  const body=source.split('function retry(){')[1].split('}\n  return')[0];
  let revisions=0;const button={};
  const context=vm.createContext({retrying:{current:false},restoreFocus:{current:false},retryRef:{current:button},
    document:{activeElement:button},setRevision:()=>revisions++});
  vm.runInContext(`function retry(){${body}}`,context);
  context.retry();context.retry();
  assert.equal(revisions,1);assert.equal(context.restoreFocus.current,true);
  context.retrying.current=false;context.document.activeElement={};context.retry();
  assert.equal(revisions,2);assert.equal(context.restoreFocus.current,false);
});

test('재조회 중에는 이탈한 초점을 빼앗지 않고 로딩 안내로 이동한다',()=>{
  const source=readFileSync(new URL('../../gui/GeneratorUsage.jsx',import.meta.url),'utf8');
  const effect=source.split('\n').find(line=>line.includes('loadingRef.current?.focus()'));
  for(const target of ['body','other']){
    const body={},other={};let focused=0;
    const context=vm.createContext({restoreFocus:{current:true},visibleError:'',visibleContent:null,
      document:{body,activeElement:target==='body'?body:other},loadingRef:{current:{focus:()=>focused++}},useEffect:fn=>fn()});
    vm.runInContext(effect,context);
    assert.equal(focused,target==='body'?1:0);
  }
});
