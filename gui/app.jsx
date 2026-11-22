import {classifyQueueUpdate,validChatQueue} from "./chatQueueUpdate.mjs";
import {validSessionViewPage} from "./sessionViewPage.mjs";
import {validSessionListPage} from "./sessionListPage.mjs";
import SeedProposal from "./SeedProposal.jsx";
import {formatActivityOutput} from "./formatActivityOutput.mjs";
import {matchesLiveInstructionReceipt,matchesLiveInstructionRecovery,validLiveInstructionRows} from "./liveInstructionReceipt.mjs";
import {Command} from "cmdk";
import QwenArchive from "./QwenArchive.jsx";
import KimodoPage from "./KimodoPage.jsx";
import KimodoProposal from "./KimodoProposal.jsx";
import CaptureProposal from "./CaptureProposal.jsx";
import GenerationProposal from "./GenerationProposal.jsx";
import KimodoFrames from "./KimodoFrames.jsx";
import BillboardCatalog from "./BillboardCatalog.jsx";
import SpriteSheetEditor from "./SpriteSheetEditor.jsx";
import KeyframeCatalog from "./KeyframeCatalog.jsx";
import ContentDatabaseStatus from "./ContentDatabaseStatus.jsx";
import EffectEditor from "./EffectEditor.jsx";
import BuildingEditor from "./BuildingEditor.jsx";
import MapReview from "./MapReview.jsx";
import BattlefieldReview from "./BattlefieldReview.jsx";
import FunControlPage from "./FunControlPage.jsx";
import ConversationVideoForm from "./ConversationVideoForm.jsx";
import VacePage from "./VacePage.jsx";
import AnimatePage from "./AnimatePage.jsx";
import WriterPage from "./WriterPage.jsx";
import FluxImagePage from "./FluxImagePage.jsx";
import FluxProposal from "./FluxProposal.jsx";
import BuildingProposal from "./BuildingProposal.jsx";
import BillboardProposal from "./BillboardProposal.jsx";
import SpriteProposal from "./SpriteProposal.jsx";
import EffectProposal from "./EffectProposal.jsx";
import CityProposal from "./CityProposal.jsx";
import FieldProposal from "./FieldProposal.jsx";
import SoundEffectPage, {HeartmulaPage} from "./SoundEffectPage.jsx";
import DwposePage from "./DwposePage.jsx";
import SourceHistory from "./SourceHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import {videoLookupSuggestion} from "./videoLookupSuggestion.mjs";
import ExpressionCatalog from "./ExpressionCatalog.jsx";
import AnchorHistory from "./AnchorHistory.jsx";
import ServiceRegistry from "./ServiceRegistry.jsx";
import OperationsJobs from "./OperationsJobs.jsx";
import CapabilitySearch from "./CapabilitySearch.jsx";
import ModelPage from "./ModelPage.jsx";
import TranslationPage from "./TranslationPage.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResidentModelStatus from "./ResidentModelStatus.jsx";
import CopyTextButton from "./CopyTextButton.jsx";
import ResultTable from "./ResultTable.jsx";
import WorldMap from "./WorldMap.jsx";
import GpuPanel from "./GpuPanel.jsx";
import GpuHandoffHistory from "./GpuHandoffHistory.jsx";
import QueuePanel from "./QueuePanel.jsx";
import JobIdentifier from "./JobIdentifier.jsx";

import React, {useEffect, useLayoutEffect, useMemo, useRef, useState} from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {createRoot} from "react-dom/client";
import {AssistantRuntimeProvider, ThreadPrimitive, MessagePrimitive, useAuiState, useExternalStoreRuntime} from "@assistant-ui/react";

const embeddedGenerators={
  "wan22-vace-generator":VacePage,"wan22-animate2-generator":AnimatePage,
  "sfx-dasheng-audiogen":SoundEffectPage,"music-heartmula":HeartmulaPage,
  "dwpose-generator":DwposePage,"prompt-translation":TranslationPage,"writer-agent":WriterPage,
};
for(const name of ["image","building","mannequin","billboard","prop","vegetation","seamless","character","expression"]){
  const service="flux-"+name;
  embeddedGenerators[service+"-generator"]=props=><FluxImagePage {...props} serviceOverride={service}/>;
}
const base = "/management/assistant/";
const CONVERSATION_PAGE_SIZE=6;
const id = () => crypto.randomUUID().replaceAll("-", "");
const query = () => new URLSearchParams(location.search);
function call(command, payload = {}, options = {}) {
  return managementCommand("hermes-agent", "hermes-"+command, payload, options);
}
function callUntilAborted(command,payload,signal){
  return untilAborted(call(command,payload,{signal}),signal);
}
function messagesFrom(view) {
  const records = view.messages || [];
  const start = (view.message_count ?? records.length) - (view.offset || 0) - records.length;
  return records.flatMap((m,index) => {
    const job = m.job || {}, key=m.id || m.request_id || (view.id + "-" + (start + index));
    if(m.form_id)return [{id:m.form_id,role:"user",content:m.text,metadata:{custom:{formId:m.form_id,session:view.id}}}];
    const activity = job.tool_activity || {};
    const page = activity.source_history_page;
    const table = activity.history_table || (page && {
      title:page.service+" 생성 이력", summary:"전체 "+page.total+"건 · 이번 조회 "+page.rows.length+"건",
      columns:["작업 ID","상태"], rows:page.rows.map(row=>[row.id,row.status])
    });
    const answer = job.final_response || "";
    const kimodoProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_KIMODO_PROPOSAL");
    const generationProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated ? ["audio","video","writer"].find(kind=>answer.includes("HERMES_"+kind.toUpperCase()+"_PROPOSAL")) : null;
    const captureProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_CAPTURE_PROPOSAL");
    const fluxProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_FLUX_PROPOSAL");
    const buildingProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_BUILDING_PROPOSAL");
    const billboardProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_BILLBOARD_PROPOSAL");
    const spriteProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_SPRITE_PROPOSAL");
    const effectProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_EFFECT_PROPOSAL");
    const cityProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_CITY_PROPOSAL");
    const fieldProposal=m.session_job_unique===true && job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_FIELD_PROPOSAL");
    let displayAnswer=kimodoProposal ? answer.replace(/\n*HERMES_KIMODO_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_KIMODO_PROPOSAL\s*$/, "") : fluxProposal ? answer.replace(/\n*HERMES_FLUX_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_FLUX_PROPOSAL\s*$/, "") : buildingProposal ? answer.replace(/\n*HERMES_BUILDING_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_BUILDING_PROPOSAL\s*$/, "") : billboardProposal ? answer.replace(/\n*HERMES_BILLBOARD_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_BILLBOARD_PROPOSAL\s*$/, "") : spriteProposal ? answer.replace(/\n*HERMES_SPRITE_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_SPRITE_PROPOSAL\s*$/, "") : effectProposal ? answer.replace(/\n*HERMES_EFFECT_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_EFFECT_PROPOSAL\s*$/, "") : cityProposal ? answer.replace(/\n*HERMES_CITY_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_CITY_PROPOSAL\s*$/, "") : fieldProposal ? answer.replace(/\n*HERMES_FIELD_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_FIELD_PROPOSAL\s*$/, "") : answer;
    if(captureProposal)displayAnswer=displayAnswer.replace(/\n*HERMES_CAPTURE_PROPOSAL\s*\n[\s\S]*?\nEND_HERMES_CAPTURE_PROPOSAL\s*$/, "");
    if(generationProposal){const marker=generationProposal.toUpperCase();displayAnswer=displayAnswer.replace(new RegExp("\\n*HERMES_"+marker+"_PROPOSAL\\s*\\n[\\s\\S]*?\\nEND_HERMES_"+marker+"_PROPOSAL\\s*$"), "");}
    const suggestion = !activity.video_source && job.status?.status==="completed" && !job.final_response_truncated ? videoLookupSuggestion(answer,m.text) : null;
    const showAnswer = !table || (answer !== activity.source_history_summary && !activity.history_table_is_answer);
    return [{id:key+"-user",role:"user",content:m.text},
      {id:key+"-answer",role:"assistant",content:showAnswer ? (suggestion ? "작업 결과 조회가 필요합니다." : displayAnswer) : "",metadata:{custom:{
        videoSuggestion:suggestion,
        status:job.status?.status || "접수 확인 중",kimodoRequest:/kimodo|키모도|김도/i.test(m.text || ""),queueMessage:job.status?.status==="queued" && typeof job.status.message==="string" ? job.status.message : "",session:view.id,job:m.job_id,sessionSnapshot:view.snapshot,sessionOffset:view.offset || 0,seedProposal:m.seed_form_proposal,kimodoProposal,captureProposal,generationProposal,fluxProposal,buildingProposal,billboardProposal,spriteProposal,effectProposal,cityProposal,fieldProposal,activity,table}}}];
  });
}
function jobLink(id,session){
  const params=new URLSearchParams({panel:"jobs",job:id});
  if(session)params.set("session",session);
  return "/management/frame/hermes-agent/?"+params;
}
const statusLabels={completed:"완료",failed:"실패",running:"실행 중",queued:"대기 중",pending:"접수 확인 중",unknown:"확인 불가",cancelled:"취소",canceled:"취소"};
function SuggestedVideoResult({suggestion,onReuse}){
  const [open,setOpen]=useState(false),[service,setService]=useState(suggestion.service);
  const choices={"wan22-fun-control":"Wan Fun Control","wan22-vace":"Wan VACE","wan22-animate2":"Wan Animate-2",dwpose:"DWPose",kimodo:"Kimodo"};
  return <section aria-label="작업 결과 조회 안내"><p>헤르메스가 조회 명령만 제시해 결과는 아직 확인되지 않았습니다. 제안된 생성기가 맞는지 확인하세요.</p>
    <label>조회할 생성기 <select value={service} onChange={event=>{setService(event.target.value);setOpen(false);}}>{Object.entries(choices).map(([value,label])=><option value={value} key={value}>{label}</option>)}</select></label>
    <button type="button" onClick={()=>setOpen(value=>!value)}>{open ? "결과 닫기" : "작업 상태와 결과 조회"}</button>{open && (service==="kimodo" ? <KimodoFrames key={service} id={suggestion.job_id} selectionControls/> : <MediaJobResult key={service} kind="video" folderLink service={service} id={suggestion.job_id} onReuse={service==="wan22-fun-control" ? onReuse : undefined}/>)}</section>;
}
const HistoryRoutes=React.createContext({});
const ProposalActions=React.createContext(null);
function ChatQueuePrompt({text}){
  const [expanded,setExpanded]=useState(false);
  const prompt=typeof text==="string" ? text : "요청 내용을 확인할 수 없습니다.";
  const long=prompt.length>120 || prompt.split("\n").length>4;
  return <><p tabIndex={long && expanded ? 0 : undefined} role={long && expanded ? "region" : undefined} aria-label={long && expanded ? "요청 전체 내용" : undefined} className={long ? expanded ? "chat-queue-prompt-expanded" : "chat-queue-prompt-preview" : undefined}>{prompt}</p>{long && <button type="button" aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded ? "요청 접기" : "요청 전체 보기"}</button>}</>;
}
function ChatQueueItem({item,onChange,onEditing,disableEdit,savedEdit,unavailable,mutationLocked}){
  const [editing,setEditing]=useState(Boolean(savedEdit)),[text,setText]=useState(savedEdit?.text ?? item.prompt),[editRevision,setEditRevision]=useState(savedEdit?.revision ?? item.revision);
  const editButton=useRef(null);
  useEffect(()=>{if(!savedEdit)setEditing(false);},[savedEdit]);
  const editChanged=editing && (item.revision!==editRevision || item.state!=="queued");
  const textTooLong=Array.from(text || "").length>8000;
  function change(cancel){onChange({request_id:item.request_id,revision:cancel?item.revision:editRevision,...(cancel?{cancel:true}:{prompt:text})});}
  return <article className="chat-queued-item"><strong>{item.state==='departed'?'대기열에서 사라짐':item.state==='dispatching'?'실행 준비 중':'대기 중'}</strong>
    {editing ? <><textarea autoFocus aria-label="대기 요청 수정" value={text} onChange={event=>{setText(event.target.value);onEditing({...item,revision:editRevision,text:event.target.value});}}/>{editChanged && <><p role="alert">대기 요청이 변경되었거나 대기열에서 사라졌습니다. 작성한 내용을 복사한 뒤 편집을 취소하고 최신 상태를 확인해 주세요.</p><CopyTextButton value={text} label="대기 요청 편집 내용 복사" buttonLabel="편집 내용 복사"/></>}{unavailable && <p role="status">연결이 복구되어 대기열 상태를 확인할 때까지 저장할 수 없습니다.</p>}{textTooLong && <p role="alert">대기 요청은 8,000자까지 저장할 수 있습니다. 초과한 내용을 줄여 주세요.</p>}<div className="chat-queue-actions"><button type="button" disabled={mutationLocked || unavailable || editChanged || textTooLong || !text.trim() || text.trim()===String(item.prompt || "").trim()} onClick={()=>change(false)}>변경 저장</button><button type="button" onClick={()=>{setText(item.prompt);setEditing(false);onEditing(null);requestAnimationFrame(()=>editButton.current?.focus());}}>편집 취소</button></div></> : <ChatQueuePrompt text={item.prompt}/>}
    {item.state==='queued' && !editing && <div className="chat-queue-actions"><button ref={editButton} type="button" disabled={mutationLocked || disableEdit || unavailable} title={unavailable?"대기열 연결을 확인해 주세요.":disableEdit?"다른 요청의 편집을 먼저 마쳐 주세요.":undefined} onClick={()=>{setText(item.prompt);setEditRevision(item.revision);onEditing({...item,text:item.prompt});setEditing(true);}}>수정</button><button type="button" disabled={mutationLocked || unavailable} title={unavailable?"대기열 연결을 확인해 주세요.":undefined} onClick={()=>change(true)}>대기 취소</button></div>}
  </article>;
}
function LiveInstructionForm({session,job,onRefresh,unavailable=false,receipts=[]}){
  const key="hermes-live-pending-"+session+"-"+job;
  const draftKey="hermes-live-draft-"+session+"-"+job;
  const [restored]=useState(()=>{try{const item=JSON.parse(sessionStorage.getItem(key));return item?.session_id===session && item.job_id===job && ["steer","redirect"].includes(item.mode) && typeof item.text==="string" && item.text.trim() && typeof item.request_id==="string" ? item : null;}catch{return null;}});
  const [draft]=useState(()=>{try{const item=JSON.parse(sessionStorage.getItem(draftKey));return item && ["steer","redirect"].includes(item.mode) && typeof item.text==="string" ? item : null;}catch{return null;}});
  const [mode,setMode]=useState(draft?.mode || restored?.mode || "steer"),[text,setText]=useState(draft?.text ?? restored?.text ?? ""),[busy,setBusy]=useState(false),[notice,setNotice]=useState(restored ? "이전 지시의 접수 여부를 다시 확인해 주세요." : "");
  const sendController=useRef(null),sendBusy=useRef(false),mounted=useRef(true);
  const [draftStorageError,setDraftStorageError]=useState(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;sendController.current?.abort();};},[]);
  function saveDraft(nextText,nextMode){setText(nextText);setMode(nextMode);try{if(nextText)sessionStorage.setItem(draftKey,JSON.stringify({text:nextText,mode:nextMode}));else sessionStorage.removeItem(draftKey);setDraftStorageError(false);}catch{setDraftStorageError(true);}}
  const [pendingReceipt,setPendingReceipt]=useState(restored);
  useEffect(()=>{if(!pendingReceipt)return;try{if(!sessionStorage.getItem(key)){const receipt=receipts.find(row=>matchesLiveInstructionReceipt(row,pendingReceipt,{confirmed:true}));if(receipt){setPendingReceipt(null);setNotice("이전 지시의 전달 내역을 확인했습니다. 상세 상태를 확인하세요.");}else setNotice("이전 접수 확인 기록이 없어 전달 여부를 확인할 수 없습니다. 전달 내역을 확인하세요.");}}catch{}},[key,pendingReceipt,receipts]);
  const pendingMismatch=Boolean(pendingReceipt && (pendingReceipt.text!==text.trim() || pendingReceipt.mode!==mode));
  const instructionTooLong=Array.from(text.trim()).length>8000;
  async function send(){
    const input=pendingReceipt?.text || text.trim(),sendMode=pendingReceipt?.mode || mode;if(!input || sendBusy.current || unavailable || (!pendingReceipt && Array.from(input).length>8000))return;
    let pending;try{pending=JSON.parse(sessionStorage.getItem(key) || "null") || pendingReceipt;}catch{setNotice("이전 접수 기록을 읽을 수 없습니다. 작업 상태를 확인하세요.");return;}
    if(pending && (pending.text!==input || pending.mode!==sendMode)){setNotice("이전 지시의 접수 확인이 필요합니다. 전달 내역을 확인하세요.");return;}
    pending=pending || {session_id:session,job_id:job,request_id:crypto.randomUUID().replaceAll("-",""),mode:sendMode,text:input};
    try{sessionStorage.setItem(key,JSON.stringify(pending));}catch{setNotice("접수 확인 정보를 보관하지 못해 지시를 전달할 수 없습니다. 브라우저 저장 공간을 확인하세요.");return;}setPendingReceipt(pending);sendBusy.current=true;setBusy(true);setNotice("");
    const controller=new AbortController();sendController.current=controller;const timer=setTimeout(()=>controller.abort(),30000);
    try{const row=await callUntilAborted("live-instruction",pending,controller.signal);if(controller.signal.aborted || !matchesLiveInstructionReceipt(row,pending))throw new Error("접수 응답 불일치");let current,storedDraft;try{current=JSON.parse(sessionStorage.getItem(key));storedDraft=JSON.parse(sessionStorage.getItem(draftKey));}catch{}if(current?.request_id===pending.request_id){sessionStorage.removeItem(key);setPendingReceipt(null);if(storedDraft?.text?.trim()===pending.text && storedDraft.mode===pending.mode)sessionStorage.removeItem(draftKey);}if(text.trim()===pending.text && mode===pending.mode)setText("");setNotice(row.state==="applied"?"지시 반영이 확인됐습니다.":row.state==="accepted"?"전달 접수됨 · 반영 여부 확인 중":row.state==="undelivered"?"전달되지 않았습니다. 후속 요청으로 복구할 수 있습니다.":row.state==="pending" || row.state==="delivering"?"지시 전달 상태를 확인 중입니다.":"전달 결과 확인이 필요합니다.");onRefresh();}
    catch(problem){if(mounted.current)setNotice("접수 결과를 확인하지 못했습니다. 같은 지시로 다시 확인하세요. "+requestErrorMessage(problem));}finally{clearTimeout(timer);sendController.current=null;sendBusy.current=false;if(mounted.current)setBusy(false);}
  }
  return <div className="live-instruction-form"><label>실행 중 지시 <textarea aria-label="실행 중 지시" value={text} disabled={busy} onChange={event=>saveDraft(event.target.value,mode)} placeholder="추가하거나 수정할 지시를 입력하세요"/></label><span className="live-instruction-mode-label">전달 방식</span><div className="chat-queue-actions"><select aria-label="전달 방식" value={mode} disabled={busy} onChange={event=>saveDraft(text,event.target.value)}><option value="steer">지시 추가</option><option value="redirect">지시 방향 수정</option></select><button type="button" aria-label={busy ? "지시 확인 중" : pendingReceipt ? "지시 접수 다시 확인" : "지시 전달"} aria-disabled={busy || unavailable || (!pendingReceipt && (!text.trim() || instructionTooLong))} onClick={send}>{busy?"확인 중":pendingReceipt?"접수 확인":"전달"}</button></div>{draftStorageError && text && <p role="alert">초안을 이 탭에 보관하지 못했습니다. 패널을 닫기 전에 내용을 복사하세요. <CopyTextButton value={text} label="실행 중 지시 초안 복사" buttonLabel="초안 복사"/></p>}{unavailable && <p role="status">대기열 연결을 확인할 때까지 지시를 전달할 수 없습니다.</p>}{instructionTooLong && !pendingReceipt && <p role="alert">지시는 8,000자까지 전달할 수 있습니다. 초과한 내용을 줄여 주세요.</p>}{pendingMismatch && <><p>이전 지시의 접수를 먼저 확인합니다. 작성 중인 새 지시는 유지됩니다.</p><details><summary>확인할 이전 지시 보기</summary><p>{pendingReceipt.mode==="steer" ? "지시 추가" : "지시 방향 수정"}</p><p className="chat-queue-prompt-expanded" tabIndex={0} aria-label="확인할 이전 지시 내용">{pendingReceipt.text}</p></details></>}{notice && <p role="status">{notice}</p>}</div>;
}
function LiveInstructionReceipts({rows,session,onRefresh,unavailable=false}){
  const [notice,setNotice]=useState(""),[busy,setBusy]=useState("");
  const recovering=useRef(false),controllerRef=useRef(null),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;controllerRef.current?.abort();};},[]);
  async function recover(row){
    if(recovering.current || unavailable)return;
    recovering.current=true;setBusy(row.request_id);setNotice("");const controller=new AbortController();controllerRef.current=controller;const timer=setTimeout(()=>controller.abort(),30000);
    try{const result=await callUntilAborted("live-instruction-recover",{session_id:session,request_id:row.request_id},controller.signal);if(controller.signal.aborted || !(await matchesLiveInstructionRecovery(result,row)) || controller.signal.aborted)throw new Error("복구 응답 불일치");setNotice(!result.duplicate?"후속 대기열에 복구했습니다.":result.request.state==="cancelled"?"이 지시의 후속 요청은 이미 취소되었습니다.":result.request.state==="dispatched"?"이 지시의 후속 요청은 이미 실행 접수되었습니다.":result.request.state==="dispatching"?"이 지시의 후속 요청은 실행 준비 중입니다.":"이 지시의 후속 요청은 이미 대기 중입니다.");}
    catch{if(mounted.current)setNotice("복구 결과를 확인하지 못했습니다. 대기열과 지시 내역을 확인한 뒤 다시 시도하세요.");}finally{clearTimeout(timer);controllerRef.current=null;recovering.current=false;if(mounted.current){setBusy("");onRefresh();}}
  }
  const labels={pending:"접수 중",delivering:"전달 확인 중",accepted:"전달 접수 · 반영 확인 중",applied:"반영 확인",undelivered:"미전달",unknown:"전달 여부 불명"};
  if(!rows?.length)return null;
  const needsRecovery=rows.filter(row=>row.state==="undelivered" && !row.recovery).length;
  const recoveryLabels={queued:"대기 중",dispatching:"실행 준비 중",dispatched:"실행 접수됨",cancelled:"취소됨"};
  return <details className="live-instruction-receipts"><summary>실행 중 전달한 지시 내역 · 최근 {rows.length}건{needsRecovery>0 && ` · 미복구 ${needsRecovery}건`}</summary>{rows.slice().reverse().map(row=><article key={row.request_id}><strong>{labels[row.state] || "확인 불가"} · {row.mode==="steer"?"지시 추가":"방향 수정"}</strong><p>{row.text}</p><small>{row.created_at && !Number.isNaN(new Date(row.created_at).getTime()) && <>접수 · {new Date(row.created_at).toLocaleString("ko-KR")} · </>}{row.job_id && <a href={jobLink(row.job_id,session)}>원래 작업 보기</a>}</small>{row.state==="undelivered" && (row.recovery ? <p><small>후속 요청 {recoveryLabels[row.recovery.state] || "상태 확인 불가"}{row.recovery.job_id && <> · <a href={jobLink(row.recovery.job_id,session)}>후속 작업 보기</a></>}</small></p> : <button type="button" disabled={Boolean(busy) || unavailable} onClick={()=>recover(row)}>{busy===row.request_id?"복구 중":"후속 요청으로 복구"}</button>)}{row.state==="unknown" && <p><small>중복 반영 가능성이 있어 자동 재전달하지 않습니다.</small></p>}</article>)}{notice && <p role="status">{notice}</p>}</details>;
}
function ChatQueuePanel({session}){
  const [data,setData]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0),[stopJobs,setStopJobs]=useState(()=>new Set()),[stopNotices,setStopNotices]=useState({});
  const editKey="hermes-queue-edit-"+session;
  const [editingItem,setEditingItem]=useState(()=>{try{const saved=JSON.parse(sessionStorage.getItem(editKey));return saved && typeof saved.request_id==="string" && typeof saved.text==="string" && Number.isInteger(saved.revision) ? saved : null;}catch{return null;}});
  const [editStorageError,setEditStorageError]=useState(false);
  const editingItemRef=useRef(editingItem);
  const pendingKey="hermes-queue-update-"+session;
  const [pendingUpdate,setPendingUpdate]=useState(()=>{try{const p=JSON.parse(sessionStorage.getItem(pendingKey));return p?.session_id===session && /^[A-Za-z0-9_-]{8,80}$/.test(p.request_id) && Number.isInteger(p.revision) && p.revision>0 && ((p.cancel===true && p.prompt===undefined) || (p.cancel===undefined && typeof p.prompt==="string" && p.prompt.trim() && Array.from(p.prompt).length<=8000)) ? p : null;}catch{return null;}});
  const pendingRef=useRef(pendingUpdate),updateController=useRef(null),updateBusyRef=useRef(false),pendingPanelRef=useRef(null),queueRefreshRef=useRef(null);
  const stopControllers=useRef(new Map()),panelMounted=useRef(true);
  const [updateBusy,setUpdateBusy]=useState(false),[updateNotice,setUpdateNotice]=useState("");
  useEffect(()=>()=>{updateController.current?.abort();},[]);
  useEffect(()=>{panelMounted.current=true;return()=>{panelMounted.current=false;for(const controller of stopControllers.current.values())controller.abort();};},[]);
  function rememberEdit(item,expected){
    const current=editingItemRef.current;
    if(!item && expected && (!current || current.request_id!==expected.request_id || current.revision!==expected.revision || current.text!==expected.text))return;
    const focused=!item && expected && document.activeElement?.matches('textarea[aria-label="대기 요청 수정"]') ? document.activeElement : null;
    editingItemRef.current=item;setEditingItem(item);
    try{if(item)sessionStorage.setItem(editKey,JSON.stringify(item));else sessionStorage.removeItem(editKey);setEditStorageError(false);}catch{setEditStorageError(true);}
    if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)queueRefreshRef.current?.focus();});
  }
  function clearPending(p){try{const stored=JSON.parse(sessionStorage.getItem(pendingKey));if(stored && JSON.stringify(stored)!==JSON.stringify(p))return false;sessionStorage.removeItem(pendingKey);}catch{return false;}const focused=pendingPanelRef.current?.contains(document.activeElement) ? document.activeElement : null;pendingRef.current=null;setPendingUpdate(null);if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)queueRefreshRef.current?.focus();});return true;}
  async function sendUpdate(payload){
    if(updateBusyRef.current)return;
    let p=pendingRef.current;
    if(!p){if(!payload.cancel && (typeof payload.prompt!=="string" || !payload.prompt.trim() || Array.from(payload.prompt).length>8000)){setUpdateNotice("대기 요청은 1~8,000자여야 합니다.");return;}p={session_id:session,...payload};try{sessionStorage.setItem(pendingKey,JSON.stringify(p));}catch{setUpdateNotice("접수 확인 정보를 보관하지 못해 변경 요청을 보내지 않았습니다.");return;}pendingRef.current=p;setPendingUpdate(p);}
    updateBusyRef.current=true;setUpdateBusy(true);setUpdateNotice("");const controller=new AbortController();updateController.current=controller;const timer=setTimeout(()=>controller.abort(),30000);
    try{const row=await callUntilAborted("chat-queue-update",p,controller.signal);if(controller.signal.aborted || !row || row.request_id!==p.request_id || row.revision!==p.revision+1 || (p.cancel ? row.state!=="cancelled" : row.state!=="queued" || row.prompt!==p.prompt))throw new Error("변경 응답 불일치");if(clearPending(p)){if(!p.cancel)rememberEdit(null,{request_id:p.request_id,revision:p.revision,text:p.prompt});setUpdateNotice(p.cancel?"대기 요청을 취소했습니다.":"대기 요청을 수정했습니다.");}else setUpdateNotice("변경 응답을 받았지만 확인 기록을 지우지 못했습니다. 저장소를 확인하세요.");}
    catch{setUpdateNotice("변경 결과를 확인하지 못했습니다. 같은 요청을 다시 확인하거나 현재 상태를 조회하세요.");}finally{clearTimeout(timer);updateController.current=null;updateBusyRef.current=false;setUpdateBusy(false);refresh(n=>n+1);}
  }
  async function checkUpdate(){
    const p=pendingRef.current;if(!p || updateBusyRef.current)return;
    updateBusyRef.current=true;setUpdateBusy(true);const controller=new AbortController();updateController.current=controller;const timer=setTimeout(()=>controller.abort(),15000);
    try{const view=await callUntilAborted("session-view",{session_id:session,limit:1},controller.signal);const state=classifyQueueUpdate(view,session,p);if(controller.signal.aborted || state==="invalid")throw new Error("대기열 응답 오류");if(state==="waiting"){setUpdateNotice("요청이 이전 버전으로 대기 중입니다. 앞선 변경이 늦게 반영될 수 있으므로 같은 요청만 다시 확인할 수 있습니다.");}else if(clearPending(p)){if(state==="applied"){rememberEdit(null,{request_id:p.request_id,revision:p.revision,text:p.prompt});setUpdateNotice("현재 대기 요청에 수정 내용이 반영되어 있습니다.");}else setUpdateNotice("대기 요청의 상태가 변경되어 이전 변경이 추가로 적용되지는 않습니다. 앞선 요청의 처리 결과와 편집 내용을 확인하세요.");}else setUpdateNotice("확인 기록을 지우지 못했습니다. 저장소를 확인하세요.");refresh(n=>n+1);}
    catch{setUpdateNotice("현재 대기 상태를 확인하지 못했습니다. 같은 요청을 다시 확인해 주세요.");}finally{clearTimeout(timer);updateController.current=null;updateBusyRef.current=false;setUpdateBusy(false);}
  }
  async function stopCurrent(){
    const job=data?.chat_active?.job_id;if(!job || error || stopControllers.current.has(job) || !window.confirm("현재 채팅 작업에 중단을 요청할까요? 이미 실행된 도구의 변경은 유지될 수 있습니다."))return;
    const controller=new AbortController();stopControllers.current.set(job,controller);const timer=setTimeout(()=>controller.abort(),30000);
    setStopJobs(previous=>new Set(previous).add(job));setStopNotices(previous=>({...previous,[job]:""}));
    try{const response=await callUntilAborted("cancel",{id:job},controller.signal);if(controller.signal.aborted || response.id!==job || response.cancel_requested!==true)throw new Error("중단 요청 접수를 확인할 수 없습니다.");setStopNotices(previous=>({...previous,[job]:"중단을 요청했습니다. 작업 종료 여부를 확인 중입니다."}));}
    catch{if(panelMounted.current)setStopNotices(previous=>({...previous,[job]:"중단 요청 결과를 확인하지 못했습니다. 작업 상세에서 종료 여부를 확인하세요."}));}finally{clearTimeout(timer);stopControllers.current.delete(job);if(panelMounted.current){setStopJobs(previous=>{const next=new Set(previous);next.delete(job);return next;});refresh(n=>n+1);}}
  }
  useEffect(()=>{let active=true,timer,timeout,controller;async function load(){controller=new AbortController();timeout=setTimeout(()=>controller.abort(),15000);try{const next=await callUntilAborted("session-view",{session_id:session,limit:1},controller.signal);if(!validChatQueue(next,session) || (next.chat_active!=null && (typeof next.chat_active.job_id!=="string" || typeof next.chat_active.prompt!=="string" || typeof next.chat_active.status!=="string")) || !validLiveInstructionRows(next.live_instructions))throw new Error("대기열 응답 오류");if(active && !controller.signal.aborted){setData({...next,checkedAt:new Date()});setError("");}}catch(problem){if(active)setError(problem.message || "대기열 조회 오류");}finally{clearTimeout(timeout);if(active)timer=setTimeout(load,3000);}}load();return()=>{active=false;clearTimeout(timer);clearTimeout(timeout);controller?.abort();};},[session,revision]);
  return <section className="chat-queue-panel" aria-label="세션 채팅 대기열"><div className="chat-queue-header"><h2>세션 채팅 대기열</h2><button ref={queueRefreshRef} type="button" onClick={()=>refresh(n=>n+1)}>새로고침</button></div>
    <small>{data?.checkedAt ? "조회 시각 · "+data.checkedAt.toLocaleString("ko-KR")+" · 조회 종료 후 3초마다" : error ? "대기열 조회 실패" : "대기열 조회 중"}</small>
    {error && <p role="alert">대기열을 불러오지 못했습니다. {data && "표시된 내용은 마지막 조회 결과입니다."}</p>}
    {editStorageError && editingItem && <p role="alert">편집 내용을 이 탭에 보관하지 못했습니다. 패널을 닫기 전에 내용을 복사하세요. <CopyTextButton value={editingItem.text} label="대기 요청 편집 내용 복사" buttonLabel="편집 내용 복사"/></p>}
    {pendingUpdate && <section ref={pendingPanelRef} className="chat-queued-item" aria-label="대기 요청 변경 확인"><strong>대기 요청 변경 확인 필요</strong><p>{pendingUpdate.cancel?"대기 취소":"대기 요청 수정"} · {pendingUpdate.request_id}</p>{pendingUpdate.prompt && <><ChatQueuePrompt text={pendingUpdate.prompt}/><CopyTextButton value={pendingUpdate.prompt} label="확인할 수정 내용 복사" buttonLabel="수정 내용 복사"/></>}<div className="chat-queue-actions"><button type="button" aria-disabled={updateBusy} onClick={()=>sendUpdate()}>{updateBusy?"확인 중":"같은 요청 다시 확인"}</button><button type="button" aria-disabled={updateBusy} onClick={checkUpdate}>현재 상태 확인</button></div></section>}
    {updateNotice && <p role="status">{updateNotice}</p>}
    {!data && error && editingItem && <section className="chat-queued-item" aria-label="복원된 대기 요청 편집 내용"><strong>이 탭에 보관된 편집 내용</strong><p>대기열 상태를 확인할 때까지 저장할 수 없습니다. 내용을 복사하거나 연결 후 다시 확인하세요.</p><textarea aria-label="복원된 대기 요청 수정" value={editingItem.text} onChange={event=>rememberEdit({...editingItem,text:event.target.value})}/>{editingItem.text && <CopyTextButton value={editingItem.text} label="복원된 대기 요청 편집 내용 복사" buttonLabel="편집 내용 복사"/>}<button type="button" onClick={()=>rememberEdit(null)}>편집 내용 지우기</button></section>}
    {data && <><h3>현재 요청</h3>{data.chat_active ? <article className="chat-queue-current"><strong>{statusLabels[data.chat_active.status] || "확인 불가"}</strong><ChatQueuePrompt key={data.chat_active.job_id} text={data.chat_active.prompt}/><JobIdentifier id={data.chat_active.job_id} label="채팅 작업 ID" compact/><a href={jobLink(data.chat_active.job_id,session)}>작업 상세 보기</a>{data.chat_active.status==="running" && (data.chat_active.control_ready ? <LiveInstructionForm key={data.chat_active.job_id} session={session} job={data.chat_active.job_id} receipts={data.live_instructions} unavailable={Boolean(error)} onRefresh={()=>refresh(n=>n+1)}/> : <p>실행 중 지시 전달 경로가 준비되지 않았습니다. 준비 중이거나 이전 방식으로 시작된 작업일 수 있습니다.</p>)}{["running","queued"].includes(data.chat_active.status) && <button type="button" aria-disabled={stopJobs.has(data.chat_active.job_id) || Boolean(error)} onClick={stopCurrent}>{stopJobs.has(data.chat_active.job_id)?"중단 요청 중":"지시 중단"}</button>}{stopNotices[data.chat_active.job_id] && <p role="status">{stopNotices[data.chat_active.job_id]}</p>}</article> : <p>실행 중인 채팅 요청이 없습니다.</p>}
      <h3>대기 중인 요청 · {data.chat_queue.length}</h3>{!data.chat_queue.length && <p>대기 중인 요청이 없습니다. 이 세션에서 요청이 실행되는 동안 새 메시지를 보내면 대기열에 추가되고, 앞선 요청이 끝난 뒤 순서대로 실행됩니다.</p>}{[...data.chat_queue,...(editingItem && !data.chat_queue.some(item=>item.request_id===editingItem.request_id) ? [{...editingItem,state:"departed"}] : [])].map((item,index)=><div key={item.request_id}><small>{item.state==="departed"?"대기열에서 사라진 요청의 편집 내용":"대기 순서 · "+(index+1)}</small><ChatQueueItem item={item} savedEdit={editingItem?.request_id===item.request_id ? editingItem : null} unavailable={Boolean(error)} mutationLocked={Boolean(pendingUpdate)} disableEdit={Boolean(editingItem && editingItem.request_id!==item.request_id)} onEditing={rememberEdit} onChange={sendUpdate}/></div>)}<LiveInstructionReceipts rows={data.live_instructions} session={session} unavailable={Boolean(error)} onRefresh={()=>refresh(n=>n+1)}/></>}
  </section>;
}
function AssistantText({text}){
  return <div className="assistant-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
    a:({href,children})=>href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <>{children}</>,
    img:({alt})=><span>{alt || "이미지"}</span>,
  }}>{text}</Markdown></div>;
}
function ActivityOutput({output}){
  const [mode,setMode]=useState("formatted");
  const formatted=useMemo(()=>formatActivityOutput(output),[output]);
  const text=useMemo(()=>{if(!formatted)return "";try{const value=JSON.parse(output);return typeof value?.matches_text==="string" ? value.matches_text : typeof value?.content==="string" ? value.content : "";}catch{return "";}},[output,formatted]);
  const shown=(mode==="text" && text ? text : mode!=="raw" && formatted ? formatted : output) || "";
  return <>{formatted && <button className="activity-output-toggle" type="button" onClick={()=>setMode(mode==="raw"?"formatted":"raw")}>{mode==="raw"?"정리해서 보기":"원문 보기"}</button>}{text && <button className="activity-output-toggle" type="button" onClick={()=>setMode(mode==="text"?"formatted":"text")}>{mode==="text"?"구조 보기":"텍스트 보기"}</button>}{shown && <CopyTextButton value={shown} label="도구 결과 출력 복사" buttonLabel="출력 복사"/>}{mode==="text" && text && <p>텍스트 필드만 표시합니다. 다른 필드는 구조 보기에서 확인하세요.</p>}<pre tabIndex={0} aria-label="도구 결과 출력">{shown || "출력 없음"}</pre></>;
}
function ActivityEvent({start,result,running}){
  const [open,setOpen]=useState(false);
  const event=start || result, state=result ? (result.result==="error" ? "failed" : "completed") : running && start?.call_id ? "running" : "unknown";
  const label={running:"실행 중",completed:"완료",failed:"실패",unknown:"결과 미확인"}[state];
  return <li><details onToggle={event=>{if(event.target===event.currentTarget)setOpen(event.currentTarget.open);}}><summary>
    <span className={'activity-state '+state}><span className="activity-icon" aria-hidden="true">{state==="running"?"◌":state==="completed"?"✓":state==="failed"?"!":"?"}</span>{label}</span><span>{event.name}</span>{event.timestamp && <time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleTimeString("ko-KR")}</time>}</summary>
    {open && <div className="hermes-activity-detail">{start?.target && <><strong>실행 대상</strong><pre tabIndex={0} aria-label="도구 실행 대상">{start.target}</pre></>}{result && <><strong>도구 결과</strong>{typeof result.output==="string" ? <><ActivityOutput output={result.output}/>{result.output_truncated && <small>출력의 앞부분만 표시합니다.</small>}</> : <p>상세 출력을 불러오지 못했습니다.</p>}{Number.isInteger(result.duration_ms) && <p>소요 시간 · {(result.duration_ms/1000).toFixed(1)}초</p>}</>}{!result && <p>{state==="running" ? "도구 결과를 기다리는 중입니다." : "기록된 결과가 없습니다."}</p>}{event.call_id && <p>호출 ID · <code>{event.call_id}</code></p>}</div>}
  </details></li>;
}
function groupActivityEvents(events){
  const entries=[],calls=new Map();
  events.forEach((event,index)=>{
    if(event.type==="tool_use"){
      const item={start:event,index};entries.push(item);
      if(event.call_id)calls.set(event.call_id,item);
    } else if(event.type==="tool_result"){
      const match=event.call_id && calls.get(event.call_id);
      if(match && !match.result)match.result=event;
      else entries.push({result:event,index});
    }
  });
  return entries;
}
function ActivityEvents({entries,truncated,running=false}){
  const activeTool=entries.some(item=>item.start?.call_id && !item.result);
  return <><ol className="hermes-activity-events">{entries.map(({start,result,index})=>{const event=start || result;return <ActivityEvent key={(event.call_id || "event")+":"+(event.timestamp || index)} {...{start,result,running}}/>;})}</ol>{running && !activeTool && <p className="hermes-activity-wait" role="status"><span className="activity-state running"><span className="activity-icon" aria-hidden="true">◌</span>기록상 작업 실행 중</span> · 현재 실행 중인 도구 활동은 관측되지 않았습니다. 다음 활동을 기다리는 중입니다.</p>}{truncated && <small>최근 활동만 표시합니다.</small>}</>;
}
function ActivitySection({activity,running=false}){
  const [open,setOpen]=useState(false);
  const entries=useMemo(()=>groupActivityEvents(activity?.events || []),[activity?.events]);
  const count=entries.length;
  return <section className="hermes-activity" aria-label={running?"헤르메스 진행 상황":undefined} aria-live={running?"polite":undefined}>
    <details onToggle={event=>{if(event.target===event.currentTarget)setOpen(event.currentTarget.open);}}><summary>{running ? "진행 상황 · 기록상 작업 실행 중"+(count ? " · 최근 도구 활동 "+count+"건" : " · 도구 활동 대기 중") : "도구 사용 내역 · 최근 "+count+"건"}</summary>
      {open && <>{count ? <ActivityEvents entries={entries} truncated={activity.truncated} running={running}/> : <p>{running?"아직 관측된 도구 활동이 없습니다. 작업을 진행 중입니다.":"표시할 도구 활동이 없습니다."}</p>}{running && <small>진행 중에는 약 3초 간격으로 갱신됩니다.</small>}</>}
    </details>
  </section>;
}
function Message() {
  const actions=React.useContext(ProposalActions);
  const message=useAuiState(s=>s.message);
  const meta=message.metadata?.custom || {};
  const copyText=(message.content || []).filter(part=>part.type==="text" && typeof part.text==="string").map(part=>part.text).join("\n");
  const paths=React.useContext(HistoryRoutes);
  const path=paths[meta.activity?.source_history_page?.service];
  const table=meta.table && meta.activity?.source_history_page ? {...meta.table,rows:meta.table.rows.map(([job,...cells])=>[
    <><JobIdentifier id={job} compact/>{path && <a href={path+"?"+new URLSearchParams({job,session:meta.session})}>작업 열기</a>}</>,...cells])} : meta.table;
  return <MessagePrimitive.Root data-form-id={meta.formId || undefined} data-job-id={meta.job || undefined} tabIndex={meta.formId || meta.job ? -1 : undefined} className={"message "+message.role+(meta.formId?" message-form":"")}>
    <b>{meta.formId?"생성 작업":message.role==="user"?"나":"헤르메스"}</b>
    {meta.status==="failed" ? <section className="assistant-failure" aria-label="헤르메스 작업 실패">
      <strong>헤르메스 작업 실패</strong>
      <p>요청을 완료하지 못했습니다. {meta.job && "작업 상세에서 원인을 확인하세요. "}생성 요청이었다면 다시 접수하기 전에 작업·대기열과 생성 이력을 확인하세요.</p>
      <div className="assistant-failure-actions"><button type="button" onClick={actions.openQueue}>작업·대기열 확인</button>{meta.kimodoRequest && <button type="button" onClick={()=>actions.openStep()}>Kimodo 생성기 열기</button>}{meta.job && <a href={jobLink(meta.job,meta.session)}>오류 상세 확인</a>}</div>
      {copyText.trim() && <details><summary>헤르메스 응답 원문</summary><MessagePrimitive.Parts components={{Text:AssistantText}}/><CopyTextButton value={copyText} label="헤르메스 응답 원문 복사" buttonLabel="원문 복사"/></details>}
    </section> : <MessagePrimitive.Parts components={message.role==="assistant" ? {Text:AssistantText} : undefined}/>}
    {message.role==="assistant" && ["cancelled","canceled"].includes(meta.status) && !message.content?.some(part=>part.type==="text" && part.text?.trim()) && <p className="assistant-cancelled" role="status">이 요청은 취소되었습니다.</p>}
    {meta.formId && <ConversationVideoForm session={meta.session} formId={meta.formId} open={actions.openVideoForm} reuse={actions.openJobForm}/>}
    {meta.seedProposal && <SeedProposal proposal={meta.seedProposal} onOpen={actions.openSeedForm}/>}
    {meta.kimodoProposal && meta.job && <KimodoProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset} append={actions.append} openStep={actions.openStep}/>}
    {meta.generationProposal && meta.job && <GenerationProposal key={meta.job} kind={meta.generationProposal} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.captureProposal && meta.job && <CaptureProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.fluxProposal && meta.job && <FluxProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.buildingProposal && meta.job && <BuildingProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.billboardProposal && meta.job && <BillboardProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.spriteProposal && meta.job && <SpriteProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.effectProposal && meta.job && <EffectProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.cityProposal && meta.job && <CityProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {meta.fieldProposal && meta.job && <FieldProposal key={meta.job} job={meta.job} session={meta.session} snapshot={meta.sessionSnapshot} offset={meta.sessionOffset}/>}
    {table && <ResultTable table={table}/>}
    {meta.videoSuggestion && <SuggestedVideoResult suggestion={meta.videoSuggestion} onReuse={()=>actions.openJobForm(meta.videoSuggestion.job_id)}/>}
    {meta.activity?.video_source && <MediaJobResult kind="video" folderLink service={meta.activity.video_source.service} id={meta.activity.video_source.job_id} onReuse={meta.activity.video_source.service==="wan22-fun-control" ? ()=>actions.openJobForm(meta.activity.video_source.job_id) : undefined}/>}
    {!meta.table && meta.activity?.source_history_summary && <pre>{meta.activity.source_history_summary}</pre>}
    {(meta.status==="running" || meta.activity?.events?.length>0) && <ActivitySection activity={meta.activity} running={meta.status==="running"}/>}
    {meta.queueMessage && <p role="status">{meta.queueMessage}</p>}
    {copyText.trim() && !meta.formId && meta.status!=="failed" && <CopyTextButton value={copyText} label={message.role==="user" ? "사용자 메시지 복사" : "헤르메스 메시지 복사"} buttonLabel="메시지 복사"/>}
    {meta.status && <small>{statusLabels[meta.status] || meta.status} {meta.job && <> · <a href={jobLink(meta.job,meta.session)}>{meta.job}</a> <CopyTextButton value={meta.job} label="헤르메스 작업 ID 복사" buttonLabel="ID 복사"/></>}</small>}
  </MessagePrimitive.Root>;
}
function Conversation({view,historyPage,changeHistory}) {
  const messages=React.useMemo(()=>messagesFrom(view),[view]);
  const viewport=useRef(null),returningLatest=useRef(false);
  useEffect(()=>{
    if(!historyPage && returningLatest.current && view.id && view.offset===0){
      const trigger=returningLatest.current;returningLatest.current=false;
      requestAnimationFrame(()=>{viewport.current?.scrollTo({top:viewport.current.scrollHeight,behavior:"auto"});if(document.activeElement===document.body || document.activeElement===trigger)viewport.current?.focus({preventScroll:true});});
    }
  },[historyPage,view.id,view.offset]);
  const [routes,setRoutes]=useState({});
  const hasHistory=messages.some(message=>message.metadata?.custom?.activity?.source_history_page);
  useEffect(()=>{
    if(!hasHistory)return;
    const controller=new AbortController();
    fetch(base+"history-services",{signal:controller.signal}).then(response=>{
      if(!response.ok)throw new Error();
      return response.json();
    }).then(services=>{
      if(!controller.signal.aborted)setRoutes(Object.fromEntries(services.filter(row=>row.result_path).map(row=>[row.service,row.result_path])));
    }).catch(()=>{}); // Keep saved rows readable when the catalog is unavailable.
    return ()=>controller.abort();
  },[hasHistory]);
  const runtime=useExternalStoreRuntime({messages,isRunning:false,convertMessage:m=>m});
  return <HistoryRoutes.Provider value={routes}><AssistantRuntimeProvider runtime={runtime}><ThreadPrimitive.Root className="thread"><ThreadPrimitive.Viewport ref={viewport} className="viewport" tabIndex={-1} aria-label="대화 메시지">
    {view.next_offset != null && <nav className="conversation-history-nav" aria-label="이전 대화 페이지"><button type="button" onClick={()=>changeHistory({offset:view.next_offset,snapshot:view.snapshot})}>이전 메시지 보기</button><span>이전 메시지 {Math.max(0,(view.message_count || 0)-(view.offset || 0)-(view.messages || []).length)}건</span></nav>}
    <ThreadPrimitive.Empty><h2 className="conversation-empty-title">무엇을 도와드릴까요?</h2></ThreadPrimitive.Empty>
    <ThreadPrimitive.Messages components={{Message}}/>
    {historyPage && <nav className="conversation-history-nav" aria-label="이후 대화 페이지">
      {historyPage.offset>CONVERSATION_PAGE_SIZE && <button type="button" onClick={()=>changeHistory({offset:Math.max(0,historyPage.offset-CONVERSATION_PAGE_SIZE),snapshot:historyPage.snapshot})}>다음 메시지 보기</button>}
      <button type="button" onClick={event=>{returningLatest.current=event.currentTarget;changeHistory(null);}}>최신 대화로 돌아가기</button>
    </nav>}
  </ThreadPrimitive.Viewport>
    {historyPage ? <button type="button" className="conversation-latest" onClick={event=>{returningLatest.current=event.currentTarget;changeHistory(null);}}>최신 메시지로 ↓</button> :
      <ThreadPrimitive.ScrollToBottom className="conversation-latest" behavior="smooth">최신 메시지로 ↓</ThreadPrimitive.ScrollToBottom>}
  </ThreadPrimitive.Root></AssistantRuntimeProvider></HistoryRoutes.Provider>;
}
function initialToolCategory(){
  const category=query().get("category") || "all";
  return ({"music-generation":"sound-management","sound-effects":"sound-management","town-map-review":"map-review","field-map-review":"map-review",animation:"animation-tool"})[category] || category;
}
function readPendingSubmission(raw,session){
  if(raw===null)return null;
  try{
    const item=JSON.parse(raw);
    if(typeof item?.prompt==="string" && item.prompt.trim() &&
       typeof item.session_id==="string" && /^[a-f0-9]{32}$/.test(item.session_id) &&
       (!session || item.session_id===session) && typeof item.request_id==="string" && /^[a-f0-9]{32}$/.test(item.request_id))
      return (!Object.hasOwn(item,'model_profile') || ['qwen3.5-4b','qwen3.8-27b'].includes(item.model_profile)) ? {session_id:item.session_id,request_id:item.request_id,prompt:item.prompt,...(item.model_profile?{model_profile:item.model_profile}:{})} : null;
  }catch{}
  return null;
}
function SidePanel({title,subtitle,onClose,onKeyDown,width,minWidth,maxWidth,onResize,hidden=false,children}) {
  const body=useRef(null),heading=useRef(null);
  useEffect(()=>{if(body.current)body.current.scrollTop=0;},[title]);
  useEffect(()=>{if(!hidden && title!=="도구 탐색")heading.current?.focus();},[title,hidden]);
  return <section id="hermes-side-panel" className="fun-drawer" style={hidden?{display:"none"}:undefined} aria-label={title} onKeyDown={onKeyDown}>
    <div className="fun-drawer-divider" role="separator" tabIndex={0} aria-label="오른쪽 패널 너비" aria-describedby="side-panel-resize-help" title="드래그하거나 좌우 화살표로 너비 조절 · Home 최소 · End 최대" aria-controls="hermes-side-panel" aria-orientation="vertical" aria-valuemin={minWidth} aria-valuemax={maxWidth} aria-valuenow={width}
      onPointerDown={event=>{if(event.button===0){event.preventDefault();event.currentTarget.focus();event.currentTarget.setPointerCapture(event.pointerId);}}}
      onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))onResize(event.currentTarget.parentElement.getBoundingClientRect().right-event.clientX);}}
      onKeyDown={event=>{const sizes={ArrowLeft:width+16,ArrowRight:width-16,Home:minWidth,End:maxWidth};if(Object.hasOwn(sizes,event.key)){event.preventDefault();event.stopPropagation();onResize(sizes[event.key]);}}}/>
    <span id="side-panel-resize-help" className="generator-visually-hidden">드래그하거나 좌우 화살표로 너비를 조절합니다. Home은 최소, End는 최대 너비입니다.</span>
    <header className="fun-drawer-header"><div ref={heading} tabIndex={-1} aria-label={title}><strong>{title}</strong><small>{subtitle}</small></div>
      <button type="button" aria-label={title+" 닫기"} onClick={onClose}>닫기</button></header>
    <div className="fun-drawer-body" ref={body}>{children}</div>
  </section>;
}
function App() {
  const [showFunControl,setShowFunControl]=useState(false);
  const [funMounted,setFunMounted]=useState(false);
  useEffect(()=>{if(showFunControl)setFunMounted(true);},[showFunControl]);
  const [showKimodo,setShowKimodo]=useState(false);
  const [kimodoMounted,setKimodoMounted]=useState(false);
  const [generatorPanel,setGeneratorPanel]=useState(null);
  const [mountedGenerators,setMountedGenerators]=useState([]);
  const [kimodoProposal,setKimodoProposal]=useState(null);
  const [kimodoRevision,setKimodoRevision]=useState(0);
  const [videoFormId,setVideoFormId]=useState("");
  const [videoFormRevision,setVideoFormRevision]=useState(0);
  const [seedProposal,setSeedProposal]=useState(null);
  const [session,setSession]=useState(query().get("session") || "");
  useEffect(()=>{setGeneratorPanel(null);setMountedGenerators([]);setKimodoMounted(false);setFunMounted(false);},[session]);
  const [sessions,setSessions]=useState([]), [view,setView]=useState({}), [tools,setTools]=useState([]);
  const [draft,setDraft]=useState(""),[search,setSearch]=useState(()=>query().get("search") || ""),[showTools,setShowTools]=useState(()=>query().has("category") || query().has("search") || ["jobs","capabilities"].includes(query().get("panel")));
  const [catalogError,setCatalogError]=useState(""),[catalogLoading,setCatalogLoading]=useState(true),[catalogRevision,retryCatalog]=useState(0);
  const [category,setCategory]=useState(initialToolCategory);
  const [archived,setArchived]=useState(false),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [sessionQuery,setSessionQuery]=useState("");
  const [listRequest,setListRequest]=useState({offset:0,query:""}),[listPage,setListPage]=useState(null);
  const [listError,setListError]=useState(""),[listLoading,setListLoading]=useState(false);
  const listFocusPending=useRef(false),listResultRef=useRef(null),listErrorRef=useRef(null);
  useEffect(()=>{if(listFocusPending.current && !listLoading && (listPage || listError)){listFocusPending.current=false;(listError ? listErrorRef.current : listResultRef.current)?.focus();}},[listPage,listError,listLoading]);
  function resetSessionList(){
    setSessionQuery("");setListRequest({offset:0,query:""});
  }
  const [queue,setQueue]=useState(null),[refresh,setRefresh]=useState(0);
  const queueFilterCache=useRef({});
  const [historyPage,setHistoryPage]=useState(null);
  const [viewError,setViewError]=useState("");
  const [viewLoading,setViewLoading]=useState(false);
  const [targetForm,setTargetForm]=useState("");
  const [targetProposal,setTargetProposal]=useState("");
  const [viewRevision,retryView]=useState(0);
  const sending=useRef(false),text=useRef(null);
  useLayoutEffect(()=>{
    const node=text.current;
    if(!node)return;
    const resize=()=>{node.style.height="auto";node.style.height=node.scrollHeight+"px";};
    resize();
    let width=node.clientWidth;
    const observer=new ResizeObserver(()=>{if(node.clientWidth!==width){width=node.clientWidth;resize();}});
    observer.observe(node);
    return()=>observer.disconnect();
  },[draft,session]);
  const toolToggle=useRef(null),toolSearch=useRef(null),toolScope=useRef(null),gpuToggle=useRef(null),queueToggle=useRef(null),chatQueueToggle=useRef(null),sessionToggle=useRef(null),sessionSearch=useRef(null);
  useEffect(()=>{if(showTools)(toolSearch.current || toolScope.current)?.focus({preventScroll:true});},[showTools]);
  function closeTools(focusTarget=toolToggle) {
    const url=new URL(location.href);
    if(url.searchParams.get("panel")==="jobs")url.searchParams.delete("job");
    if(["jobs","capabilities"].includes(url.searchParams.get("panel")))url.searchParams.delete("panel");
    url.searchParams.delete("category");
    url.searchParams.delete("search");
    history.replaceState(history.state,"",url);
    setShowTools(false);
    focusTarget.current?.focus();
  }
  function handleToolKeys(event){
    if(event.key==="Escape" && !event.nativeEvent.isComposing){
      event.preventDefault();closeTools();
    }
  }
  function closeFun(){setShowFunControl(false);toolToggle.current?.focus();}
  function select(next) {
    if(next && next===session)return;
    const url=new URL(location.href);
    if(next!==session){setShowFunControl(false);setShowKimodo(false);setKimodoProposal(null);setSeedProposal(null);setVideoFormId("");}
    if(next!==session && url.searchParams.get("panel")==="jobs")url.searchParams.delete("job");
    if(next)url.searchParams.set("session",next);else url.searchParams.delete("session");
    history.pushState(null,"",url);setSession(next);setView({});setHistoryPage(null);setQueue(null);setError("");setViewError("");setViewLoading(false);setTargetForm("");setTargetProposal("");
  }
  useEffect(()=>{const cb=()=>{setSearchMode(["jobs","capabilities"].includes(query().get("panel"))?query().get("panel"):"tools");setCategory(initialToolCategory());setSearch(query().get("search") || "");setShowTools(query().has("category") || query().has("search") || ["jobs","capabilities"].includes(query().get("panel")));setShowFunControl(false);setShowKimodo(false);setKimodoProposal(null);setSeedProposal(null);setVideoFormId("");setSession(query().get("session")||"");setView({});setHistoryPage(null);setQueue(null);setError("");setViewError("");setViewLoading(false);setTargetForm("");setTargetProposal("");};window.addEventListener("popstate",cb);return()=>window.removeEventListener("popstate",cb);},[]);
  useEffect(()=>{let active=true,timedOut=false;const controller=new AbortController();const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);setCatalogLoading(true);setCatalogError("");fetch(base+"tools",{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error("도구 목록을 불러올 수 없습니다.");return r.json();}).then(v=>{if(!Array.isArray(v) || v.some(item=>!item || typeof item!=="object" || ["id","label","category"].some(key=>typeof item[key]!=="string" || !item[key])))throw new Error("도구 목록 응답을 읽을 수 없습니다.");if(active)setTools(v)}).catch(e=>{if(active)setCatalogError(timedOut ? "도구 목록 조회 시간이 초과됐습니다. 다시 조회하세요." : e.message || "도구 목록을 불러올 수 없습니다.")}).finally(()=>{clearTimeout(timeout);if(active)setCatalogLoading(false)});
    return()=>{active=false;clearTimeout(timeout);controller.abort();};},[catalogRevision]);
  useEffect(()=>{
    let active=true,timedOut=false;const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setListPage(null);setSessions([]);setListError("");setListLoading(true);
    call(archived?"session-archived":"session-list",{...listRequest,limit:30},{signal:controller.signal}).then(page=>{
      if(!active)return;
      if(!validSessionListPage(page,listRequest))throw new Error("세션 목록 응답을 확인할 수 없습니다. 다시 검색하세요.");
      setSessions(page.sessions);setListPage(page);
    }).catch(problem=>{if(active)setListError(timedOut ? "대화 목록 조회 시간이 초과됐습니다." : problem.message);}).finally(()=>{clearTimeout(timeout);if(active)setListLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[archived,listRequest,refresh]);
  useEffect(()=>{setDraft(sessionStorage.getItem("hermes-draft-"+session) || "");},[session]);
  useEffect(()=>{
    let active=true,timer,controller;
    async function load() {
      controller=new AbortController();let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const payload={session_id:session,limit:CONVERSATION_PAGE_SIZE,...(historyPage || {})};
        const next=await call("session-view",payload,{signal:controller.signal});
        if(!validSessionViewPage(next,session,historyPage,CONVERSATION_PAGE_SIZE))throw new Error("대화 응답 형식을 확인할 수 없습니다.");
        if(active) {setView(next);setViewError("");}
      } catch(problem) {
        if(active)setViewError(timedOut ? "대화 조회 시간이 초과됐습니다." : problem.message);
      } finally {
        clearTimeout(timeout);
        if(active){setViewLoading(false);if(!historyPage)timer=setTimeout(load,3000);}
      }
    }
    if(session)load();
    return ()=>{active=false;clearTimeout(timer);controller?.abort();};
  },[session,historyPage,viewRevision]);
  useEffect(()=>{
    if(!targetForm || !(view.messages || []).some(message=>message.form_id===targetForm))return;
    const frame=requestAnimationFrame(()=>{const node=document.querySelector("[data-form-id=\""+targetForm+"\"]");if(node){node.scrollIntoView({block:"center",behavior:"smooth"});node.focus({preventScroll:true});setTargetForm("");}});
    return ()=>cancelAnimationFrame(frame);
  },[targetForm,view]);
  useEffect(()=>{
    if(!targetProposal || !(view.messages || []).some(message=>message.job_id===targetProposal))return;
    const frame=requestAnimationFrame(()=>{const node=document.querySelector('[data-job-id="'+targetProposal+'"]');if(node){node.scrollIntoView({block:"center",behavior:"smooth"});node.focus({preventScroll:true});setTargetProposal("");}});
    return ()=>cancelAnimationFrame(frame);
  },[targetProposal,view]);
  function openQueueMessage(step){
    const form=/^[a-f0-9]{32}$/.test(step.form_id || "");
    const proposal=/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(step.proposal_job_id || "");
    if((!form && !proposal) || !/^[a-f0-9]{64}$/.test(step.message_snapshot) || !Number.isInteger(step.message_offset) || step.message_offset<0)return false;
    if(view.snapshot!==step.message_snapshot)return false;
    const offset=Math.floor(step.message_offset/CONVERSATION_PAGE_SIZE)*CONVERSATION_PAGE_SIZE;
    if(form)setTargetForm(step.form_id);else setTargetProposal(step.proposal_job_id);
    setQueue(null);
    if(!(view.messages || []).some(message=>form ? message.form_id===step.form_id : message.job_id===step.proposal_job_id))changeHistory(offset ? {offset,snapshot:step.message_snapshot} : null);
    return true;
  }
  function changeHistory(page) {
    setError("");
    setViewError("");
    setViewLoading(true);
    if(page===historyPage)retryView(n=>n+1);
    else setHistoryPage(page);
  }
  function edit(v){setDraft(v);sessionStorage.setItem("hermes-draft-"+session,v)}
  const pendingKey = "hermes-pending-" + session;
  const pendingText = sessionStorage.getItem(pendingKey);
  const pending = readPendingSubmission(pendingText,session);
  const invalidPending = pendingText!==null && !pending;
  const [confirmWithdrawal,setConfirmWithdrawal]=useState(false);
  useEffect(()=>setConfirmWithdrawal(false),[session,pending?.request_id]);
  async function withdrawPending(){
    if(!pending || busy)return;
    setBusy(true);setError("");
    try{
      const result=await call("session-withdraw-unsubmitted",{session_id:pending.session_id,request_id:pending.request_id});
      if(result.session_id!==pending.session_id || result.request_id!==pending.request_id || !["withdrawn","accepted"].includes(result.state))throw new Error("철회 결과를 확인할 수 없습니다.");
      if(result.state==="accepted")throw new Error("이미 접수된 요청입니다. 대화 이력이나 채팅 대기열에서 확인하세요.");
      if(sessionStorage.getItem(pendingKey)!==pendingText)throw new Error("접수 기록이 변경됐습니다. 다시 확인하세요.");
      sessionStorage.removeItem(pendingKey);
      if(draft===pending.prompt)edit("");
      setConfirmWithdrawal(false);setRefresh(n=>n+1);
    }catch(problem){setError(problem.message || "철회 결과를 확인할 수 없습니다.");}
    finally{setBusy(false);}
  }
  const contextBlocking=Boolean(view.context?.operation && !["completed","failed","cancelled"].includes(view.context.operation.status));
  const submitDisabledReason = busy ? "요청을 접수하고 있습니다." : invalidPending ? "손상된 접수 기록을 확인하고 지워 주세요." : pending && pending.prompt!==draft ? "이전 요청의 접수 상태를 먼저 확인해 주세요." : !draft.trim() ? "메시지를 입력해 주세요." : "";
  async function send(retry=false){
    if(invalidPending || sending.current || (!retry && !draft.trim()))return;
    if(pending && pending.prompt!==draft && !retry)return;
    sending.current = true;
    setBusy(true);
    setError("");
    try {
      let prompt=draft;
      // Browser-local receipt is a candidate, not proof that it is the latest
      // submission across all generators or devices. Resolve it before use.
      if(!pending && session && /^(생성\s*등록했다|생성\s*접수했다|방금\s*생성했다)\.?\s*(확인해(?:라|줘|주세요)|상태\s*확인(?:해줘|해주세요)?)\.?$/i.test(prompt.trim())){
        const receipt=sessionStorage.getItem('kimodo-generation-receipt-'+session);
        if(receipt && /^[a-f0-9]{32}$/.test(receipt)){
          const record=await call('delegation-status',{request_id:receipt});
          if(record.state==='accepted' && record.service==='kimodo' && record.request_id===receipt && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(record.job_id || '')){
            prompt+='\n\n이 브라우저의 이 세션에서 확인된 Kimodo 접수 후보: '+record.job_id+'. 다른 생성기의 더 최근 작업인지는 확인되지 않았으니 대상을 명시하고 이 후보의 상태와 결과를 조회해 주세요.';
            edit(prompt);
          }
        }
      }
      const item = pending || {session_id:session || id(), request_id:id(), prompt, model_profile:'qwen3.8-27b'};
      sessionStorage.setItem(pendingKey, JSON.stringify(item));
      if (!session) await call("session-create", {session_id:item.session_id});
      if(item.model_profile==='qwen3.8-27b'){
        const resident=await call("resident-start",{session_id:item.session_id,request_id:item.request_id});
        if(resident.state!=='accepted' || !resident.id)throw new Error('Qwen 3.8 상주 모델 접수를 확인할 수 없습니다. 같은 요청의 상태를 확인하세요.');
      }
      await call("session-submit", item);
      sessionStorage.removeItem(pendingKey);
      const currentDraft=sessionStorage.getItem("hermes-draft-"+session) || "";
      const remaining=currentDraft===item.prompt?"":currentDraft;
      if(!remaining || session!==item.session_id)sessionStorage.removeItem("hermes-draft-"+session);
      if(remaining && session!==item.session_id)sessionStorage.setItem("hermes-draft-"+item.session_id,remaining);
      if ((query().get("session") || "") === session) {
        setDraft(remaining);
        setHistoryPage(null);
        if (session !== item.session_id) select(item.session_id);
        setArchived(false);
      }
      setListRequest(current=>({offset:0,query:current.query}));setRefresh(n => n + 1);
    } catch (e) {
      if ((query().get("session") || "") === session) setError(e.message);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function setAutomaticContext(enabled){
    if(!session || busy)return;
    const selected=session;setBusy(true);setError("");
    try{await call("session-context-settings",{session_id:selected,enabled});retryView(n=>n+1);}
    catch(problem){if((query().get("session") || "")===selected)setError(problem.message);}
    finally{setBusy(false);}
  }
  async function compactContext(){
    if(!session || busy)return;
    const selected=session, key="hermes-context-pending-"+selected;
    const operation=view.context?.operation;
    const requestId=sessionStorage.getItem(key) || (!operation?.job_id && operation?.request_id) || id();
    setBusy(true);setError("");
    try{
      if(typeof window.confirmGpuQueueStart!=="function")throw new Error("GPU 대기열 확인 기능을 불러오지 못했습니다.");
      if(!await window.confirmGpuQueueStart())return;
      sessionStorage.setItem(key,requestId);
      await call("session-context-compress",{session_id:selected,request_id:requestId});
      sessionStorage.removeItem(key);retryView(n=>n+1);
    }catch(problem){if((query().get("session") || "")===selected)setError(problem.message);}
    finally{setBusy(false);}
  }
  async function lifecycle(record,action){
    if(busy)return;
    if(action==="delete"&&!window.confirm((record.title || record.id)+" 대화 기록을 영구 삭제할까요?"))return;
    setBusy(true);
    try{
      const receipt=await call("session-"+action,{session_id:record.id,expected_update:record.updated_at});
      if(receipt.session_id!==record.id || receipt.operation!==action)throw new Error("세션 처리 결과를 확인하세요.");
      if(action==="delete"){
        sessionStorage.removeItem("hermes-draft-"+record.id);
        sessionStorage.removeItem("hermes-pending-"+record.id);
      }
      if(action==="restore"){setArchived(false);select(record.id)}else if(record.id===session)select("");
      setListRequest(current=>({offset:0,query:current.query}));setRefresh(n=>n+1);
    }catch(e){setError(e.message)}finally{setBusy(false);}
  }
  const [showGpu,setShowGpu]=useState(false);
  const [showHandoff,setShowHandoff]=useState(false);
  const handoffToggle=useRef(null);
  useEffect(()=>{if(showTools || showGpu || queue || generatorPanel || showKimodo || showFunControl)setShowHandoff(false);},[showTools,showGpu,queue,generatorPanel,showKimodo,showFunControl]);
  useEffect(()=>{setShowHandoff(false);},[session]);
  function closeHandoff(){setShowHandoff(false);handoffToggle.current?.focus();}
  function openHandoff(){if(showTools)closeTools();setShowGpu(false);setQueue(null);setGeneratorPanel(null);setShowKimodo(false);setShowFunControl(false);setShowHandoff(true);}
  const [searchMode,setSearchMode]=useState(()=>["jobs","capabilities"].includes(query().get("panel"))?query().get("panel"):"tools");
  const appendSelection=(label,id)=>{edit([draft,label+" "+id].filter(Boolean).join("\n"));closeTools(text);};
  function openFunFromTools(){
    if(showTools)closeTools();
    setShowGpu(false);setShowKimodo(false);setGeneratorPanel(null);setQueue(null);
    if(!showFunControl){setSeedProposal(null);setVideoFormId("");setShowFunControl(true);}
  }
  function openGenerator(tool){
    if(showTools)closeTools();
    setShowGpu(false);setQueue(null);setShowKimodo(false);setShowFunControl(false);
    setMountedGenerators(items=>items.includes(tool.id)?items:[...items,tool.id]);
    setGeneratorPanel({id:tool.id,label:tool.label});
  }
  function closeGenerator(){setGeneratorPanel(null);toolToggle.current?.focus();}
  function closeGpu(){setShowGpu(false);gpuToggle.current?.focus();}
  function closeQueue(){const trigger=queue?.mode==="chat"?chatQueueToggle:queueToggle;setQueue(null);trigger.current?.focus();}
  function openKimodo(inputs=null) {
    if(showTools)closeTools();
    setShowGpu(false);setQueue(null);setGeneratorPanel(null);setShowFunControl(false);
    if(inputs){setKimodoProposal(inputs);setKimodoRevision(n=>n+1);}
    setKimodoMounted(true);setShowKimodo(true);
  }
  function closeKimodo(){setShowKimodo(false);toolToggle.current?.focus();}
  function chooseTool(label,identifier) {
    edit([draft,"사용할 도구: "+label+" ("+identifier+")\n"].filter(Boolean).join("\n"));
    closeTools(text);
  }
  function reviewLink(path){
    const url=new URL(path,location.origin);
    if(session)url.searchParams.set("session",session);
    return url.pathname+url.search;
  }
  function changeCategory(value){
    const url=new URL(location.href);
    url.searchParams.set("category",value);
    history.replaceState(null,"",url);setCategory(value);
  }
  const toolFieldLabels={"sound-management":"음악·효과음","animation-tool":"모션·포즈·영상·편집","image-generation":"이미지 생성","map-review":"맵·에셋 관리","game-ui":"게임 UI","model-management":"모델 관리","writer-agent":"텍스트·번역"};
  const categories=new Map(tools.map(tool=>[tool.category,toolFieldLabels[tool.category] || tool.category_label]));
  const terms=search.trim().toLowerCase().split(/\s+/);
  const toolSearchAliases={"kimodo-generator":"키모도 김도", "wan22-fun-control-generator":"완 펀 컨트롤 원 펀 콘트롤"};
  const matchedTools=tools.filter(tool=>(category==="all" || tool.category===category) &&
    terms.every(term=>[tool.label,tool.id,tool.description,toolSearchAliases[tool.id] || ""].join(" ").toLowerCase().includes(term)));
  const chosen=query().get("tool");
  const [folded,setFolded]=useState(()=>localStorage.getItem("hermes-session-folded")==="true");
  function closeMobileSessions(){setFolded(true);requestAnimationFrame(()=>sessionToggle.current?.focus());}
  const [sidebarWidth,setSidebarWidth]=useState(()=>{
    const saved=Number(localStorage.getItem("hermes-session-width"));
    return saved>=200 && saved<=600?saved:288;
  });
  const [panelWidth,setPanelWidth]=useState(()=>{const saved=Number(localStorage.getItem("hermes-panel-width"));return saved>=260 && saved<=1200?saved:480;});
  const [viewportWidth,setViewportWidth]=useState(()=>window.innerWidth);
  useEffect(()=>{const update=()=>setViewportWidth(window.innerWidth);window.addEventListener("resize",update);return()=>window.removeEventListener("resize",update);},[]);
  const panelOpen=Boolean(showFunControl || showKimodo || showTools || showGpu || showHandoff || queue || generatorPanel);
  const sidebarMax=Math.min(600,Math.floor(viewportWidth*.48),panelOpen && viewportWidth>=1000 ? Math.max(200,viewportWidth-340-320-8) : 600);
  const sidebarActual=Math.min(sidebarWidth,sidebarMax);
  const panelMin=Math.min(260,viewportWidth);
  const sidebarOccupied=folded?0:sidebarActual+8;
  const panelMax=Math.max(panelMin,Math.min(1200,viewportWidth>=1000?viewportWidth-sidebarOccupied-320:viewportWidth));
  const panelActual=Math.max(panelMin,Math.min(panelWidth,panelMax));
  function resizePanel(width){setPanelWidth(Math.max(panelMin,Math.min(panelMax,Math.round(width))));}
  useEffect(()=>{localStorage.setItem("hermes-panel-width",String(panelWidth));},[panelWidth]);
  function resizeSidebar(width){
    setSidebarWidth(Math.max(200,Math.min(sidebarMax,Math.round(width))));
  }
  useEffect(()=>{localStorage.setItem("hermes-session-width",String(sidebarWidth));},[sidebarWidth]);
  return <main className={"hermes-chat"+(folded?" sessions-folded":"")+(panelOpen?" fun-panel-open":"")} style={{"--sessions-width":sidebarActual+"px","--panel-width":panelActual+"px"}}>
    <aside id="hermes-session-list" hidden={folded} aria-label="대화 세션">
      <div className="session-sidebar-heading"><h2>{archived?"보관된 대화":"대화 세션"}</h2><button type="button" disabled={busy} onClick={()=>{select("");setArchived(false);resetSessionList();if(window.innerWidth<=700)closeMobileSessions();}}>+ 새 대화</button><button type="button" className="session-sidebar-close" onClick={closeMobileSessions}>닫기</button></div>
      <div className="session-sidebar-tabs" role="group" aria-label="대화 목록 선택"><button type="button" disabled={busy} aria-pressed={!archived} onClick={()=>{if(archived){resetSessionList();setArchived(false);}}}>대화 목록</button><button type="button" disabled={busy} aria-pressed={archived} onClick={()=>{if(!archived){resetSessionList();setArchived(true);}}}>보관함</button></div>
      <form className="session-search" onSubmit={e=>{e.preventDefault();setListRequest({offset:0,query:sessionQuery.trim()});}}>
        <label htmlFor="hermes-session-search">대화 검색</label>
        <div className="session-search-row"><input id="hermes-session-search" ref={sessionSearch} maxLength={100} placeholder="제목·내용·ID" title="제목, 메시지 또는 세션 ID 검색" value={sessionQuery} onChange={e=>setSessionQuery(e.target.value)}/>
          <button type="submit">검색</button></div>
        {(sessionQuery || listRequest.query) && <button type="button" onClick={()=>{resetSessionList();sessionSearch.current?.focus();}}>초기화</button>}
      </form>
      {sessionQuery.trim()!==listRequest.query && <p className="session-list-count" role="status">검색어가 변경되었습니다. 검색을 눌러 목록에 적용하세요.</p>}
      {listError && <div ref={listErrorRef} tabIndex={-1} role="alert"><p>{listError.includes("시간이 초과") ? listError : listRequest.snapshot ? "목록이 변경되었거나 페이지를 불러오지 못했습니다. 처음부터 다시 조회하세요." : "목록을 불러오지 못했습니다."}</p><button type="button" onClick={()=>{listFocusPending.current=true;if(listRequest.snapshot)setListRequest({offset:0,query:listRequest.query});else setRefresh(n=>n+1);}}>{listRequest.snapshot ? "처음부터 다시 조회" : "다시 시도"}</button></div>}
      {listLoading && <p role="status">대화 목록을 불러오는 중…</p>}
      {listPage && Number.isInteger(listPage.total) && <p ref={listResultRef} tabIndex={-1} className="session-list-count" role="status">{listRequest.query?<>‘{listRequest.query}’ 검색 결과</>:archived?"보관된 대화":"전체 대화"} {listPage.total}개{listPage.unreadable_count>0 && " · 읽을 수 없는 세션 "+listPage.unreadable_count+"개 제외"}</p>}
      {listRequest.query && sessions.some(s=>!s.title) && <p className="session-list-count">검색 결과는 세션 ID로 표시됩니다. 선택하면 대화 제목과 내용을 확인할 수 있습니다.</p>}
      {!listLoading && !listError && listPage && sessions.length===0 && <p className="session-list-empty">{listRequest.query?"검색 결과가 없습니다. 검색어를 바꿔 보세요.":archived?"보관된 대화가 없습니다.":"아직 대화가 없습니다. 새 대화를 시작해 보세요."}</p>}
      <div className="session-list-items">{sessions.map(s=><div className="session" key={s.id}><button type="button" className="session-select" disabled={busy} aria-current={s.id===session?"page":undefined} onClick={()=>{if(archived)lifecycle(s,"restore");else{select(s.id);if(window.innerWidth<=700)closeMobileSessions();}}}><span>{s.title || "세션 ID · "+s.id}</span>{s.updated_at && !Number.isNaN(new Date(s.updated_at).getTime()) && <small>최근 변경 · {new Date(s.updated_at).toLocaleString("ko-KR",{dateStyle:"short",timeStyle:"short"})}</small>}</button>
        <button type="button" className="session-action" disabled={busy} aria-label={(s.title || "세션 ID "+s.id)+" "+(archived?"영구 삭제":"보관")} onClick={()=>lifecycle(s,archived?"delete":"archive")}>{archived?"삭제":"보관"}</button></div>)}</div>
      {listPage && (listRequest.offset>0 || listPage.next_offset!=null) && <nav className="session-list-pagination" aria-label="세션 목록 페이지">
        <button type="button" disabled={!listRequest.offset} onClick={()=>{listFocusPending.current=true;setListRequest({...listRequest,offset:Math.max(0,listRequest.offset-30),snapshot:listPage.snapshot});}}>이전</button>
        <span>{Math.floor(listRequest.offset/30)+1} 페이지</span>
        <button type="button" disabled={listPage.next_offset==null} onClick={()=>{listFocusPending.current=true;setListRequest({...listRequest,offset:listPage.next_offset,snapshot:listPage.snapshot});}}>다음</button>
      </nav>}</aside>
    {!folded && <div className="session-divider" role="separator" tabIndex={0} aria-label="세션 목록 너비" aria-describedby="session-resize-help" title="드래그하거나 좌우 화살표로 너비 조절 · Home 최소 · End 최대"
      aria-controls="hermes-session-list" aria-orientation="vertical" aria-valuemin={200} aria-valuemax={sidebarMax}
      aria-valuenow={sidebarActual}
      onPointerDown={event=>{if(event.button===0){event.preventDefault();event.currentTarget.focus();event.currentTarget.setPointerCapture(event.pointerId);}}}
      onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))resizeSidebar(event.clientX-event.currentTarget.parentElement.getBoundingClientRect().left);}}
      onKeyDown={event=>{
        const current=event.currentTarget.previousElementSibling.getBoundingClientRect().width;
        const widths={ArrowLeft:current-16,ArrowRight:current+16,Home:200,End:600};
        if(Object.hasOwn(widths,event.key)){event.preventDefault();resizeSidebar(widths[event.key]);}
      }}><span id="session-resize-help" className="generator-visually-hidden">드래그하거나 좌우 화살표로 너비를 조절합니다. Home은 최소, End는 최대 너비입니다.</span></div>}
    <article><header><button ref={sessionToggle} aria-controls="hermes-session-list" aria-expanded={!folded} onClick={()=>{
      localStorage.setItem("hermes-session-folded",String(!folded));setFolded(!folded);
    }}>{folded?"세션 목록 펼치기":"세션 목록 접기"}</button><h1>{view.title || "헤르메스와 대화"}</h1></header>


    <ProposalActions.Provider value={{append:appendSelection,openStep:inputs=>openKimodo(inputs),openQueue:()=>{if(showTools)closeTools();setShowGpu(false);setShowKimodo(false);setShowFunControl(false);setGeneratorPanel(null);setQueue({run:""});},openVideoForm:formId=>{if(showTools)closeTools();setShowGpu(false);setQueue(null);setShowKimodo(false);setGeneratorPanel(null);setSeedProposal(null);setVideoFormId(formId);setVideoFormRevision(n=>n+1);setShowFunControl(true);},openSeedForm:proposal=>{if(showTools)closeTools();setShowGpu(false);setQueue(null);setShowKimodo(false);setGeneratorPanel(null);setVideoFormId("");setSeedProposal(proposal);setVideoFormRevision(n=>n+1);setShowFunControl(true);},openJobForm:job_id=>{if(showTools)closeTools();setShowGpu(false);setQueue(null);setShowKimodo(false);setGeneratorPanel(null);setVideoFormId("");setSeedProposal({job_id,reuse:true});setVideoFormRevision(n=>n+1);setShowFunControl(true);}}}><Conversation key={session} view={view} historyPage={view.offset>0 ? {offset:view.offset,snapshot:view.snapshot} : null} changeHistory={changeHistory}/></ProposalActions.Provider>{viewLoading && <p role="status">대화를 불러오는 중입니다. 현재 화면은 이전 조회 결과입니다.</p>}{viewError && <div role="alert"><p>{viewError.includes("세션 이력이 변경") ? (historyPage ? "대화 이력이 변경되었습니다. 최신 대화를 다시 불러온 뒤 이전 메시지를 조회하세요." : "대화 이력이 변경되었습니다. 작업·대기열을 다시 조회한 뒤 관련 대화를 열어 주세요.") : viewError.includes("조회 시간이 초과") ? "대화 조회 시간이 초과됐습니다. 다시 시도하세요." : "대화를 불러오지 못했습니다. 연결 상태를 확인해 주세요."}{view.id && " 표시된 대화는 마지막으로 조회한 내용입니다."}</p><div className="conversation-error-actions"><button type="button" onClick={()=>{document.querySelector(".thread .viewport")?.focus({preventScroll:true});retryView(n=>n+1);}}>다시 시도</button>{historyPage && <button type="button" onClick={()=>{changeHistory(null);document.querySelector(".thread .viewport")?.focus({preventScroll:true});}}>최신 대화 불러오기</button>}</div></div>}{error&&<p role="alert">{error}</p>}

    <form onSubmit={e=>{e.preventDefault();send()}}>
    {session && view.context && <details name="composer-popover" className="composer-context"><summary>대화 문맥{view.context.usage && " · "+(view.context.usage.tokens_after ?? view.context.usage.tokens).toLocaleString()+" 토큰"}{view.context.operation && ["queued","running","unknown"].includes(view.context.operation.status) && " · 정리 진행 중"}</summary><section className="composer-context-panel" aria-label="대화 문맥 정리">
      <p>이전 대화를 요약해 이후 요청의 문맥으로 사용합니다. 대화 기록은 유지됩니다.</p>
      <label><input type="checkbox" checked={view.context.automatic} disabled={busy} onChange={event=>setAutomaticContext(event.target.checked)}/> 자동 대화 정리</label>{" "}
      <button type="button" title={!view.message_count?"정리할 대화가 없습니다.":undefined} disabled={busy || !view.message_count || Boolean(view.context.operation?.job_id && ["queued","running","unknown"].includes(view.context.operation.status))} onClick={compactContext}>
        {view.context.operation && !view.context.operation.job_id ? "정리 접수 다시 확인" : "대화 정리"}</button>
      {view.context.operation && <small role="status"> 정리 작업: {statusLabels[view.context.operation.status] || view.context.operation.status}{view.context.operation.job_id && <> · <a href={jobLink(view.context.operation.job_id,session)}>작업 상세</a></>}</small>}
      {view.context.usage && <small> · 최근 입력 추정 {(view.context.usage.tokens_after ?? view.context.usage.tokens).toLocaleString()} 토큰{view.context.usage.threshold && " / 정리 기준 "+view.context.usage.threshold.toLocaleString()} (시스템·도구 지시 포함)</small>}
      {view.context.usage?.state==="compressed" && <small role="status"> · 대화 정리 완료</small>}
      {view.context.usage?.state==="compressing" && <small role="status"> · 대화 정리 중</small>}
      {view.context.usage?.state==="unchanged" && <small role="status"> · 정리할 수 있는 대화 범위가 없습니다.</small>}
      {view.context.checkpoint && <details><summary>대화 정리 내용 · {view.context.checkpoint.count}개 지시{view.context.checkpoint.created_at && " · "+view.context.checkpoint.created_at}</summary><pre>{view.context.checkpoint.summary || "정리된 대화에 별도 요약 표시가 없습니다."}</pre></details>}
    </section></details>}
    {session && <ResidentModelStatus key={session} session={session}/>}
    {session && <button type="button" ref={handoffToggle} aria-controls="hermes-side-panel" aria-expanded={showHandoff} onClick={()=>showHandoff?closeHandoff():openHandoff()}>GPU 양도 이력</button>}
    <button type="button" ref={gpuToggle} aria-expanded={showGpu} onClick={()=>{if(showTools)closeTools();setShowGpu(value=>!value);}}>GPU 프로세스 정보</button>
    {session&&<button type="button" ref={queueToggle} aria-expanded={Boolean(queue && queue.mode!=="chat" && !showTools && !showGpu)} onClick={()=>{if(showTools)closeTools();setShowGpu(false);setQueue(value=>value && value.mode!=="chat" && !showTools && !showGpu ? null : {run:""});}}>작업 대기열</button>}{session&&<button type="button" ref={chatQueueToggle} aria-expanded={queue?.mode==="chat" && !showTools && !showGpu} onClick={()=>{if(showTools)closeTools();setShowGpu(false);setQueue(value=>value?.mode==="chat" && !showTools && !showGpu ? null : {run:"",mode:"chat"});}}>채팅 대기열{view.chat_queue?.length ? " · "+view.chat_queue.length : ""}</button>}{chosen&&<button type="button" onClick={()=>edit(draft+"\n사용할 도구: "+chosen+"\n")}>{chosen} 요청에 추가</button>}
    <button type="button" ref={toolToggle} aria-expanded={showTools} onClick={()=>{setShowGpu(false);if(showTools)closeTools();else setShowTools(true)}}>도구 탐색</button>
    {pending && <small>접수 확인 중인 요청의 모델: {pending.model_profile || '자동 선택'}</small>}
    {pending && !confirmWithdrawal && <button type="button" disabled={busy} onClick={()=>setConfirmWithdrawal(true)}>미접수 요청 철회</button>}
    {pending && confirmWithdrawal && <div role="group" aria-label="미접수 요청 철회 확인"><p>미접수인 경우에만 철회하며 기존 작업은 중단하지 않습니다. 작성한 이전 요청은 지워집니다.</p><button type="button" disabled={busy} onClick={()=>setConfirmWithdrawal(false)}>취소</button><button type="button" disabled={busy} onClick={withdrawPending}>미접수 확인 후 철회</button></div>}
    <textarea ref={text} aria-label="메시지" aria-describedby={submitDisabledReason ? "composer-submit-reason" : undefined} placeholder="헤르메스에게 메시지 보내기" value={draft} disabled={busy} onChange={e=>edit(e.target.value)} title="Enter로 보내기 · Shift+Enter로 줄바꿈" onKeyDown={event=>{
      if(event.key!=="Enter" || event.shiftKey || event.altKey || event.nativeEvent.isComposing || event.nativeEvent.keyCode===229)return;
      event.preventDefault();
      if(!event.repeat)event.currentTarget.form.querySelector('button[type="submit"]').click();
    }}/>
    {invalidPending && <div role="alert">이 탭의 접수 기록을 읽을 수 없습니다. 대화 이력에서 이전 요청의 접수 여부를 확인하세요.
      <button type="button" onClick={()=>{sessionStorage.removeItem(pendingKey);setRefresh(n=>n+1);}}>탭의 손상된 접수 기록 지우기</button></div>}
    {pending && pending.prompt!==draft && <details><summary>접수 확인이 필요한 이전 요청</summary>
      <pre>{pending.prompt}</pre><button type="button" disabled={busy} onClick={()=>send(true)}>이전 요청 접수 다시 확인</button></details>}
    {pending && pending.prompt===draft && <small className="composer-reason" role="status">이전 요청의 접수 여부를 같은 요청 ID로 다시 확인합니다.</small>}
    {submitDisabledReason && <small id="composer-submit-reason" className={submitDisabledReason === "메시지를 입력해 주세요." ? "composer-reason-hidden" : "composer-reason"} role="status">{submitDisabledReason}</small>}
    <button type="submit" disabled={Boolean(submitDisabledReason)} title={submitDisabledReason || undefined}>{busy?"접수 중":pending && pending.prompt===draft?"접수 다시 확인":"보내기"}</button></form></article>
    {(showFunControl || showKimodo || showTools || showGpu || showHandoff || queue || generatorPanel || funMounted || kimodoMounted || mountedGenerators.length>0) && <SidePanel hidden={!panelOpen} width={panelActual} minWidth={panelMin} maxWidth={panelMax} onResize={resizePanel} title={showHandoff?"GPU 양도 이력":showTools?"도구 탐색":showGpu?"GPU 프로세스 정보":queue?(queue.mode==="chat"?"채팅 대기열":"작업 대기열"):generatorPanel?generatorPanel.label:showKimodo?"Kimodo 모션 생성":"Wan Fun Control"} subtitle={showHandoff?"이 대화의 양도와 모델 복구 상태":showTools?"도구와 관리 기능 찾기":showGpu?"GPU 사용 현황":queue?(queue.mode==="chat"?"이 세션의 대기 요청":"진행 상태와 결과"):"생성 입력 검토"} onClose={showHandoff?closeHandoff:showTools?()=>closeTools():showGpu?closeGpu:queue?closeQueue:generatorPanel?closeGenerator:showKimodo?closeKimodo:closeFun} onKeyDown={showTools?handleToolKeys:event=>{if(event.key==="Escape" && !event.nativeEvent.isComposing){event.preventDefault();showHandoff?closeHandoff():showGpu?closeGpu():queue?closeQueue():generatorPanel?closeGenerator():showKimodo?closeKimodo():closeFun();}}}>
    {showHandoff && session && <GpuHandoffHistory key={session} session={session}/>}
    {showTools && <div className="tool-drawer-content">
      <label className="search-scope">탐색 대상 <select ref={toolScope} value={searchMode} onChange={e=>setSearchMode(e.target.value)}>
        <optgroup label="도구와 기능"><option value="tools">도구 목록</option><option value="capabilities">관리 명령 검색</option></optgroup>
        <optgroup label="저장된 자료"><option value="expressions">표정 프리셋</option><option value="billboards">빌보드 에셋</option><option value="keyframes">Kimodo 키프레임</option></optgroup>
        <optgroup label="작업과 검수 이력"><option value="history">생성 이력</option><option value="jobs">운영 작업 이력</option><option value="anchors">앵커 검수 이력</option></optgroup>
        <optgroup label="시스템 상태"><option value="services">서비스 등록 상태</option><option value="content">콘텐츠 DB 상태</option></optgroup>
      </select></label>
      <p className="generator-help-text">탐색 대상은 찾을 정보의 종류입니다.{searchMode==="tools" && " 도구 분야는 목록을 작업 영역별로 좁힙니다."}</p>
      {["capabilities","expressions","keyframes","services"].includes(searchMode) && <input ref={toolSearch} aria-label={{capabilities:"관리 기능 검색",expressions:"표정 프리셋 검색",keyframes:"Kimodo 키프레임 검색",services:"서비스 검색"}[searchMode]} maxLength={100} placeholder="이름·기능 검색" value={search} onChange={e=>setSearch(e.target.value)}/>}
      {["capabilities","expressions","keyframes","services"].includes(searchMode) && search && <button type="button" onClick={()=>{setSearch("");requestAnimationFrame(()=>toolSearch.current?.focus());}}>검색어 지우기</button>}
      {searchMode==="expressions" && <ExpressionCatalog key={search} query={search} choose={appendSelection}/>}
      {searchMode==="anchors" && <AnchorHistory/>}
      {searchMode==="billboards" && <BillboardCatalog choose={appendSelection}/>}
      {searchMode==="keyframes" && <KeyframeCatalog query={search} choose={appendSelection}/>}
      {searchMode==="content" && <ContentDatabaseStatus/>}
      {searchMode==="jobs" && <OperationsJobs key={session+":"+(query().get("job") || "")} session={session} linkedJob={query().get("panel")==="jobs"?query().get("job"):null} linkedStatus={(view.messages || []).find(message=>message.job_id===query().get("job"))?.job?.status?.status}/>}
      {searchMode==="history" && <SourceHistory session={session} choose={appendSelection} tools={tools}/>}
      {searchMode==="services" && <ServiceRegistry query={search}/>}
      {searchMode==="capabilities" && <CapabilitySearch search={search} choose={chooseTool}/>}
      {searchMode==="tools" && <label>도구 분야 <select value={category} onChange={e=>changeCategory(e.target.value)}>
        <option value="all">전체</option>
        {category!=="all" && !categories.has(category) && <option value={category}>{category}</option>}
        {Array.from(categories,([id,label])=><option key={id} value={id}>{label || id}</option>)}
      </select></label>}
      {searchMode==="tools" && catalogError && <div role="alert"><p>{catalogError}</p><button type="button" onClick={()=>{toolSearch.current?.focus();retryCatalog(value=>value+1);}}>도구 목록 다시 조회</button></div>}
      {searchMode==="tools" && <Command label="도구 검색" shouldFilter={false} loop onKeyDownCapture={e=>{
        if(e.key==="Enter" && (e.nativeEvent.isComposing || e.nativeEvent.keyCode===229))e.stopPropagation();
      }}>
        <Command.Input ref={toolSearch} aria-label="도구 검색" placeholder="이름·기능 검색" maxLength={100} value={search} onValueChange={setSearch}/>
        {!catalogError && <p role="status">{catalogLoading ? "도구 목록을 불러오는 중입니다." : tools.length===0 ? "등록된 도구가 없습니다." : <>검색 결과 {matchedTools.length}건{!matchedTools.length && " · 검색어나 도구 분야를 바꿔 보세요."}</>}</p>}
        {search && <button type="button" onKeyDown={event=>{if(event.key==="Enter" || event.key===" ")event.stopPropagation();}} onClick={()=>{setSearch("");requestAnimationFrame(()=>toolSearch.current?.focus());}}>검색어 지우기</button>}
        {category!=="all" && <button type="button" onKeyDown={event=>{if(event.key==="Enter" || event.key===" ")event.stopPropagation();}} onClick={()=>{changeCategory("all");requestAnimationFrame(()=>toolSearch.current?.focus());}}>도구 분야 초기화</button>}
        <Command.List label="검색 결과">
          {matchedTools.map(tool=><Command.Group className="tool-match" key={tool.id} heading={tool.label}>
            <Command.Item aria-label={tool.label+" · 대화에 추가"} value={tool.id+"/chat"} onSelect={()=>chooseTool(tool.label,tool.id)}>대화에 추가</Command.Item>
            {session && tool.id==="wan22-fun-control-generator" && <Command.Item aria-label={tool.label+" · 생성 폼 열기"} value={tool.id+"/video-form"} onSelect={openFunFromTools}>생성 폼 열기</Command.Item>}
            {session && embeddedGenerators[tool.id] && <Command.Item aria-label={tool.label+" · 생성 폼 열기"} value={tool.id+"/generator-form"} onSelect={()=>openGenerator(tool)}>생성 폼 열기</Command.Item>}
            {session && tool.id==="kimodo-generator" && <Command.Item aria-label={tool.label+" · 생성 폼 열기"} value={tool.id+"/generator-form"} onSelect={()=>openKimodo()}>생성 폼 열기</Command.Item>}
            {tool.review_path && <Command.Item aria-label={tool.label+" · 화면 열기"} value={tool.id+"/page"} onSelect={()=>location.assign(reviewLink(tool.review_path))}>화면 열기</Command.Item>}
          </Command.Group>)}
        </Command.List>
      </Command>}
    </div>}
      {showGpu && !showTools && <GpuPanel embedded/>}
      {queue?.mode==="chat" && session && !showTools && !showGpu && <ChatQueuePanel key={session} session={session}/>}
      {queue && queue.mode!=="chat" && session && !showTools && !showGpu && <QueuePanel key={session+queue.run} session={session} initialRun={queue.run} filterCache={queueFilterCache} call={call} openMessage={openQueueMessage} choose={appendSelection}/>}
      {mountedGenerators.map(id=>{const Generator=embeddedGenerators[id];return <div key={id} hidden={showTools || showGpu || Boolean(queue) || generatorPanel?.id!==id} className="embedded-generator"><Generator embedded session={session}/></div>;})}
      {kimodoMounted && <div hidden={!showKimodo || showTools || showGpu || Boolean(queue) || Boolean(generatorPanel)} className="embedded-generator"><KimodoPage key={session+":"+kimodoRevision} embedded session={session} initialInputs={kimodoProposal} onChoose={(label,value)=>{edit([draft,label+" "+value].filter(Boolean).join("\n"));text.current?.focus();}}/></div>}
      {funMounted && <div hidden={!showFunControl || showTools || showGpu || Boolean(queue) || showKimodo || Boolean(generatorPanel)}><FunControlPage key={session+videoFormId+videoFormRevision} embedded session={session} restoreFormId={videoFormId} seedProposal={seedProposal} onSaved={()=>setRefresh(n=>n+1)}/></div>}
    </SidePanel>}
    </main>
}
const pages = {
  "/management/frame/kimodo-generator": KimodoPage,
  "/management/assistant/qwen-archive": QwenArchive,
  "/management/assistant/kimodo": KimodoPage,
  "/management/frame/effect-editor": EffectEditor,
  "/management/frame/sprite-sheet-editor": SpriteSheetEditor,
  "/management/assistant/sprite-sheets": SpriteSheetEditor,
  "/management/assistant/effects": EffectEditor,
  "/management/frame/building-editor": BuildingEditor,
  "/management/frame/asset-editor": BillboardCatalog,
  "/management/assistant/billboards": BillboardCatalog,
  "/management/assistant/buildings": BuildingEditor,
  "/management/assistant/field-map": MapReview,
  "/management/assistant/town-map": MapReview,
  "/management/assistant/battlefield": BattlefieldReview,
  "/management/frame/wan22-fun-control-generator": FunControlPage,
  "/management/assistant/fun-control": FunControlPage,
  "/management/frame/wan22-vace-generator": VacePage,
  "/management/assistant/vace": VacePage,
  "/management/frame/wan22-animate2-generator": AnimatePage,
  "/management/frame/writer-agent": WriterPage,
  "/management/frame/flux-expression-generator": FluxImagePage,
  "/management/frame/flux-seamless-generator": FluxImagePage,
  "/management/frame/flux-character-generator": FluxImagePage,
  "/management/frame/flux-building-generator": FluxImagePage,
  "/management/frame/flux-mannequin-generator": FluxImagePage,
  "/management/frame/flux-billboard-generator": FluxImagePage,
  "/management/frame/flux-prop-generator": FluxImagePage,
  "/management/frame/flux-vegetation-generator": FluxImagePage,
  "/management/frame/flux-image-generator": FluxImagePage,
  "/management/assistant/flux-image": FluxImagePage,
  "/management/frame/music-heartmula": HeartmulaPage,
  "/management/assistant/heartmula": HeartmulaPage,
  "/management/frame/sfx-dasheng-audiogen": SoundEffectPage,
  "/management/assistant/sound-effect": SoundEffectPage,
  "/management/assistant/dwpose": DwposePage,
  "/management/frame/dwpose-generator": DwposePage,
  "/management/assistant/models": ModelPage,
  "/management/frame/model-management": ModelPage,
  "/management/frame/world-map": WorldMap,
  "/management/frame/prompt-translation": TranslationPage,
  "/management/assistant/translation": TranslationPage,
};
const Page = pages[location.pathname.replace(/\/$/, "")] || App;
createRoot(document.getElementById("root")).render(<Page/>);
