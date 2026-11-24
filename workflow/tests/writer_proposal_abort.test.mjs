import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('작가 독립 화면 종료는 제안 조회를 중단하고 늦은 응답을 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/WriterPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf("  useEffect(()=>{\n    if(embedded || !params.has('proposal_job'))return;"),end=source.indexOf('  },[]);',start)+'  },[]);'.length;assert.ok(start>=0 && end>start);
 let run,signal,resolve,updates=0;
 const context=vm.createContext({AbortController,embedded:false,params:new URLSearchParams('proposal_job=x'),location:{search:''},session:'s',useEffect:fn=>run=fn,generationProposalScope:()=>({}),readGenerationProposal:(_command,_scope,options)=>(signal=options.signal,new Promise(done=>resolve=done)),managementCommand:()=>{},setProposal:()=>updates++,setProposalScope:()=>updates++,setNotice:()=>updates++,setProposalError:()=>updates++,setProposalLoading:()=>updates++,requestErrorMessage:error=>error.message});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();cleanup();resolve({mode:'write',prompt:'내용'});await new Promise(done=>setImmediate(done));assert.equal(signal.aborted,true);assert.equal(updates,0);
});
