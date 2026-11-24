import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('키프레임 원본 조회 실패 후 재조회하면 오류와 잠금이 해제된다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;',source.indexOf('function Preview'));
 const end=source.indexOf('  },[id,attempt]);',start)+'  },[id,attempt]);'.length;
 let run,fail=true,error='',result=null;const retryPending={current:true},id='a'.repeat(32);
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,id,attempt:0,retryPending,useEffect:fn=>run=fn,setError:value=>error=value,setResult:value=>result=value,requestErrorMessage,
  managementCommand:()=>fail ? Promise.reject(new Error('조회 실패')) : Promise.resolve({id,image_base64:'encoded',sha256:'b'.repeat(64)})});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'조회 실패');assert.equal(retryPending.current,false);assert.equal(result,null);
 cleanup();fail=false;run();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'');assert.equal(retryPending.current,false);assert.equal(result.id,id);
});
