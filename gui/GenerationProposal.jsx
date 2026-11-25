import React,{useEffect,useRef,useState} from 'react';
import {readProposalPreview} from './readProposalPreview.mjs';
import {readGenerationProposal} from './generationProposal.mjs';
import {useMinimaxReportReceipt,MinimaxReportStatus,PreparedMinimaxForm} from './useMinimaxReportReceipt.jsx';
import {useVideoDelegationReceipt} from './useVideoDelegationReceipt.js';
import {managementCommand,untilAborted} from './managementCommand.js';

const names={audio:'오디오',video:'영상',writer:'작가'};
const routes={'music-heartmula':'music-heartmula','sfx-dasheng-audiogen':'sfx-dasheng-audiogen',dwpose:'dwpose-generator','wan22-animate2':'wan22-animate2-generator','wan22-fun-control':'wan22-fun-control-generator','wan22-vace':'wan22-vace-generator','wan22-i2v':'wan22-i2v-generator','minimax-h3-i2v':'minimax-h3-i2v-generator','minimax-h3-ref2va':'minimax-h3-ref2va-generator','wan21-t2v':'wan21-t2v-generator','wan21-i2v':'wan21-i2v-generator','writer-agent':'writer-agent'};
export function GenerationProposalReview({kind,proposal,session,job,snapshot,offset}){
  const service=kind==='writer'?'writer-agent':proposal.service,request=kind==='audio'?proposal.request:proposal;
  const minimaxReceipt=useMinimaxReportReceipt(kind==='video' && service==='minimax-h3-i2v' ? {session,job} : null,'minimax-h3-i2v');
  const editReceipt=useVideoDelegationReceipt(kind==='video' && service==='minimax-h3-ref2va' ? {session,job} : null,'minimax-h3-ref2va');
  const route=routes[service];
  const transfer=kind==='audio' || kind==='writer' || (kind==='video' && (service==='wan22-vace' || (service==='minimax-h3-ref2va' && proposal.mode==='video_edit') || (['wan22-i2v','minimax-h3-i2v'].includes(service) && proposal.mode==='first_frame') || (service==='wan21-t2v' && proposal.mode==='text') || (service==='wan21-i2v' && proposal.mode==='first_frame') || (service==='wan22-fun-control' && proposal.mode==='pose_video')));
  if(kind==='video' && service==='minimax-h3-i2v')return <><p>이 제안에 연결된 MiniMax 영상 접수폼이 아직 확인되지 않았습니다. 준비된 폼은 이 대화의 우측 패널에서 확인할 수 있습니다.</p><MinimaxReportStatus receipt={minimaxReceipt}/></>;
  return <><p>{service}{kind==='video' && ' · 입력 방식 '+proposal.mode}{kind==='writer' && ' · 요청 방식 '+proposal.mode}</p>
    {proposal.selection_reason && <p>선택 이유: {proposal.selection_reason}</p>}
    {kind==='video' && service==='minimax-h3-i2v' && <MinimaxReportStatus receipt={minimaxReceipt}/>}
    {kind==='video' && service==='minimax-h3-ref2va' && <div><p role="status">{editReceipt.state==='accepted' ? '접수된 작업 '+editReceipt.job : editReceipt.state==='editing' ? '이 제안은 아직 접수되지 않았습니다.' : editReceipt.state==='checking' ? '접수 상태 확인 중' : '접수 상태를 확인하세요.'}</p><button type="button" onClick={editReceipt.refresh}>접수 상태 새로고침</button></div>}
    {request.prompt && <><strong>요청 내용</strong><p style={{whiteSpace:'pre-wrap'}}>{request.prompt}</p></>}
    {kind==='audio' && <><p>시드 {request.seed}{request.duration_seconds!=null && ' · 최대 '+request.duration_seconds+'초'} · 반복 요청 {request.loop_request?'켜짐':'꺼짐'}</p>{request.lyrics && <><strong>가사</strong><p style={{whiteSpace:'pre-wrap'}}>{request.lyrics}</p></>}</>}
    {service!=='minimax-h3-ref2va' && <p>{kind==='video' && service==='minimax-h3-i2v' && minimaxReceipt.state==='accepted' ? '이 제안은 이미 접수되었습니다.' : kind==='video' && service==='minimax-h3-i2v' && minimaxReceipt.state!=='editing' ? '접수 상태를 확인하세요.' : <>아직 접수되지 않았습니다. {service==='wan22-animate2' ? '현재 생성 가능 상태를 확인하세요.' : '도구에서 입력과 필요한 첨부를 확인한 뒤 접수하세요.'}</>}</p>}
    {kind==='video' && service==='wan22-fun-control' && !transfer && <p>현재 생성 폼은 처리된 포즈 영상 입력만 지원하므로 이 입력 방식은 그대로 접수할 수 없습니다.</p>}
    {kind==='video' && service==='wan22-animate2' && <p>도구에서 참조 이미지와 동작 영상을 선택하고 생성 설정을 확인하세요.</p>}
    {route && <a href={'/management/frame/'+route+'/?'+new URLSearchParams({session,...(transfer?{proposal_job:job,proposal_snapshot:snapshot,proposal_offset:String(offset)}:{})})}>{transfer?'제안 입력으로 도구 열기':'해당 도구 열기'}</a>}
  </>;
}
export default function GenerationProposal({session,job,snapshot,offset,kind,onOpenForm}){
  return <GenerationProposalForSelection key={JSON.stringify([session,job,snapshot,offset,kind])} session={session} job={job} snapshot={snapshot} offset={offset} kind={kind} onOpenForm={onOpenForm}/>;
}
function GenerationProposalForSelection({session,job,snapshot,offset,kind,onOpenForm}){
  const [proposal,setProposal]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [prepared,setPrepared]=useState(null);
  const receipt=useMinimaxReportReceipt(kind==='video' && prepared ? {session,job} : null,'minimax-h3-i2v');
  const buttonRef=useRef(null),request=useRef(null);useEffect(()=>()=>request.current?.abort(),[]);
  useEffect(()=>{
    if(kind!=='video')return;
    let active=true,timer,attempts=0;const controller=new AbortController();
    async function refresh(){
      attempts++;
      try{
        const listed=await untilAborted(managementCommand('hermes-agent','hermes-minimax-form-list',{session_id:session},{signal:controller.signal}),controller.signal);
        if(!Array.isArray(listed?.forms))throw new Error('접수폼 목록을 확인할 수 없습니다.');
        const matches=listed.forms.filter(row=>row.source_job_id===job && row.service==='minimax-h3-i2v');
        if(matches.length>1)throw new Error('같은 제안에 연결된 접수폼이 여러 개입니다.');
        if(!matches.length)return;
        const checked=await readGenerationProposal(managementCommand,{session,job,snapshot,offset,kind},{signal:controller.signal});
        if(active && checked.service==='minimax-h3-i2v'){setPrepared(matches[0]);setError('');}
      }catch(problem){if(active && problem.name!=='AbortError')setError(problem.message || '접수폼 상태를 확인할 수 없습니다.');}
      finally{if(active)timer=setTimeout(refresh,attempts<12?5000:60000);}
    }
    refresh();
    return()=>{active=false;clearTimeout(timer);controller.abort();};
  },[session,job,snapshot,offset,kind]);
  async function inspect(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError('');setProposal(null);
    try{setProposal(await readProposalPreview(readGenerationProposal,[{session,job,snapshot,offset,kind}],controller.signal));}
    catch(problem){if(!controller.signal.aborted || timedOut)setError(timedOut ? '생성 제안 조회 시간이 초과됐습니다. 다시 확인하세요.' : problem.message);}
    finally{clearTimeout(timeout);if(request.current===controller)request.current=null;if(!controller.signal.aborted || timedOut){setBusy(false);requestAnimationFrame(()=>{if(document.activeElement===document.body && buttonRef.current?.isConnected && !buttonRef.current.disabled)buttonRef.current.focus();});}}
  }
  return <section aria-label={names[kind]+' 제안'}>{prepared ? <><PreparedMinimaxForm form={prepared} label="영상" onOpenForm={onOpenForm} receipt={receipt}/></> : <><button ref={buttonRef} type="button" disabled={busy} onClick={inspect}>{names[kind]} 제안 확인</button>{busy && <p role="status">생성 제안을 조회하고 있습니다.</p>}{proposal && <GenerationProposalReview kind={kind} proposal={proposal} session={session} job={job} snapshot={snapshot} offset={offset}/>}</>}{error && <p role="alert">{error}</p>}</section>;
}
