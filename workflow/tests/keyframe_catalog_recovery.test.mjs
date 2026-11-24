import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validKeyframeCatalogPage} from '../../gui/keyframeCatalogPage.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('키프레임 목록 조회 실패 후 재조회하면 이전 목록을 정상 목록으로 교체한다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,deadline,timedOut=false;',source.indexOf('function SearchResults'));
 const end=source.indexOf('  },[query,cursor]);',start)+'  },[query,cursor]);'.length;
 let run,timer,fail=true,error='',loading=false,page={old:true};const pageTransition={current:true};
 const context=vm.createContext({AbortController,untilAborted,Date,query:'',cursor:{},pageTransition,useEffect:fn=>run=fn,validKeyframeCatalogPage,requestErrorMessage,
  setLoading:value=>loading=value,setError:value=>error=value,setPage:value=>page=value,setReceivedAt:()=>{},select:()=>{},
  setTimeout:(fn,delay)=>{if(delay===200)timer=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>fail ? Promise.reject(new Error('조회 실패')) : Promise.resolve({items:[],total:0,offset:0,next_offset:null,snapshot:'a'.repeat(64),note:''})});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'조회 실패');assert.equal(loading,false);assert.equal(page.old,true);assert.equal(pageTransition.current,false);
 cleanup();fail=false;run();timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'');assert.equal(loading,false);assert.equal(page.total,0);assert.equal(pageTransition.current,false);
});
