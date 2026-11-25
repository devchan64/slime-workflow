import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('양도 이력 조회에서 메시지 없는 오류가 발생해도 이전 결과와 재조회 안내를 유지한다', async()=>{
  const source=readFileSync(new URL('../../gui/GpuHandoffHistory.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function refresh(){');
  const end=source.indexOf('  useEffect(',start);
  assert.ok(start>=0 && end>start);
  for(const problem of [null,new Error('')]){
    let error='',busy=false,rows=['previous'];
    const context=vm.createContext({AbortController,TypeError,Date,setTimeout,clearTimeout,untilAborted,
      activeRequest:{current:null},rowRevision:{current:0},session:'session',page:0,size:5,
      managementCommand:async()=>{throw problem;},setBusy:value=>busy=value,setError:value=>error=value,
      setRows:value=>rows=value,setCheckedAt:()=>{}});
    vm.runInContext(source.slice(start,end)+'\nthis.refresh=refresh;',context);
    await context.refresh();
    assert.match(error,/다시 조회/);
    assert.equal(busy,false);
    assert.deepEqual(rows,['previous']);
  }
});
