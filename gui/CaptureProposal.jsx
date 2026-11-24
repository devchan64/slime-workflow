import React,{useEffect,useRef,useState} from 'react';
import {readProposalPreview} from './readProposalPreview.mjs';
import {readCaptureProposal} from './captureProposal.mjs';

const labels={map:'맵 ID',show_character:'캐릭터 표시',show_safe_boundary:'안전 경계 표시',edges:'경계 표시',tile_edges:'타일 경계',ground:'바닥',zoom:'배율',column:'열',row:'행',rotation:'회전',outline:'외곽선',outline_width:'외곽선 폭',rim:'림 조명',shadow:'그림자',shadow_profile:'그림자 설정',contrast:'대비',saturation_reduced:'채도 감소',brightness_reduced:'밝기 감소',width:'너비',height:'높이'};
const values={paving:'포장',grass:'풀','meadow-road':'초원 길',baseline:'기본',contrast:'대비',broad:'넓게',original:'원본',soft:'부드럽게'};
export function CaptureProposalReview({value,session}){
  const {proposal,registration}=value, map=proposal.service==='map-review';
  const href=map && registration.status==='registered' ? '/management/frame/map-review/?'+new URLSearchParams({map:proposal.settings.map,townPage:'1',session}) : null;
  return <><h4>{map?'맵 검수 캡처':'캐릭터 검수 캡처'} 제안</h4><dl>{Object.entries(proposal.settings).map(([key,value])=><React.Fragment key={key}><dt>{labels[key] || key}</dt><dd>{typeof value==='boolean' ? (value?'켜짐':'꺼짐') : (values[value] || String(value))}</dd></React.Fragment>)}</dl>
    {map ? <p>{registration.status==='registered'?'등록된 맵 · 조회 시점 기준':registration.status==='not_registered'?'등록 맵 목록에 없음':'맵 등록 여부 확인 불가'}</p> : <p>캐릭터 표현 검수 화면은 폐기되었습니다. 기존 작업과 결과는 원 서비스에서 확인하세요.</p>}
    <p>대화에서 캡처 실행은 지원하지 않습니다.{map && ' 맵 화면에서 직접 확인할 수 있으며 GPU를 사용할 수 있습니다.'}</p>
    {href && <a href={href}>맵 검수 화면 열기</a>}
  </>;
}
export default function CaptureProposal({session,job,snapshot,offset}){
  return <CaptureProposalForSelection key={JSON.stringify([session,job,snapshot,offset])} session={session} job={job} snapshot={snapshot} offset={offset}/>;
}
function CaptureProposalForSelection({session,job,snapshot,offset}){
  const [value,setValue]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const request=useRef(null);useEffect(()=>()=>request.current?.abort(),[]);
  async function inspect(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError('');setValue(null);
    try{setValue(await readProposalPreview(readCaptureProposal,[{session,job,snapshot,offset}],controller.signal));}
    catch(problem){if(!controller.signal.aborted || timedOut)setError(timedOut ? '캡처 설정 조회 시간이 초과됐습니다. 다시 확인하세요.' : problem.message);}
    finally{clearTimeout(timeout);if(request.current===controller)request.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  return <section aria-label="캡처 제안"><button type="button" disabled={busy} onClick={inspect}>캡처 설정 확인</button>{busy && <p role="status">캡처 설정을 조회하고 있습니다.</p>}{error && <p role="alert">{error}</p>}{value && <CaptureProposalReview value={value} session={session}/>}</section>;
}
