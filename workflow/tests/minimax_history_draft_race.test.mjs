import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {validGenerationJobId} from '../../gui/generationJobId.mjs';
const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function navigatePage('),source.indexOf('  const session=',source.indexOf('  async function navigatePage(')));
test('잘못된 복원 ID는 안내하고 초안 복원을 막는 주소 매개변수를 제거한다',()=>{
 const effect=source.match(/  useEffect\(\(\)=>\{if\(embedded\)return;const parameters=.*?\},\[embedded\]\);/)?.[0];assert.ok(effect);
 let error='',replaced;const savedState={key:'existing'};
 const context=vm.createContext({embedded:false,location:{search:'?session=abc&restore=invalid',href:'http://localhost/?session=abc&restore=invalid'},URL,URLSearchParams,validGenerationJobId,history:{state:savedState,replaceState:(state,_title,url)=>{assert.equal(state,savedState);replaced=url;}},setError:value=>error=value,useEffect:fn=>fn()});
 vm.runInContext(effect,context);assert.match(error,/작업 ID/);assert.equal(replaced.searchParams.get('session'),'abc');assert.equal(replaced.searchParams.has('restore'),false);
});
for(const condition of ['unchanged','changed','checking','storage','job'])test('이력 이동 시 입력 보존: '+condition,async()=>{
 let finish,error='',destination='',stored=null,reads=0;
 const context=vm.createContext({separatePages:true,navigationPending:{current:false},checkingSlots:{current:new Set()},inputRevision:{current:0},references:[{}],imageBase64:()=>{reads++;return new Promise(resolve=>finish=resolve);},sessionStorage:{setItem:(_key,value)=>{if(condition==='storage')throw Error('full');stored=JSON.parse(value);}},location:{assign:url=>destination=url},minimaxImageHistoryUrl:(_building,id)=>id?'job-history':'history',building:false,session:'s',prompt:'작성 중',seed:42,size:512,downscale:false,sampler:'euler',setError:value=>error=value,navigate:()=>{},setJob:()=>{}});
 vm.runInContext(code,context);const waiting=context.navigatePage('history',condition==='job'?'job-id':undefined);await context.navigatePage('history');assert.equal(reads,1);
 if(condition==='changed')context.inputRevision.current++;if(condition==='checking')context.checkingSlots.current.add(0);finish('saved-image');await waiting;
 if(['changed','checking'].includes(condition)){assert.equal(destination,'');assert.equal(stored,null);assert.match(error,/변경되어 이동하지/);}
 else if(condition==='storage'){assert.equal(destination,'');assert.match(error,/보존하지 못해/);}
 else{assert.equal(destination,condition==='job'?'job-history':'history');assert.equal(stored.prompt,'작성 중');assert.equal(stored.images[0],'saved-image');}
 assert.equal(context.navigationPending.current,false);
});
