import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('모델 선택은 기존 이력 상태와 다른 주소 매개변수를 유지한다',()=>{
  const source=readFileSync(new URL('../../gui/ModelPage.jsx',import.meta.url),'utf8');
  const handler=source.slice(source.indexOf('  function chooseModel('),source.indexOf('\n  return <article',source.indexOf('  function chooseModel(')));
  const state={session:'existing'},calls=[],selected=[];
  const context=vm.createContext({URL,location:{href:'http://example.test/model?session=chat&model=old#section'},history:{state,replaceState:(...args)=>calls.push(args)},selectedRef:{current:''},missingRef:{current:'missing'},select:value=>selected.push(value),setMissingModel:()=>{}});
  vm.runInContext(handler+'\nchooseModel("kimodo");',context);
  assert.equal(calls[0][0],state);assert.equal(calls[0][2].searchParams.get('model'),'kimodo');
  assert.equal(calls[0][2].searchParams.get('session'),'chat');assert.equal(calls[0][2].hash,'#section');assert.deepEqual(selected,['kimodo']);
});

test('맵 종류 주소 갱신은 기존 이력 상태와 선택 맵을 유지한다',()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const start=source.indexOf('    const url=new URL(location.href);',source.indexOf('const recoveryParams='));
  const end=source.indexOf('\n    untilAborted(',start);
  for(const field of [true,false]){
    const state={session:'existing'},calls=[];
    const context=vm.createContext({URL,field,location:{href:'http://example.test/map?session=chat&map=iseulon#view'},history:{state,replaceState:(...args)=>calls.push(args)}});
    vm.runInContext(source.slice(start,end),context);
    assert.equal(calls[0][0],state);assert.equal(calls[0][2].searchParams.get('mapKind'),field?'field':'town');
    assert.equal(calls[0][2].searchParams.get('map'),'iseulon');assert.equal(calls[0][2].searchParams.get('session'),'chat');assert.equal(calls[0][2].hash,'#view');
  }
});

test('맵 로딩 복구 주소는 종류와 선택 맵 및 대화 세션을 보존한다',()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  const recoveryParams=new URLSearchParams(');
  const end=source.indexOf('\n  useEffect(',start);
  for(const field of [true,false]){
    const context=vm.createContext({URLSearchParams,field,location:{search:'?map=iseulon&session=chat'}});
    vm.runInContext(source.slice(start,end)+'\nthis.result=recoveryParams.toString();',context);
    const params=new URLSearchParams(context.result);
    assert.equal(params.get('mapKind'),field?'field':'town');
    assert.equal(params.get('map'),'iseulon');assert.equal(params.get('session'),'chat');
  }
});

test('지도 종류 이동은 대화 세션을 유지하고 이전 지도 선택은 비운다',()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  const destination=kind=>{');
  const end=source.indexOf('\n  async function exportImage()',start);
  const context=vm.createContext({URL,location:{href:'http://example.test/field-map/?map=old&session=chat#view'}});
  vm.runInContext(source.slice(start,end)+'\nthis.destination=destination;',context);
  for(const kind of ['town','field','battle']){
    const url=new URL(context.destination(kind));
    assert.equal(url.pathname,'/management/frame/map-review/');
    assert.equal(url.searchParams.get('mapKind'),kind);assert.equal(url.searchParams.get('session'),'chat');
    assert.equal(url.searchParams.has('map'),false);assert.equal(url.hash,'#view');
  }
});
