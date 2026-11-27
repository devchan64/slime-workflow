import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

for(const [name,guard,startRef,inputName,dep] of [
  ['VacePage.jsx','restoreStarted','inputRef','values','values'],
  ['FunControlPage.jsx','externalRestoreStarted','requestRef','request','request'],
  ['SoundEffectPage.jsx','restoredQuery','formRef','form','form'],
])test(`${name}: 저장 입력 조회 중 수정은 복원을 거절하고 사유를 표시한다`,async()=>{
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const line=source.split('\n').find(value=>value.includes('useEffect(()=>{if(embedded || !') && value.includes(guard));assert.ok(line);
  let run,deps,finish,error='',applied=0;const old={prompt:'기존'},current={current:old};
  const c={embedded:false,template:{},values:old,request:old,form:old,[guard]:{current:false},[startRef]:current,reviewEpoch:{current:0},interactionRef:{current:{busy:false,pending:null,review:null}},
    location:{search:'?restore=2026-11-24_11-17-24-15f79014',href:'http://localhost/?restore=2026-11-24_11-17-24-15f79014'},history:{state:null,replaceState(){}},URL,URLSearchParams,AbortController,Boolean,
    validVideoJobId:()=>true,validGenerationJobId:()=>true,useEffect:(fn,arr)=>{run=fn;deps=arr;},
    readJob:()=>new Promise(resolve=>finish=()=>resolve({request:{prompt:'저장'},inputAtStart:old,formAtStart:old,reviewAtStart:0})),
    restore:(_request,record)=>{if(record.inputAtStart!==current.current)throw Error('조회 중 입력이 변경되어 적용하지 않았습니다.');applied++;},setForm:()=>applied++,setNotice:(message,isError)=>{if(isError)error=message;},setError:message=>error=message};
  vm.createContext(c);vm.runInContext(line,c);const firstDeps=Array.from(deps);run();current.current={prompt:'새 입력'};c[inputName]=current.current;vm.runInContext(line,c);assert.deepEqual(Array.from(deps),firstDeps,dep+' 변경으로 조회를 중단하면 안 됩니다.');finish();await new Promise(resolve=>setImmediate(resolve));assert.equal(applied,0);assert.match(error,/입력이 변경/);
});
