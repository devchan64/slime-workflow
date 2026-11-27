import StandaloneGeneratorHistory from "./StandaloneGeneratorHistory.jsx";
import React,{useEffect} from 'react';
import GeneratorJobResult from './GeneratorJobResult.jsx';
import {untilAborted} from './managementCommand.js';
import {validGenerationJobId} from './generationJobId.mjs';

export const DWPOSE_HISTORY='/management/frame/dwpose-history/';
export function dwposeHistoryUrl(session,id){const q=new URLSearchParams();if(session)q.set('session',session);if(validGenerationJobId(id))q.set('job',id);return DWPOSE_HISTORY+(q.size?'?'+q:'');}
export default function DwposeHistoryPage(){
  const q=new URLSearchParams(location.search),session=q.get('session')||'';
  async function readJob(id,{signal}={}){
    const response=await untilAborted(fetch('/management/assistant/dwpose-input/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);
    if(!response.ok)throw Error('저장된 DWPose 입력을 불러올 수 없습니다.');const hands=response.headers.get('X-Pose-Hands'),face=response.headers.get('X-Pose-Face');
    if(!['true','false'].includes(hands) || !['true','false'].includes(face))throw Error('저장된 포즈 옵션을 확인할 수 없습니다.');
    const blob=await untilAborted(response.blob(),signal);const image=await untilAborted(createImageBitmap(blob),signal);const valid=image.width===832 && image.height===480;image.close();if(!valid)throw Error('저장된 PNG를 확인할 수 없습니다.');
    const data=await untilAborted(new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('저장된 PNG를 읽을 수 없습니다.'));reader.readAsDataURL(blob);}),signal);
    return {id,request:{pose_include_hands:hands==='true',pose_include_face:face==='true',images:[data]}};
  }
  function restore(_request,record){if(!validGenerationJobId(record.id))throw Error('작업 ID를 확인하세요.');const params=new URLSearchParams({restore:record.id});if(session)params.set('session',session);location.assign('/management/frame/dwpose-generator/?'+params);}
  useEffect(()=>{document.title='DWPose 생성이력';},[]);
  return <article className="dwpose-page dwpose-standalone generator-page-common"><h1>DWPose 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/dwpose-generator/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span></nav><StandaloneGeneratorHistory service="dwpose" readJob={readJob} restore={restore} renderResult={(id,{resultRef,cleaned})=><section ref={resultRef} tabIndex={-1} aria-label="선택한 DWPose 작업 결과"><GeneratorJobResult selectionControls job={id} service="dwpose" readJobWithSignal={readJob} controls={false} onDeleted={cleaned}/></section>}/></article>;
}
