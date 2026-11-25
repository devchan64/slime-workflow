import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('숨긴 탭은 설정 조회를 중단하고 다시 보일 때 최신 조회만 반영한다',async()=>{
  const source=readFileSync(new URL('../../gui/ResidentModelStatus.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    if(saving)return;'),end=source.indexOf('  async function changeDflash',start);
  let visibility,cleanup,calls=0,resolveFirst,settings=null,error='';const timers=new Map();let nextTimer=0;
  const document={visibilityState:'visible',addEventListener:(_name,fn)=>visibility=fn,removeEventListener:()=>{}};
  const first=new Promise(resolve=>resolveFirst=resolve);
  const context=vm.createContext({saving:false,session:'s',revision:0,document,AbortController,untilAborted,requestErrorMessage,
    useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timers.set(++nextTimer,fn),nextTimer),clearTimeout:id=>timers.delete(id),
    setSettings:value=>settings=value,setSettingsError:value=>error=value,
    managementCommand:()=>++calls===1?first:Promise.resolve({session_id:'s',enabled:true,available:true})});
  vm.runInContext(source.slice(start,end),context);assert.equal(calls,1);
  document.visibilityState='hidden';visibility();await new Promise(done=>setImmediate(done));assert.equal(settings,null);assert.equal(error,'');assert.equal(timers.size,0);
  document.visibilityState='visible';visibility();await new Promise(done=>setImmediate(done));assert.equal(calls,2);assert.equal(settings.enabled,true);
  resolveFirst({session_id:'s',enabled:false,available:true});await new Promise(done=>setImmediate(done));assert.equal(settings.enabled,true);cleanup();assert.equal(timers.size,0);
});

test('설정 조회 시간 초과는 이전 값을 보존하고 자동 재조회로 복구한다',async()=>{
  const source=readFileSync(new URL('../../gui/ResidentModelStatus.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    if(saving)return;'),end=source.indexOf('  async function changeDflash',start);
  let cleanup,calls=0,error='',settings={session_id:'s',enabled:false,available:true},nextTimer=0;
  const timers=new Map(),document={visibilityState:'visible',addEventListener:()=>{},removeEventListener:()=>{}};
  const context=vm.createContext({saving:false,session:'s',revision:0,document,AbortController,untilAborted,requestErrorMessage,
    useEffect:fn=>cleanup=fn(),setTimeout:(fn,delay)=>(timers.set(++nextTimer,{fn,delay}),nextTimer),clearTimeout:id=>timers.delete(id),
    setSettings:value=>settings=value,setSettingsError:value=>error=value,
    managementCommand:()=>++calls===1?new Promise(()=>{}):Promise.resolve({session_id:'s',enabled:true,available:true})});
  vm.runInContext(source.slice(start,end),context);
  const run=delay=>{const [id,timer]=[...timers].find(([,item])=>item.delay===delay);timers.delete(id);timer.fn();};
  run(10000);await new Promise(done=>setImmediate(done));assert.match(error,/시간이 초과/);assert.equal(settings.enabled,false);
  run(30000);await new Promise(done=>setImmediate(done));assert.equal(settings.enabled,true);assert.equal(error,'');cleanup();assert.equal(timers.size,0);
});

test('설정 저장 중 중복 요청을 막고 시간 초과 뒤 상태를 다시 조회한다',async()=>{
  const source=readFileSync(new URL('../../gui/ResidentModelStatus.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function changeDflash'),end=source.indexOf('  const [label,description]',start);
  const controller=new AbortController();let calls=0,saving=false,error='',refreshes=0;
  const context=vm.createContext({AbortSignal:{timeout:()=>controller.signal},untilAborted,requestErrorMessage,session:'s',savingRef:{current:false},setSaving:value=>saving=value,setSaveError:value=>error=value,setSettings:()=>assert.fail('확인되지 않은 값 적용'),refresh:()=>refreshes++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
  vm.runInContext(source.slice(start,end),context);const first=context.changeDflash(true);await context.changeDflash(true);
  assert.equal(calls,1);assert.equal(saving,true);controller.abort();await first;
  assert.equal(saving,false);assert.equal(context.savingRef.current,false);assert.equal(refreshes,1);assert.ok(error);
});

test('설정 저장은 요청한 세션과 설정이 일치할 때만 값을 갱신한다',async()=>{
  const source=readFileSync(new URL('../../gui/ResidentModelStatus.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function changeDflash'),end=source.indexOf('  const [label,description]',start);
  for(const result of [{session_id:'other',enabled:true},{session_id:'s',enabled:false},{session_id:'s',enabled:true}]){
    const controller=new AbortController();let settings={enabled:false,available:true},error='',refreshes=0;
    const context=vm.createContext({AbortSignal:{timeout:()=>controller.signal},untilAborted,requestErrorMessage,session:'s',savingRef:{current:false},setSaving:()=>{},setSaveError:value=>error=value,setSettings:fn=>settings=fn(settings),refresh:()=>refreshes++,managementCommand:async()=>result});
    vm.runInContext(source.slice(start,end),context);await context.changeDflash(true);
    const accepted=result.session_id==='s' && result.enabled===true;
    assert.equal(settings.enabled,accepted);assert.equal(Boolean(error),!accepted);assert.equal(refreshes,1);
  }
});
