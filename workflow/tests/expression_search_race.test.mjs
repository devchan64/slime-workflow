import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('검색어가 바뀐 직후 이전 표정 조회의 응답은 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/ExpressionCatalog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,deadline,timedOut=false;');
 const end=source.indexOf('  },[query,cursor]);',start)+'  },[query,cursor]);'.length;
 let run,timer,resolveRequest,updates=0;const currentQuery={current:'old'};
 const context=vm.createContext({AbortController,untilAborted,Date,query:'old',cursor:{},currentQuery,requestRevision:{current:0},navigationPending:{current:true},useEffect:fn=>run=fn,
  setLoading:()=>updates++,setError:()=>updates++,setPage:()=>updates++,setPageQuery:()=>updates++,setReceivedAt:()=>updates++,validExpressionCatalogPage:()=>true,requestErrorMessage:()=>'',
  setTimeout:(fn,delay)=>{if(delay===200)timer=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>new Promise(resolve=>resolveRequest=resolve)});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();const request=timer();currentQuery.current='new';const before=updates;
 resolveRequest({});await request;assert.equal(updates,before);cleanup();
});

test('표정 페이지 이동 직후 이전 페이지 응답과 중복 이동을 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/ExpressionCatalog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,deadline,timedOut=false;');
 const end=source.indexOf('  },[query,cursor]);',start)+'  },[query,cursor]);'.length;
 const navigate=source.slice(source.indexOf('  function navigate(event,next)'),source.indexOf('  return <section'));
 let run,timer,resolveRequest,updates=0,moves=0;const button={};
 const context=vm.createContext({AbortController,untilAborted,Date,query:'q',cursor:{},currentQuery:{current:'q'},requestRevision:{current:0},navigationPending:{current:false},pageOrigin:{current:null},focusPage:{current:false},document:{activeElement:button},button,useEffect:fn=>run=fn,
  setLoading:()=>updates++,setError:()=>updates++,setPage:()=>updates++,setPageQuery:()=>updates++,setReceivedAt:()=>updates++,setPagination:()=>moves++,validExpressionCatalogPage:()=>true,requestErrorMessage:()=>'',
  setTimeout:(fn,delay)=>{if(delay===200)timer=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>new Promise(resolve=>resolveRequest=resolve)});
 vm.runInContext(source.slice(start,end)+navigate,context);const cleanup=run();const request=timer();context.navigationPending.current=false;
 context.navigate({currentTarget:button},{offset:20});context.navigate({currentTarget:button},{offset:20});const before=updates;
 resolveRequest({});await request;assert.equal(updates,before);assert.equal(moves,1);cleanup();
});

test('표정 목록 조회 실패 후 재조회가 성공하면 오류와 이동 잠금이 해제된다',async()=>{
 const source=readFileSync(new URL('../../gui/ExpressionCatalog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,deadline,timedOut=false;');
 const end=source.indexOf('  },[query,cursor]);',start)+'  },[query,cursor]);'.length;
 let run,timer,fail=true,error='',page=null,loading=false;const navigationPending={current:true};
 const context=vm.createContext({AbortController,untilAborted,Date,query:'q',cursor:{},currentQuery:{current:'q'},requestRevision:{current:0},navigationPending,useEffect:fn=>run=fn,
  setLoading:value=>loading=value,setError:value=>error=value,setPage:value=>page=value,setPageQuery:()=>{},setReceivedAt:()=>{},validExpressionCatalogPage:()=>true,requestErrorMessage:problem=>problem.message,
  setTimeout:(fn,delay)=>{if(delay===200)timer=fn;return 1;},clearTimeout:()=>{},managementCommand:async()=>{if(fail)throw new Error('조회 실패');return {records:[]};}});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await timer();
 assert.equal(error,'조회 실패');assert.equal(loading,false);assert.equal(navigationPending.current,false);
 cleanup();fail=false;run();await timer();
 assert.equal(error,'');assert.equal(loading,false);assert.equal(navigationPending.current,false);assert.deepEqual(page.records,[]);
});
