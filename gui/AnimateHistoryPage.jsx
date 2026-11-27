import StandaloneGeneratorHistory from "./StandaloneGeneratorHistory.jsx";
import WanHistoryNavigation,{wanHistoryUrl} from "./WanHistoryNavigation.jsx";
import React,{useEffect} from 'react';
import GeneratorJobResult from './GeneratorJobResult.jsx';
import {readAnimateJob} from './readAnimateJob.js';
import {validVideoJobId} from './videoJobId.mjs';
const service='wan22-animate2';
export function animateHistoryUrl(session,id){return wanHistoryUrl(service,session,id);}
export default function AnimateHistoryPage(){
 const q=new URLSearchParams(location.search),session=q.get('session')||'';
 async function readHistory(id,options){const record=await readAnimateJob(id,options);return {...record,request:{...record.request,images:[record.reference],driving_video:record.motion}};}
 function restore(_request,record){if(!validVideoJobId(record.id))throw Error('작업 ID를 확인하세요.');const q=new URLSearchParams({restore:record.id});if(session)q.set('session',session);location.assign('/management/frame/wan22-animate2-generator/?'+q);}
 useEffect(()=>{document.title='Animate-2 생성이력';},[]);
 return <article className="animate-page generator-page-common animate-standalone"><h1>Animate-2 생성이력</h1><WanHistoryNavigation service={service} session={session}/><StandaloneGeneratorHistory service={service} readJob={readHistory} restore={restore} renderResult={(id,{resultRef,cleaned})=><section ref={resultRef} tabIndex={-1} aria-label="선택한 Animate-2 작업 결과"><GeneratorJobResult selectionControls job={id} service={service} readJobWithSignal={readAnimateJob} controls={false} onDeleted={cleaned}/></section>}/></article>;
}
