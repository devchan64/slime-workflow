import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('보관 로그 형식 오류는 마지막 정상 로그를 유지한다',async()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const method='async function readLog(){'+source.split('async function readLog(){')[1].split('\n  return <>')[0];
  let response={log:'정상 로그'},log=null,error='',loading=false,checkedAt=null;
  const context=vm.createContext({request:{current:null},AbortController,setTimeout:()=>1,clearTimeout:()=>{},service:'qwen',id:'job',
    setLoading:value=>loading=value,setError:value=>error=value,setLog:value=>log=value,setCheckedAt:value=>checkedAt=value,
    managementCommand:async()=>response,untilAborted:promise=>promise,requestErrorMessage:problem=>problem.message});
  vm.runInContext(method,context);
  await context.readLog();assert.equal(log,'정상 로그');assert.equal(error,'');assert.equal(loading,false);const lastSuccess=checkedAt;assert.ok(lastSuccess);
  for(const invalid of [{log:{invalid:true}},{log:null},{}]){response=invalid;await context.readLog();assert.equal(log,'정상 로그');assert.equal(checkedAt,lastSuccess);assert.match(error,/형식/);assert.equal(loading,false);}
  response={log:''};await context.readLog();assert.equal(log,'');assert.equal(error,'');
});

test('보관 상세가 닫힌 뒤 늦은 로그를 반영하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const method='async function readLog(){'+source.split('async function readLog(){')[1].split('\n  return <>')[0];
  const cleanup=source.split('\n').find(line=>line.includes('useEffect(()=>()=>{const active=request.current;'));
  let resolveLate,cleanupHandler,log='기존 로그',error='',signal;
  const context=vm.createContext({request:{current:null},AbortController,setTimeout:()=>1,clearTimeout:()=>{},service:'qwen',id:'job',
    useEffect:effect=>cleanupHandler=effect(),setLoading:()=>{},setError:value=>error=value,setLog:value=>log=value,
    managementCommand:(_service,_operation,_payload,options)=>{signal=options.signal;return new Promise(resolve=>resolveLate=resolve);},untilAborted,requestErrorMessage:problem=>problem.message});
  vm.runInContext(cleanup+'\n'+method,context);
  const pending=context.readLog();cleanupHandler();assert.equal(signal.aborted,true);await pending;
  resolveLate({log:'늦은 로그'});await Promise.resolve();assert.equal(log,'기존 로그');assert.equal(error,'');assert.equal(context.request.current,null);
});

test('없는 로그의 내부 경로는 안내로 바꾸고 재조회 성공 시 오류를 지운다',async()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const method='async function readLog(){'+source.split('async function readLog(){')[1].split('\n  return <>')[0];
  let fail=true,error='',log=null,loading=false;
  const context=vm.createContext({request:{current:null},AbortController,setTimeout:()=>1,clearTimeout:()=>{},service:'qwen',id:'job',
    setLoading:value=>loading=value,setError:value=>error=value,setLog:value=>log=value,setCheckedAt:()=>{},
    managementCommand:async()=>{if(fail)throw new Error("[Errno 2] No such file or directory: '/private/worker.log'");return {log:'복구된 로그'};},
    untilAborted,requestErrorMessage:problem=>problem.message});
  vm.runInContext(method,context);
  await context.readLog();assert.match(error,/작업 ID와 이력/);assert.doesNotMatch(error,/private|worker\.log/);assert.equal(loading,false);
  fail=false;await context.readLog();assert.equal(error,'');assert.equal(log,'복구된 로그');assert.equal(loading,false);
});
