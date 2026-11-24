import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('키프레임 페이지 전환은 첫 입력 직후 중복을 막는다',()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const method=source.split('\n').find(line=>line.trim().startsWith('function changePage('));
 const button={},changes=[];
 const context=vm.createContext({pageTransition:{current:false},pageOrigin:{current:null},restorePageFocus:{current:false},
  document:{activeElement:button},setLoading:value=>changes.push(['loading',value]),setCursor:value=>changes.push(['cursor',value])});
 vm.runInContext(method,context);context.changePage({offset:20},{currentTarget:button});context.changePage({offset:40},{currentTarget:button});
 assert.equal(changes.length,2);assert.equal(changes[0][1],true);assert.equal(changes[1][1].offset,20);
 assert.equal(context.restorePageFocus.current,true);assert.equal(context.pageTransition.current,true);
});

test('조회 실패 후 잠금을 풀어 처음부터 다시 조회할 수 있다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    let active=true,deadline'),source.indexOf('  return <section ref={sectionRef}'));
 const method=source.split('\n').find(line=>line.trim().startsWith('function changePage('));
 let start,error='',cursor=null;const button={};
 const context=vm.createContext({AbortController,pageTransition:{current:true},pageOrigin:{current:null},restorePageFocus:{current:false},
  document:{activeElement:button},query:'',cursor:{},useEffect:fn=>fn(),setTimeout:(fn,ms)=>{if(ms===200)start=fn;return 1;},clearTimeout:()=>{},
  setLoading:()=>{},setError:value=>error=value,setCursor:value=>cursor=value,managementCommand:()=>Promise.reject(Error('실패')),
  untilAborted:promise=>promise,requestErrorMessage:problem=>problem.message});
 vm.runInContext(effect+'\n'+method,context);start();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'실패');assert.equal(context.pageTransition.current,false);
 context.changePage({},{currentTarget:button});assert.ok(cursor);assert.equal(context.pageTransition.current,true);
});

test('화면 종료 후 늦은 목록 응답은 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    let active=true,deadline'),source.indexOf('  return <section ref={sectionRef}'));
 let start,cleanup,finish,signal,updates=0;
 const context=vm.createContext({AbortController,Date,pageTransition:{current:true},query:'',cursor:{},useEffect:fn=>cleanup=fn(),
  setTimeout:(fn,ms)=>{if(ms===200)start=fn;return 1;},clearTimeout:()=>{},setLoading:()=>{},setError:()=>{},
  setPage:()=>updates++,setReceivedAt:()=>updates++,select:()=>updates++,validKeyframeCatalogPage:()=>true,
  managementCommand:(_service,_command,_payload,options)=>{signal=options.signal;return new Promise(resolve=>finish=resolve);},untilAborted:promise=>promise});
 vm.runInContext(effect,context);start();cleanup();assert.equal(signal.aborted,true);
 finish({});await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,0);
});
