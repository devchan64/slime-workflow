import React,{useEffect,useRef,useState} from 'react';
import {SendBuildingReview} from './BuildingReviewCandidate.jsx';
import GeneratorHistory from './GeneratorHistory.jsx';
import HistoryCleanup from './HistoryCleanup.jsx';
import MediaJobResult from './MediaJobResult.jsx';
import SavedGeneratorInputs from './SavedGeneratorInputs.jsx';
import {validGenerationJobId} from './generationJobId.mjs';
import {untilAborted} from './managementCommand.js';

export const MINI_MAX_IMAGE_HISTORY='/management/frame/minimax-h3-image-history/';
export function minimaxImageHistoryUrl(building,id){const q=new URLSearchParams();if(building)q.set('form','building');if(id)q.set('job',id);return MINI_MAX_IMAGE_HISTORY+(q.size?'?'+q:'')+(id?'#job-result':'');}
export function MiniMaxImageHistory({job,setJob,revision,setRevision,readJob,restore,historyRef,resultRef}){
  useEffect(()=>{const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;},[historyRef]);
  return <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service="minimax-h3-image" statusCommand="status" card allowPriority toggleResult renderSelectionAction={record=><SendBuildingReview key={record.id} id={record.id} status={record.recorded_status}/>} readJobWithSignal={readJob} restore={restore} openResult={setJob} resultId={job} onCloseResult={()=>setJob('')} onSelectedDeleted={id=>{if(id===job)setJob('');setRevision(n=>n+1);}} footer={<HistoryCleanup service="minimax-h3-image" allowSelected={false} onDeleted={()=>{setJob('');setRevision(n=>n+1);}}/>} renderResult={id=><section id="job-result" ref={resultRef} tabIndex={-1} aria-label="선택한 이미지 작업 결과"><SavedGeneratorInputs id={id} service="minimax-h3-image" statusCommand="status"/><MediaJobResult kind="image" service="minimax-h3-image" id={id}/></section>}/></div>;
}
export default function MiniMaxImageHistoryPage({building:legacyBuilding=false}={}){
  const q=new URLSearchParams(location.search),building=legacyBuilding || q.get('form')==='building';
  const form=building ? '/management/frame/minimax-h3-building-generator/' : '/management/frame/minimax-h3-image-generator/';
  const [job,setJob]=useState(validGenerationJobId(q.get('job')) ? q.get('job') : ''),[revision,setRevision]=useState(0);
  const historyRef=useRef(null),resultRef=useRef(null);
  useEffect(()=>{document.title='MiniMax H3 이미지 생성이력';},[]);
  async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/minimax-h3-image-input/'+encodeURIComponent(id),{signal,cache:'no-store'}),signal);if(!response.ok)throw Error('저장된 입력을 읽을 수 없습니다.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record?.request || typeof record.request!=='object')throw Error('저장된 입력을 확인할 수 없습니다.');return record;}
  function restore(request,record){if(!validGenerationJobId(record.id))throw Error('작업 ID를 확인할 수 없습니다.');location.assign(form+'?restore='+encodeURIComponent(record.id));}
  return <article className="vace-page generator-page-common vace-standalone"><h1>MiniMax H3 이미지 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={form}>생성기 입력폼</a><a href={MINI_MAX_IMAGE_HISTORY} aria-current="page">생성기 생성이력</a>{building && <a href="/management/frame/building-editor/">건물 검수 페이지</a>}</nav><p>일반 이미지와 건물 이미지의 생성이력을 함께 표시합니다.</p><MiniMaxImageHistory job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readJob} restore={restore} historyRef={historyRef} resultRef={resultRef}/></article>;
}
