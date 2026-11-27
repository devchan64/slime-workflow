import InvalidHistoryJobNotice from './InvalidHistoryJobNotice.jsx';
import React,{useEffect,useRef,useState} from 'react';
import GeneratorHistory from './GeneratorHistory.jsx';
import GeneratorJobResult from './GeneratorJobResult.jsx';
import {untilAborted} from './managementCommand.js';
import {validGenerationJobId} from './generationJobId.mjs';

export const FLUX_HISTORY='/management/frame/flux-image-history/';
export const FLUX_HISTORY_SERVICES=Object.freeze({'flux-image':'일반 이미지','flux-character':'캐릭터','flux-mannequin':'마네킨','flux-billboard':'빌보드','flux-prop':'소품','flux-vegetation':'식생','flux-building':'건물','flux-seamless':'심리스 타일','flux-expression':'표정'});
export function fluxHistoryUrl(service,id,session=''){if(!Object.hasOwn(FLUX_HISTORY_SERVICES,service))throw Error('생성기를 확인하세요.');const q=new URLSearchParams({service});if(session)q.set('session',session);if(validGenerationJobId(id))q.set('job',id);return FLUX_HISTORY+'?'+q+(validGenerationJobId(id)?'#job-result':'');}
export function FluxHistoryPanel({service,job,setJob,revision,setRevision,readJob,restore,historyRef,resultRef,onNotice,disabled=false,disabledHelpId}){
  useEffect(()=>{const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;},[historyRef,service]);
  function cleaned(message){setJob('');onNotice?.(message);setRevision(value=>value+1);}
  return <><fieldset ref={historyRef} className="flux-history-controls" disabled={disabled} aria-describedby={disabled ? disabledHelpId : undefined}><legend className="generator-visually-hidden">생성 이력</legend><GeneratorHistory card allowPriority toggleResult onSelectedDeleted={(id,message)=>{if(job===id)setJob('');onNotice?.(message);setRevision(value=>value+1);}} key={service+':'+revision} service={service} readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob('')} restore={restore} renderResult={id=><section id="job-result" ref={resultRef} tabIndex={-1} aria-label="선택한 FLUX 작업 결과"><GeneratorJobResult selectionControls job={id} kind="flux" service={service} readJobWithSignal={readJob} onDeleted={cleaned}/></section>}/></fieldset><GeneratorJobResult selectionControls job="" kind="flux" service={service} onDeleted={cleaned}/></>;
}
export default function FluxHistoryPage({service:legacyService}={}){
  const params=new URLSearchParams(location.search), requested=legacyService || params.get('service') || 'flux-image',session=params.get('session') || '';
  const valid=Object.hasOwn(FLUX_HISTORY_SERVICES,requested),service=valid ? requested : '';
  const [job,setJob]=useState(validGenerationJobId(params.get('job')) ? params.get('job') : ''),[revision,setRevision]=useState(0),[notice,setNotice]=useState('');
  const historyRef=useRef(null),resultRef=useRef(null);
  useEffect(()=>{document.title='FLUX 이미지 생성이력';},[]);
  async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/flux-image-input/'+encodeURIComponent(id)+'?service='+encodeURIComponent(service),{signal,cache:'no-store'}),signal);let record;try{record=await untilAborted(response.json(),signal);}catch(error){signal?.throwIfAborted();throw Error('저장 입력 형식을 확인할 수 없습니다.');}if(!response.ok)throw Error(record?.detail || '저장 입력을 확인할 수 없습니다.');if(record?.id!==id || !record.request || typeof record.request!=='object' || !Array.isArray(record.images) || record.images.some(image=>typeof image!=='string'))throw Error('저장 입력 형식을 확인할 수 없습니다.');return {...record,request:{...record.request,images:record.images}};}
  function restore(_request,record){if(!validGenerationJobId(record.id))throw Error('작업 ID를 확인하세요.');const q=new URLSearchParams({restore:record.id});if(session)q.set('session',session);location.assign('/management/frame/'+service+'-generator/?'+q);}
  if(!valid)return <article><h1>FLUX 이미지 생성이력</h1><p role="alert">지원하지 않는 생성기입니다. 입력 페이지에서 다시 이동하세요.</p></article>;
  return <article className="flux-page generator-page-common flux-standalone"><h1>FLUX 이미지 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/'+service+'-generator/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span>{service==='flux-building' && <a href="/management/frame/building-editor/">건물 검수 페이지</a>}{['flux-billboard','flux-prop','flux-vegetation'].includes(service) && <a href="/management/frame/asset-editor/">빌보드 검수 페이지</a>}</nav><label>생성기 <select value={service} onChange={event=>location.assign(fluxHistoryUrl(event.target.value,undefined,session))}>{Object.entries(FLUX_HISTORY_SERVICES).map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label><p>선택한 생성기의 작업만 표시합니다. 이력과 삭제 범위는 해당 생성기에 한정됩니다.</p><InvalidHistoryJobNotice/>{notice && <p role="status">{notice}</p>}<FluxHistoryPanel service={service} job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readJob} restore={restore} historyRef={historyRef} resultRef={resultRef} onNotice={setNotice}/></article>;
}
