import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('스프라이트 검색 재시도는 사라질 버튼의 초점을 검색 입력으로 돌린다',()=>{
  const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
  const match=source.match(/onClick=\{(event=>\{if\(document\.activeElement===event\.currentTarget\)searchRef\.current\?\.focus\(\);setSearchBusy\(true\);setError\(""\);setRequest\(\{\.\.\.request\}\);\})\}>이전 조건으로 다시 검색/);
  assert.ok(match);
  for(const focused of [true,false]){
    const button={},other={},document={activeElement:focused?button:other};let moved=false,busy=false,error='오류',requestValue;
    const context=vm.createContext({document,searchRef:{current:{focus(){moved=true;}}},setSearchBusy:value=>busy=value,setError:value=>error=value,setRequest:value=>requestValue=value,request:{source:'assets',query:'rest'}});
    vm.runInContext('('+match[1]+')',context)({currentTarget:button});
    assert.equal(moved,focused);assert.equal(busy,true);assert.equal(error,'');assert.equal(requestValue.query,'rest');
  }
});

test('명시적 시트 선택은 다른 곳으로 이동한 초점을 빼앗지 않는다',()=>{
  const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    if(focusFrom &&'),end=source.indexOf('\n  useEffect(()=>{',start+1);
  assert.ok(start>=0 && end>start);
  for(const state of ['origin','body','other','automatic']){
    const body={},origin={},document={body,activeElement:state==='body'?body:state==='other'?{}:origin};let focused=false;
    const context=vm.createContext({document,focusFrom:state==='automatic'?null:origin,region:{current:{focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);
    assert.equal(focused,state==='origin'||state==='body');
  }
});

test('같은 원본 재검색은 이전 결과를 유지하고 원본이 바뀌면 비운다',()=>{
  const sourceText=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
  const start=sourceText.indexOf('  function applyChange(change){'),end=sourceText.indexOf('\n  function requestChange(',start);
  for(const nextSource of ['assets','baseline']){
    let items=['이전 결과'],busy=false,request;
    const context=vm.createContext({source:'assets',selected:'',setItems:value=>items=value,setSource:()=>{},setSearchBusy:value=>busy=value,setError:()=>{},setLinkNotice:()=>{},select:()=>{},setRequest:value=>request=value});
    vm.runInContext(sourceText.slice(start,end)+'\nthis.applyChange=applyChange;',context);
    context.applyChange({kind:'search',source:nextSource,query:'rest'});
    assert.equal(items===null,nextSource==='baseline');assert.equal(busy,true);assert.equal(request.source,nextSource);
  }
});

test('연결 후보를 직접 선택하면 원본 선택 안내를 해제한다',()=>{
  const sourceText=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
  const start=sourceText.indexOf('  function applyChange(change){'),end=sourceText.indexOf('\n  function requestChange(',start);
  let notice='원본 선택', chosen='';
  const context=vm.createContext({selected:'',document:{activeElement:{}},selectionFocus:{current:null},setLinkNotice:value=>notice=value,select:value=>chosen=value});
  vm.runInContext(sourceText.slice(start,end)+'\nthis.applyChange=applyChange;',context);
  context.applyChange({kind:'select',path:'candidate.png'});
  assert.equal(notice,'');
  assert.equal(chosen,'candidate.png');
});
