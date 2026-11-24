import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('정렬 미리보기의 빈 오류 후 재시도는 오류를 지우고 결과를 표시한다',async()=>{
  const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    const element=canvas.current;');
  const end=source.indexOf('  },[detail,values,play,frame,host,guides,revision]);',start)+'  },[detail,values,play,frame,host,guides,revision]);'.length;
  let run,fail=true,error='',status='',loading=false;
  const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,canvas:{current:{effectPreviewRevision:0}},detail:{},values:{},play:false,frame:0,host:true,guides:true,revision:0,
    useEffect:fn=>run=fn,setError:value=>error=value,setStatus:value=>status=value,setLoading:value=>loading=value,
    drawAlignment:()=>fail ? Promise.reject(null) : Promise.resolve('미리보기 준비')});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(error,/불러오지 못했습니다/);assert.equal(loading,false);assert.equal(status,'');
  cleanup();fail=false;run();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(error,'');assert.equal(status,'미리보기 준비');assert.equal(loading,false);
});
