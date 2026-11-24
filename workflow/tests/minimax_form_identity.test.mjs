import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../../gui/MiniMaxForms.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function open(form_id)'),end=source.indexOf('  useEffect(()=>{if(initialFormId',start);

test('폼 열기는 다른 세션 또는 다른 폼 응답을 적용하지 않는다',async()=>{
  for(const result of [
    {session_id:'other',form_id:'form',revision:1,request:{prompt:'값'}},
    {session_id:'session',form_id:'other',revision:1,request:{prompt:'값'}}
  ]){
    let selected=null,error='';
    const context=vm.createContext({session:'session',operation:{current:false},listEpoch:{current:0},active:{current:true},
      setBusy:()=>{},setNotice:()=>{},setError:value=>error=value,setSelected:value=>selected=value,
      setPrompt:()=>{},setSeed:()=>{},setSize:()=>{},setFile:()=>{},formError:(problem)=>problem.message,call:async()=>result});
    vm.runInContext(source.slice(start,end)+'\nthis.open=open;',context);
    await context.open('form');
    assert.equal(selected,null);assert.match(error,/선택한 폼/);
  }
});

test('폼을 다시 열면 상세와 목록에 조회한 버전을 함께 반영한다',async()=>{
  let selected=null,rows=[{form_id:'form',revision:1,state:'editing'}];
  const result={session_id:'session',form_id:'form',revision:2,state:'editing',request:{prompt:'변경',seed:42,width:512,height:512}};
  const context=vm.createContext({session:'session',operation:{current:false},listEpoch:{current:0},active:{current:true},
    setBusy:()=>{},setNotice:()=>{},setError:()=>{},setSelected:value=>selected=value,setRows:update=>rows=update(rows),
    setPrompt:()=>{},setSeed:()=>{},setSize:()=>{},setFile:()=>{},formError:problem=>problem.message,call:async()=>result});
  vm.runInContext(source.slice(start,end)+'\nthis.open=open;',context);
  await context.open('form');
  assert.equal(selected.revision,2);assert.equal(rows[0].revision,2);
});
