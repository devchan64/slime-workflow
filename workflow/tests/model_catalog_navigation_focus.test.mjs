import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('카탈로그에서 지연 이동 시 선택은 적용하고 사용자가 옮긴 초점은 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    if (!requestedSelection');const end=source.indexOf('  }, [requestedSelection, busy, modelsLoading, modelsError, models]);',start)+'  }, [requestedSelection, busy, modelsLoading, modelsError, models]);'.length;assert.ok(start>=0 && end>start);
 for(const moved of [false,true]){
  let run,focused=0,scrolled=0,selected='';const body={},origin={},other={},document={body,activeElement:moved?other:origin},requestedSelection={name:'kimodo',focusAtStart:origin};
  const c=vm.createContext({document,requestedSelection,handledSelection:{current:null},busy:false,modelsLoading:false,modelsError:'',models:[{name:'kimodo'}],headingRef:{current:{focus:()=>focused++,scrollIntoView:()=>scrolled++}},setSelectionNotice:()=>{},setSelected:x=>selected=x,setModelQuery:()=>{},setComparison:()=>{},setMetadata:()=>{},setJobResult:()=>{},showJob:()=>{},useEffect:fn=>run=fn});
  vm.runInContext(source.slice(start,end),c);run();assert.equal(selected,'kimodo');assert.equal(focused,moved?0:1);assert.equal(scrolled,focused);
 }
});

test('백업 목록 오류 후 재조회가 성공하면 요청한 선택을 이어서 적용한다',()=>{
 const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    if (!requestedSelection');const marker='  }, [requestedSelection, busy, modelsLoading, modelsError, models]);';const end=source.indexOf(marker,start)+marker.length;
 let run,selected='',notice='';const body={},other={},document={body,activeElement:other},requestedSelection={name:'kimodo',focusAtStart:{}};
 const c=vm.createContext({document,requestedSelection,handledSelection:{current:null},busy:false,modelsLoading:false,modelsError:'오류',models:[],headingRef:{current:{focus:()=>assert.fail('옮긴 초점을 가져오면 안 됨'),scrollIntoView:()=>assert.fail('스크롤하면 안 됨')}},setSelectionNotice:x=>notice=x,setSelected:x=>selected=x,setModelQuery:()=>{},setComparison:()=>{},setMetadata:()=>{},setJobResult:()=>{},showJob:()=>{},useEffect:fn=>run=fn});
 vm.runInContext(source.slice(start,end),c);run();assert.match(notice,/목록/);assert.equal(c.handledSelection.current,null);c.modelsError='';c.models=[{name:'kimodo'}];run();assert.equal(selected,'kimodo');assert.equal(notice,'');assert.equal(c.handledSelection.current,requestedSelection);
});

test('목록에 없던 설치본이 새로고침 후 나타나면 요청한 선택을 적용한다',()=>{
 const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    if (!requestedSelection');const marker='  }, [requestedSelection, busy, modelsLoading, modelsError, models]);';const end=source.indexOf(marker,start)+marker.length;
 let run,selected='',notice='';const body={},document={body,activeElement:{}},requestedSelection={name:'kimodo',focusAtStart:{}};
 const c=vm.createContext({document,requestedSelection,handledSelection:{current:null},busy:false,modelsLoading:false,modelsError:'',models:[{name:'other'}],headingRef:{current:null},setSelectionNotice:x=>notice=x,setSelected:x=>selected=x,setModelQuery:()=>{},setComparison:()=>{},setMetadata:()=>{},setJobResult:()=>{},showJob:()=>{},useEffect:fn=>run=fn});
 vm.runInContext(source.slice(start,end),c);run();assert.match(notice,/새로고침/);assert.equal(c.handledSelection.current,null);c.models=[{name:'kimodo'}];run();assert.equal(selected,'kimodo');assert.equal(notice,'');
});
