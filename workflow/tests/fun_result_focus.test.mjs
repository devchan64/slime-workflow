import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
test('새 작업과 상태 갱신은 사용자가 선택한 다른 이력 결과를 바꾸지 않는다',()=>{
 const method=source.match(/function setJob\(value\)\{.*?\}/)?.[0];assert.ok(method);
 let selected='history',latest='original';
 const context=vm.createContext({currentJob:{current:latest},setJobState:value=>latest=value,setResultId:update=>selected=typeof update==='function'?update(selected):update});
 vm.runInContext(method+';this.setJob=setJob;',context);
 context.setJob('original');assert.equal(selected,'history');
 context.setJob('new');assert.equal(latest,'new');assert.equal(selected,'history');
 context.setJob('');assert.equal(selected,'history');
 selected='';context.setJob('next');assert.equal(selected,'next');
 context.setJob('');assert.equal(selected,'');
});
