import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('서비스 목록 조회 실패 후 정상 재조회는 안내와 잠금을 해제한다',async()=>{
  const source=readFileSync(new URL('../../gui/ServiceRegistry.jsx',import.meta.url),'utf8');
  const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  }, [query,offset,revision]);')+'  }, [query,offset,revision]);'.length);
  let run,scheduled,fail=true,error='',page=null,loading=true;
  const pending={current:true};
  const context=vm.createContext({AbortController,untilAborted,Date,TypeError,query:'',offset:0,revision:0,refreshPending:pending,focusFailure:{current:false},focusNextPage:{current:false},
    useEffect:fn=>run=fn,setLoading:value=>loading=value,setError:value=>error=value,setPage:value=>page=value,setPageQuery:()=>{},setReceivedAt:()=>{},
    setTimeout:(fn,delay)=>{if(delay===200)scheduled=fn;return 1;},clearTimeout:()=>{},
    managementCommand:async()=>{if(fail)throw new Error('');return {services:[],total:0,offset:0,next_offset:null};}});
  vm.runInContext(effect,context);const cleanup=run();await scheduled();
  assert.match(error,/다시 시도/);assert.equal(loading,false);assert.equal(pending.current,false);
  cleanup();fail=false;run();await scheduled();
  assert.equal(error,'');assert.equal(loading,false);assert.equal(pending.current,false);assert.equal(page.total,0);
});

test('검색 전환으로 중단된 서비스 조회의 늦은 응답은 현재 상태를 바꾸지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/ServiceRegistry.jsx',import.meta.url),'utf8');
  const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  }, [query,offset,revision]);')+'  }, [query,offset,revision]);'.length);
  let run,scheduled,resolveRequest,updates=0;
  const request=new Promise(resolve=>resolveRequest=resolve);
  const context=vm.createContext({AbortController,untilAborted,Date,TypeError,query:'old',offset:0,revision:0,refreshPending:{current:true},focusFailure:{current:false},focusNextPage:{current:false},
    useEffect:fn=>run=fn,setLoading:()=>updates++,setError:()=>updates++,setPage:()=>updates++,setPageQuery:()=>updates++,setReceivedAt:()=>updates++,
    setTimeout:(fn,delay)=>{if(delay===200)scheduled=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>request});
  vm.runInContext(effect,context);const cleanup=run();const completion=scheduled();cleanup();const before=updates;
  resolveRequest({services:[],total:0,offset:0,next_offset:null});await completion;
  assert.equal(updates,before);
});
