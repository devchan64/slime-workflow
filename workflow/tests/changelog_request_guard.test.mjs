import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('변경 기록의 연속 새로고침과 페이지 이동은 한 번만 요청한다',()=>{
  const source=readFileSync(new URL('../../gui/GeneratorChangelog.jsx',import.meta.url),'utf8');
  const methods=source.slice(source.indexOf('  function navigate('),source.indexOf('  const content='));
  let revisions=0,positions=0,loading=0;
  const context=vm.createContext({requestBusy:{current:false},focusRequest:{current:null},index:0,generator:'test',
    setLoading:()=>loading++,setRevision:()=>revisions++,setPosition:()=>positions++});
  vm.runInContext(methods,context);
  context.refresh();context.refresh();context.navigate(1,{currentTarget:{}});
  assert.equal(revisions,1);assert.equal(positions,0);assert.equal(loading,1);
  context.requestBusy.current=false;
  context.navigate(1,{currentTarget:{}});context.refresh();
  assert.equal(revisions,1);assert.equal(positions,1);assert.equal(loading,2);
});
