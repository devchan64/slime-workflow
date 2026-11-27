import InvalidHistoryJobNotice from './InvalidHistoryJobNotice.jsx';
import React,{useEffect,useRef,useState} from 'react';
import MiniMaxVideoHistory from './MiniMaxVideoHistory.jsx';
import {untilAborted} from './managementCommand.js';
import {validVideoJobId} from './videoJobId.mjs';

const services={'minimax-h3-i2v':'영상 생성','minimax-h3-ref2va':'영상 편집'};
export const MINI_MAX_VIDEO_HISTORY='/management/frame/minimax-h3-video-history/';
export function miniMaxVideoHistoryUrl(service,id,session=''){const q=new URLSearchParams({service});if(session)q.set('session',session);if(validVideoJobId(id))q.set('job',id);return MINI_MAX_VIDEO_HISTORY+'?'+q;}
export default function MiniMaxVideoHistoryPage({service:legacyService}={}){
  const q=new URLSearchParams(location.search),service=legacyService || q.get('service')||'minimax-h3-i2v',session=q.get('session')||'',valid=Object.hasOwn(services,service);
  const [job,setJob]=useState(validVideoJobId(q.get('job'))?q.get('job'):''),[revision,setRevision]=useState(0),[notice,setNotice]=useState('');
  const historyRef=useRef(null),resultRef=useRef(null);
  useEffect(()=>{document.title='MiniMax 영상 생성이력';const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;},[service]);
  async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/'+service+'-input/'+encodeURIComponent(id),{signal,cache:'no-store'}),signal);if(!response.ok)throw Error('저장된 입력 또는 원본 미디어를 확인할 수 없습니다.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record.request || typeof record.request!=='object')throw Error('저장 입력 형식을 확인할 수 없습니다.');return record;}
  function restore(_request,record){if(!validVideoJobId(record.id))throw Error('작업 ID를 확인하세요.');const params=new URLSearchParams({restore:record.id});if(session)params.set('session',session);location.assign('/management/frame/'+service+'-generator/?'+params);}
  if(!valid)return <article><h1>MiniMax 영상 생성이력</h1><p role="alert">지원하지 않는 생성기입니다.</p></article>;
  return <article className="vace-page generator-page-common vace-standalone"><h1>MiniMax 영상 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/'+service+'-generator/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span></nav><InvalidHistoryJobNotice/><label>생성기 <select value={service} onChange={event=>location.assign(miniMaxVideoHistoryUrl(event.target.value,undefined,session))}>{Object.entries(services).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label><p>선택한 생성기의 이력만 표시합니다.</p>{notice && <p role="status">{notice}</p>}<MiniMaxVideoHistory service={service} job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readJob} restore={restore} historyRef={historyRef} resultRef={resultRef} onNotice={setNotice} allowPriority={service==='minimax-h3-i2v'} resultLabel="선택한 영상 작업 결과"/></article>;
}
