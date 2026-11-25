import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('콘텐츠 DB 조회가 메시지 없이 실패해도 오류를 표시하고 대기를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/ContentDatabaseStatus.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true;'),end=source.indexOf('  },[revision]);',start)+'  },[revision]);'.length;
 let error='',loading=true,cleanup;const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,revision:0,useEffect:fn=>cleanup=fn(),setTimeout,clearTimeout,setLoading:value=>loading=value,setError:value=>error=value,managementCommand:()=>Promise.reject(null)});
 vm.runInContext(source.slice(start,end),context);await new Promise(resolve=>setImmediate(resolve));
 assert.match(error,/요청을 처리할 수 없습니다/);assert.equal(loading,false);cleanup();
});
