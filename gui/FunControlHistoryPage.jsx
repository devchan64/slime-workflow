import StandaloneGeneratorHistory from "./StandaloneGeneratorHistory.jsx";
import WanHistoryNavigation,{wanHistoryUrl} from "./WanHistoryNavigation.jsx";
import React,{useEffect} from 'react';
import GeneratorJobControls from './GeneratorJobControls.jsx';
import {FunControlResult} from './FunControlSchema.jsx';
import {untilAborted} from './managementCommand.js';
import {validVideoJobId} from './videoJobId.mjs';
const service='wan22-fun-control';
export function funHistoryUrl(session,id){return wanHistoryUrl(service,session,id);}
export default function FunControlHistoryPage(){
 const q=new URLSearchParams(location.search),session=q.get('session')||'';
 async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/fun-input/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);if(!response.ok)throw Error('이 작업의 입력 사본을 확인할 수 없습니다.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record.request || !Array.isArray(record.request.images) || record.request.images.length!==1 || typeof record.request.images[0]!=='string' || typeof record.request.pose_video!=='string')throw Error('저장된 입력 형식을 확인할 수 없습니다.');return {...record,request:{...record.request,pose_video:'/management/assistant/fun-pose/'+encodeURIComponent(id)}};}
 function restore(_request,record){if(!validVideoJobId(record.id))throw Error('작업 ID를 확인하세요.');const q=new URLSearchParams({restore:record.id});if(session)q.set('session',session);location.assign('/management/frame/wan22-fun-control-generator/?'+q);}
 useEffect(()=>{document.title='Fun Control 생성이력';},[]);
 return <article className="fun-control-page generator-page-common"><h1>Fun Control 생성이력</h1><WanHistoryNavigation service={service} session={session}/><StandaloneGeneratorHistory service={service} readJob={readJob} restore={restore} renderResult={(id,{resultRef,cleaned})=><section ref={resultRef} tabIndex={-1} aria-label="선택한 작업 결과"><FunControlResult key={id} job={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</FunControlResult></section>}/></article>;
}
