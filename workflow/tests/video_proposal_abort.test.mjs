import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const templates={
 fun:{file:'FunControlPage.jsx',begin:'  useEffect(()=>{\n    const controller=new AbortController();\n    let active=true,timedOut=false;',end:'  },[templateRetry]);',data:{defaults:{frames:5,steps:1,seed:1,flow_shift:1,guidance_scale:1,switch_ratio:1,model_profile:'m'},maximum_frames:5,maximum_seed:1,models:[{id:'m',label:'모델'}],examples:[]}},
 vace:{file:'VacePage.jsx',begin:'  useEffect(()=>{\n    let active=true,timedOut=false;\n    const controller=new AbortController();',end:'  },[templateRevision]);',data:{defaults:{mode:'text',frames:5,steps:1,seed:1,flow_shift:1,guidance_scale:1,reference_strength:1},modes:[{id:'text',label:'텍스트',help:'도움'}],maximum_seed:1}}
};
for(const [name,spec] of Object.entries(templates))test(`${name} 화면 종료는 대화 제안 조회에도 중단을 전달한다`,async()=>{
 const source=readFileSync(new URL('../../gui/'+spec.file,import.meta.url),'utf8'),start=source.indexOf(spec.begin),end=source.indexOf(spec.end,start)+spec.end.length;assert.ok(start>=0 && end>start);
 let run,signal,finish,updates=0;
 const context=vm.createContext({AbortController,URLSearchParams,location:{search:''},session:'session',embedded:false,templateRetry:0,templateRevision:0,useEffect:fn=>run=fn,setTimeout:()=>1,clearTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>spec.data}),generationProposalScope:()=>({}),readGenerationProposal:(_command,_scope,options)=>(signal=options.signal,new Promise(resolve=>finish=resolve)),managementCommand:()=>{},funProposalInputs:(initial)=>initial,vaceProposalInputs:(initial)=>initial,setTemplateError:()=>{},setError:()=>updates++,setNotice:()=>updates++,setTemplate:()=>updates++,setRequest:()=>updates++,setValues:()=>updates++,select:()=>updates++});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));assert.ok(signal);cleanup();assert.equal(signal.aborted,true);const before=updates;finish({});await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,before);
});
