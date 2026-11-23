import React,{useRef,useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readGenerationProposal} from './generationProposal.mjs';

const names={audio:'오디오',video:'영상',writer:'작가'};
const routes={'music-heartmula':'music-heartmula','sfx-dasheng-audiogen':'sfx-dasheng-audiogen',dwpose:'dwpose-generator','wan22-animate2':'wan22-animate2-generator','wan22-fun-control':'wan22-fun-control-generator','wan22-vace':'wan22-vace-generator','wan22-i2v':'wan22-i2v-generator','wan21-t2v':'wan21-t2v-generator','wan21-i2v':'wan21-i2v-generator','writer-agent':'writer-agent'};
export function GenerationProposalReview({kind,proposal,session,job,snapshot,offset}){
  const service=kind==='writer'?'writer-agent':proposal.service,request=kind==='audio'?proposal.request:proposal;
  const route=routes[service];
  const transfer=kind==='audio' || kind==='writer' || (kind==='video' && (service==='wan22-vace' || (service==='wan22-i2v' && proposal.mode==='first_frame') || (service==='wan21-t2v' && proposal.mode==='text') || (service==='wan21-i2v' && proposal.mode==='first_frame') || (service==='wan22-fun-control' && proposal.mode==='pose_video')));
  return <><p>{service}{kind==='video' && ' · 입력 방식 '+proposal.mode}{kind==='writer' && ' · 요청 방식 '+proposal.mode}</p>
    {request.prompt && <><strong>요청 내용</strong><p style={{whiteSpace:'pre-wrap'}}>{request.prompt}</p></>}
    {kind==='audio' && <><p>시드 {request.seed}{request.duration_seconds!=null && ' · 최대 '+request.duration_seconds+'초'} · 반복 요청 {request.loop_request?'켜짐':'꺼짐'}</p>{request.lyrics && <><strong>가사</strong><p style={{whiteSpace:'pre-wrap'}}>{request.lyrics}</p></>}</>}
    <p>아직 접수되지 않았습니다. {service==='wan22-animate2' ? '현재 생성 가능 상태를 확인하세요.' : '도구에서 입력과 필요한 첨부를 확인한 뒤 접수하세요.'}</p>
    {kind==='video' && service==='wan22-fun-control' && !transfer && <p>현재 생성 폼은 처리된 포즈 영상 입력만 지원하므로 이 입력 방식은 그대로 접수할 수 없습니다.</p>}
    {kind==='video' && service==='wan22-animate2' && <p>도구에서 참조 이미지와 동작 영상을 선택하고 생성 설정을 확인하세요.</p>}
    {route && <a href={'/management/frame/'+route+'/?'+new URLSearchParams({session,...(transfer?{proposal_job:job,proposal_snapshot:snapshot,proposal_offset:String(offset)}:{})})}>{transfer?'제안 입력으로 도구 열기':'해당 도구 열기'}</a>}
  </>;
}
export default function GenerationProposal({session,job,snapshot,offset,kind}){
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const buttonRef=useRef(null);
  async function inspect(){setBusy(true);setError('');setProposal(null);try{setProposal(await readGenerationProposal(managementCommand,{session,job,snapshot,offset,kind}));}catch(problem){setError(problem.message);}finally{setBusy(false);requestAnimationFrame(()=>{if(document.activeElement===document.body && buttonRef.current?.isConnected && !buttonRef.current.disabled)buttonRef.current.focus();});}}
  return <section aria-label={names[kind]+' 제안'}><button ref={buttonRef} type="button" disabled={busy} onClick={inspect}>{names[kind]} 제안 확인</button>{error && <p role="alert">{error}</p>}{proposal && <GenerationProposalReview kind={kind} proposal={proposal} session={session} job={job} snapshot={snapshot} offset={offset}/>}</section>;
}
