import StandaloneGeneratorHistory from "./StandaloneGeneratorHistory.jsx";
import WanHistoryNavigation,{wanHistoryUrl} from "./WanHistoryNavigation.jsx";
import React,{useEffect} from 'react';
import GeneratorJobControls from './GeneratorJobControls.jsx';
import MediaJobResult from './MediaJobResult.jsx';
import {untilAborted} from './managementCommand.js';
import {validVideoJobId} from './videoJobId.mjs';
const service='wan22-vace';
export function vaceHistoryUrl(session,id){return wanHistoryUrl(service,session,id);}
export default function VaceHistoryPage(){
 const q=new URLSearchParams(location.search),session=q.get('session')||'';
 async function readJob(id,{signal}={}){const prefix='/management/assistant/vace-input/'+encodeURIComponent(id)+'/';const response=await untilAborted(fetch(prefix+'request',{cache:'no-store',signal}),signal);if(!response.ok)throw Error('저장된 입력 사본을 확인할 수 없습니다.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record.request || typeof record.request!=='object' || !Array.isArray(record.attachments) || record.attachments.some(key=>!['reference','pose_video','edit_video','edit_mask'].includes(key)) || new Set(record.attachments).size!==record.attachments.length)throw Error('저장 입력 형식을 확인할 수 없습니다.');const request={...record.request};for(const key of record.attachments){if(key==='reference')request.images=[prefix+key];else request[key]=prefix+key;}return {...record,request};}
 function restore(_request,record){if(!validVideoJobId(record.id))throw Error('작업 ID를 확인하세요.');const q=new URLSearchParams({restore:record.id});if(session)q.set('session',session);location.assign('/management/frame/wan22-vace-generator/?'+q);}
 useEffect(()=>{document.title='VACE 생성이력';},[]);
 return <article className="vace-page generator-page-common vace-standalone"><h1>VACE 생성이력</h1><WanHistoryNavigation service={service} session={session}/><StandaloneGeneratorHistory service={service} readJob={readJob} restore={restore} renderResult={(id,{resultRef,cleaned})=><section ref={resultRef} tabIndex={-1} aria-label="선택한 VACE 작업 결과"><MediaJobResult key={id} service={service} id={id} hideProgress>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></article>;
}
