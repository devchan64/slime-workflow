import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('다운로드 기록 갱신 요청은 렌더 전에 중복을 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/DownloadProgress.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(() => {\n    let active='),source.indexOf('  const stale='));
 const refresh=source.slice(source.indexOf('  function refreshProgress()'),source.indexOf('  const live='));
 let cleanup,timers=[],calls=0,revisions=0,checking=true;
 const pending={current:true};
 const context=vm.createContext({pending,service:'service',revision:0,AbortController,untilAborted,downloadPollInterval:()=>1000,requestErrorMessage:()=>'',useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout:()=>{},fetch:async()=>{calls++;return {ok:true,json:async()=>({active:false,lines:[]})};},setChecking:value=>checking=value,setRevision:()=>revisions++,setLines:()=>{},setDownloading:()=>{},setCheckedAt:()=>{},setError:()=>{}});
 vm.runInContext(refresh+effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(calls,1);assert.equal(pending.current,false);
 context.refreshProgress();context.refreshProgress();
 assert.equal(revisions,1);assert.equal(checking,true);assert.equal(calls,1);
 cleanup();assert.equal(calls,1);
});

test('다운로드 기록의 손상 응답은 오류를 알리고 재조회에서 복구한다',async()=>{
 const source=readFileSync(new URL('../../gui/DownloadProgress.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(() => {\n    let active='),source.indexOf('  const stale='));
 let cleanup,timers=[],error='',lines=null,attempt=0;
 const context=vm.createContext({pending:{current:true},service:'service',revision:0,AbortController,untilAborted,downloadPollInterval:()=>1000,requestErrorMessage:problem=>problem.message,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>++attempt===1?{active:false,lines:[null]}:{active:true,lines:['받는 중']}}),setChecking:()=>{},setRevision:()=>{},setLines:value=>lines=value,setDownloading:()=>{},setCheckedAt:()=>{},setError:value=>error=value});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.match(error,/응답을 확인할 수 없습니다/);assert.equal(lines,null);
 cleanup();context.revision=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(error,'');assert.deepEqual(lines,['받는 중']);assert.equal(context.pending.current,false);cleanup();
});

test('다운로드 기록의 JSON 파싱 실패 후 재조회가 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/DownloadProgress.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(() => {\n    let active='),source.indexOf('  const stale='));
 let cleanup,error='',lines=null,attempt=0;
 const context=vm.createContext({pending:{current:true},service:'service',revision:0,AbortController,untilAborted,requestErrorMessage:problem=>problem.message,useEffect:fn=>cleanup=fn(),setTimeout,clearTimeout,fetch:async()=>({ok:true,json:async()=>{if(++attempt===1)throw new SyntaxError('Unexpected token');return {active:false,lines:['완료']};}}),setChecking:()=>{},setLines:value=>lines=value,setDownloading:()=>{},setCheckedAt:()=>{},setError:value=>error=value});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(error,'다운로드 기록 응답을 확인할 수 없습니다.');assert.equal(lines,null);
 cleanup();vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(error,'');assert.deepEqual(lines,['완료']);cleanup();
});
