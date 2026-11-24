import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('사용설명 재시도는 빠른 중복 입력을 막고 초점 복구를 예약한다',()=>{
  const source=readFileSync(new URL('../../gui/GeneratorUsage.jsx',import.meta.url),'utf8');
  const body=source.split('onClick={()=>{')[1].split('}}>다시 불러오기')[0];
  let revisions=0;const button={};
  const context=vm.createContext({retrying:{current:false},restoreFocus:{current:false},retryRef:{current:button},
    document:{activeElement:button},setRevision:()=>revisions++});
  vm.runInContext(`function retry(){${body}}`,context);
  context.retry();context.retry();
  assert.equal(revisions,1);assert.equal(context.restoreFocus.current,true);
  context.retrying.current=false;context.document.activeElement={};context.retry();
  assert.equal(revisions,2);assert.equal(context.restoreFocus.current,false);
});
