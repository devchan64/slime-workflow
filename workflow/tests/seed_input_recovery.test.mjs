import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('랜덤 시드 실패는 기존 값을 유지하고 이후 성공 시 오류를 지운다',()=>{
 const source=readFileSync(new URL('../../gui/SeedInput.jsx',import.meta.url),'utf8');
 const body=source.split('onClick={()=>{')[1].split('}}>랜덤 시드')[0];
 let current='123',error='',fail=true;
 const context=vm.createContext({max:100,randomSeed:()=>{if(fail)throw Error('실패');return 42;},
  setRandomError:value=>error=value,onChange:value=>current=value});
 vm.runInContext(`function click(){${body}}`,context);context.click();
 assert.equal(current,'123');assert.match(error,/직접 입력/);
 fail=false;context.click();assert.equal(current,'42');assert.equal(error,'');
});
