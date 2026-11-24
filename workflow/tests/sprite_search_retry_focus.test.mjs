import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('스프라이트 검색 재시도는 사라질 버튼의 초점을 검색 입력으로 돌린다',()=>{
  const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
  const match=source.match(/onClick=\{(event=>\{if\(document\.activeElement===event\.currentTarget\)searchRef\.current\?\.focus\(\);setError\(""\);setRequest\(\{\.\.\.request\}\);\})\}>이전 조건으로 다시 검색/);
  assert.ok(match);
  for(const focused of [true,false]){
    const button={},other={},document={activeElement:focused?button:other};let moved=false,error='오류',requestValue;
    const context=vm.createContext({document,searchRef:{current:{focus(){moved=true;}}},setError:value=>error=value,setRequest:value=>requestValue=value,request:{source:'assets',query:'rest'}});
    vm.runInContext('('+match[1]+')',context)({currentTarget:button});
    assert.equal(moved,focused);assert.equal(error,'');assert.equal(requestValue.query,'rest');
  }
});
