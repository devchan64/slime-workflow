import StandaloneGeneratorHistory from "./StandaloneGeneratorHistory.jsx";
import React,{useEffect} from 'react';
import SavedGeneratorInputs from './SavedGeneratorInputs.jsx';
import KimodoFrames from './KimodoFrames.jsx';
import {untilAborted} from './managementCommand.js';
import {validGenerationJobId} from './generationJobId.mjs';
import {kimodoHistoryRequest} from './kimodoHistoryRequest.mjs';

export const KIMODO_HISTORY='/management/frame/kimodo-history/';
export function kimodoHistoryUrl(session,id){const q=new URLSearchParams();if(session)q.set('session',session);if(validGenerationJobId(id))q.set('job',id);return KIMODO_HISTORY+(q.size?'?'+q:'');}
export default function KimodoHistoryPage(){
  const q=new URLSearchParams(location.search),session=q.get('session')||'';
  const conversation='/management/frame/hermes-agent/'+(session?'?'+new URLSearchParams({session}):'');
  function choose(label,value){const key='hermes-draft-'+session;sessionStorage.setItem(key,[sessionStorage.getItem(key),label+' '+value].filter(Boolean).join('\n'));location.assign(conversation);}
  async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/kimodo-input/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);if(!response.ok)throw Error('저장된 Kimodo 입력을 확인할 수 없습니다.');const saved=await untilAborted(response.json(),signal);return {id,request:kimodoHistoryRequest(saved)};}
  function restore(_request,record){if(!validGenerationJobId(record.id))throw Error('작업 ID를 확인하세요.');const params=new URLSearchParams({restore:record.id});if(session)params.set('session',session);location.assign('/management/frame/kimodo-generator/?'+params);}
  useEffect(()=>{document.title='Kimodo 생성이력';},[]);
  return <main className="single-generator-shell generator-page-standalone-shell"><article className="single-generator-page generator-page-common"><h1>Kimodo 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/kimodo-generator/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span></nav><StandaloneGeneratorHistory service="kimodo" readJob={readJob} restore={restore} renderResult={(id,{resultRef,cleaned})=><section ref={resultRef} tabIndex={-1} aria-label="선택한 Kimodo 작업 결과"><button type="button" onClick={()=>choose('kimodo 작업',id)}>선택 작업을 대화 입력에 추가</button><SavedGeneratorInputs id={id} service="kimodo" readJobWithSignal={readJob}/><KimodoFrames key={id} id={id} choose={choose} onDeleted={cleaned} selectionControls/></section>}/></article></main>;
}
