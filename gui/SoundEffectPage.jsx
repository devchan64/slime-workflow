import usePageTitle from "./usePageTitle.js";
import {audioInputIssues,audioSeedValid,audioDurationValid} from "./audioInputIssues.mjs";
import {createConfirmationGate} from "./confirmationGate.mjs";
import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import ActionButton from "./ActionButton.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import MusicExamples from "./MusicExamples.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import {openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {readGenerationProposal,audioProposalInputs} from "./generationProposal.mjs";
import {restoreLostFocus,visibleFocusTarget} from "./restoreLostFocus.mjs";
import {validGenerationJobId} from "./generationJobId.mjs";
import {ActiveGeneratorJobStatus} from "./ActiveGeneratorJob.jsx";

export function HeartmulaPage({embedded=false,session=""}={}){return <AudioGeneratorPage music embedded={embedded} session={session}/>;}
export default function SoundEffectPage({embedded=false,session=""}={}){return <AudioGeneratorPage embedded={embedded} session={session}/>;}
export function AudioNotice({notice,error}){return notice ? <p role={error ? "alert" : "status"}>{notice}</p> : null;}
export function AudioReviewPending({busy,review}){return busy && !review ? <p role="status">요청을 검토하고 있습니다. 잠시 기다려 주세요.</p> : null;}
export function AudioActiveStatus({statusRef,retryRef,loading,notice,error,activeId,job,onOpen,onRetry}){
  return <ActiveGeneratorJobStatus statusRef={statusRef} retryRef={retryRef} loading={loading} notice={notice} error={error} activeId={activeId} job={job} onOpen={onOpen} onRetry={onRetry} showRetry={Boolean(error)}/>;
}

function AudioGeneratorPage({music=false,embedded=false,session:embeddedSession=""}){
  usePageTitle(music ? "HeartMuLa 음악 생성" : "Dasheng 효과음 생성",embedded);
  const service=music?"music-heartmula":"sfx-dasheng-audiogen";
  const formPath="/management/assistant/"+(music?"heartmula-input":"sfx-input");
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [form,setForm]=useState(null),[review,setReview]=useState(null);
  const [inputError,setInputError]=useState(""),[inputRevision,retryInput]=useState(0);
  const inputRetryRef=useRef(null),inputRetryFocus=useRef(false),inputPending=useRef(true);
  const formRef=useRef(form);
  formRef.current=form;
  const tagCount=form?.prompt?.split(",").filter(tag=>tag.trim()).length || 0;
  const [busy,setBusy]=useState(false),[notice,setNoticeState]=useState(""),[noticeError,setNoticeError]=useState(false),[model,setModel]=useState(null),[modelError,setModelError]=useState("");
  function setNotice(value,error=false){setNoticeError(error);setNoticeState(value);}
  const reviewEpoch=useRef(0),interactionRef=useRef({busy,review});
  interactionRef.current={busy,review};
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [activeError,setActiveError]=useState(""),[activeNotice,setActiveNotice]=useState(""),[activeId,setActiveId]=useState(""),[activeRevision,retryActive]=useState(0),[activeLoading,setActiveLoading]=useState(false);
  const activePending=useRef(false),activeRetryRef=useRef(null),activeRetryFocus=useRef(false),activeErrorRef=useRef(null);
  const [historyRevision,setHistoryRevision]=useState(0);
  const handoff=useGpuHandoff(session,service,setJob,setNotice);
  const submitting=useRef(false),confirmation=useRef(null);
  if(!confirmation.current)confirmation.current=createConfirmationGate();
  const reviewRef=useRef(null),reviewOrigin=useRef(null),reviewRequest=useRef(null),restoreFrame=useRef(null),promptRef=useRef(null),inputRegion=useRef(null),historyRegion=useRef(null),resultRegion=useRef(null),prepareRef=useRef(null),prepareDetails=useRef(null),prepareSummary=useRef(null);
  useEffect(()=>()=>{const request=reviewRequest.current;reviewRequest.current=null;request?.abort();if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);},[]);
  const prepareReasonId=useId(),durationErrorId=useId(),inputLockId=useId(),historyLockId=useId(),tagCountId=useId();
  const prepareReason=busy ? "다른 요청을 처리하고 있습니다. 완료될 때까지 기다리세요." : review ? "현재 요청의 확인을 마치거나 취소하세요." : handoff.id ? "진행 중인 GPU 양도 요청을 확인하세요." : "";
  useEffect(()=>{if(!review)return;const origin=reviewOrigin.current;const frame=requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===origin) && reviewRef.current?.isConnected)reviewRef.current.focus();});return ()=>cancelAnimationFrame(frame);},[review]);
  useEffect(()=>{
    if(!inputRetryFocus.current || (!form && !inputError))return;
    inputRetryFocus.current=false;
    const frame=requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(form ? promptRef.current : inputRetryRef.current)));
    return ()=>cancelAnimationFrame(frame);
  },[form,inputError]);
  function closeReview(){
    const preparing=review?.payload.action==="prepare";
    const restore=reviewRef.current?.contains(document.activeElement);
    const epoch=reviewEpoch.current;
    confirmation.current.cancel();setReview(null);
    handoff.clearReview();
    if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);
    if(restore)restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;if(reviewEpoch.current===epoch && !reviewRequest.current){
      const target=(preparing ? (prepareDetails.current?.open ? prepareRef : prepareSummary) : promptRef).current;
      restoreLostFocus(document,visibleFocusTarget(target));
    }});
  }
  async function readJob(id,{signal}={}){
    const formAtStart=formRef.current,reviewAtStart=reviewEpoch.current,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const cancel=()=>controller.abort();
    if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",cancel,{once:true});
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const result=await untilAborted((async()=>{
      const response=await fetch(formPath+"/"+encodeURIComponent(id),{cache:"no-store",signal:controller.signal});
      let result;
      try{result=await response.json();}catch{throw new Error(response.ok ? "저장된 오디오 입력 형식을 확인할 수 없습니다." : "저장된 입력을 확인할 수 없습니다.");}
      if(!response.ok)throw new Error(typeof result?.detail==="string" ? result.detail : "저장된 입력을 확인할 수 없습니다.");
      return result;
      })(),controller.signal);
      const input=result?.request;
      if(result?.id!==id || !input || typeof input.prompt!=="string" || !Number.isInteger(input.seed) || typeof input.loop_request!=="boolean" || typeof input.tag!=="string" ||
        (music && (typeof input.lyrics!=="string" || !Number.isFinite(input.duration_seconds))))throw new Error("저장된 오디오 입력 형식을 확인할 수 없습니다.");
      return {...result,formAtStart,reviewAtStart,focusAtStart};
    }catch(problem){if(timedOut)throw new Error("저장된 입력 조회 시간이 초과됐습니다.");throw problem;}
    finally{clearTimeout(timer);signal?.removeEventListener("abort",cancel);}
  }
  function cleaned(message){
    setJob("");setNotice(message);setHistoryRevision(value=>value+1);
  }
  useEffect(()=>{
    let active=true,timedOut=false;const controller=new AbortController();let timeout;
    if(activeRevision || embedded || !new URLSearchParams(location.search).get("job")){
      activePending.current=true;setActiveLoading(true);setActiveError("");setActiveNotice("");
      timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      untilAborted(managementCommand(service,"active",{},{signal:controller.signal}),controller.signal).then(result=>{
        if(!result || !(result.id===null || validGenerationJobId(result.id)))throw new Error("진행 작업 응답을 확인할 수 없습니다.");
        if(active){setActiveId(result.id || "");if(result.id)setJob(current=>current || result.id);if(activeRevision)setActiveNotice(result.id ? "진행 작업을 확인했습니다. 선택한 결과는 유지합니다." : "진행 중인 작업이 없습니다.");}
      }).catch(error=>{if(active)setActiveError(timedOut ? "진행 작업 조회 시간이 초과됐습니다. 다시 조회하거나 이력에서 확인하세요." : "진행 작업을 확인하지 못했습니다. 다시 조회하거나 이력에서 확인하세요 · "+requestErrorMessage(error));}).finally(()=>{clearTimeout(timeout);if(active){activePending.current=false;setActiveLoading(false);}});
    }
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[activeRevision]);
  useEffect(()=>{if(activeLoading || !activeRetryFocus.current)return;activeRetryFocus.current=false;if(document.activeElement===document.body)restoreLostFocus(document,(activeError ? activeRetryRef : activeErrorRef).current);},[activeLoading,activeError]);
  useEffect(()=>{
    const controller=new AbortController();
    let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    inputPending.current=true;setInputError("");
    untilAborted(fetch(formPath,{signal:controller.signal}).then(response=>{
      if(!response.ok)throw new Error("기본 입력을 불러올 수 없습니다.");
      return response.json();
    }),controller.signal).then(async defaults=>{
      if(!defaults || typeof defaults.prompt!=="string" || !Number.isInteger(defaults.seed) || typeof defaults.loop_request!=="boolean" || typeof defaults.tag!=="string" ||
        (music && (typeof defaults.lyrics!=="string" || !Number.isFinite(defaults.duration_seconds))))throw new Error("기본 입력 형식을 확인할 수 없습니다.");
      const id=query.get('proposal_job');
      if(!id || embedded){if(!controller.signal.aborted)setForm(current=>current ?? defaults);return;}
      try{
        const offset=query.get('proposal_offset');
        if(!/^\d+$/.test(offset || ''))throw new Error('대화 이력 정보를 확인할 수 없습니다.');
        const proposal=await untilAborted(readGenerationProposal(managementCommand,{session,job:id,snapshot:query.get('proposal_snapshot'),offset:Number(offset),kind:'audio'},{signal:controller.signal}),controller.signal);
        const inputs=audioProposalInputs(defaults,proposal,service);
        if(!controller.signal.aborted){setForm(current=>current ?? inputs);setNotice('대화 제안 입력을 불러왔습니다. 내용을 검토한 뒤 접수하세요.');}
      }catch(error){if(active && (timedOut || !controller.signal.aborted)){setForm(current=>current ?? defaults);setNotice(timedOut ? '대화 제안 조회 시간이 초과되어 기본 입력을 표시합니다.' : '대화 제안을 불러오지 못했습니다 · '+requestErrorMessage(error));}}
    }).catch(error=>{if(active && (timedOut || !controller.signal.aborted))setInputError(timedOut ? "기본 입력 조회 시간이 초과됐습니다." : requestErrorMessage(error));}).finally(()=>{clearTimeout(timeout);if(active)inputPending.current=false;});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[inputRevision]);
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  async function preview(event){
    event.preventDefault();if(reviewRequest.current || interactionRef.current.busy || interactionRef.current.review)return;
    const controller=new AbortController(),formAtStart=formRef.current;reviewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reviewEpoch.current++;
    reviewOrigin.current=document.activeElement;
    setBusy(true);setNotice("");
    try{
      if(music){
        if(!tagCount || !form.lyrics.trim())throw new Error("음악 태그와 가사를 입력하세요.");
        const status=await untilAborted(managementCommand(service,"model-status",{},{signal:controller.signal}),controller.signal);
        if(typeof (status?.generation_ready ?? status?.ready)!=="boolean")throw new Error("모델 준비 상태를 확인할 수 없습니다. 다시 시도하세요.");
        if(!generationReady(status))throw new Error(status.message || "모델 준비가 필요합니다.");
      }
      const payload={...form,seed:Number(form.seed),...(music?{duration_seconds:Number(form.duration_seconds)}:{}),action:"generate"};
      const {response,result}=await untilAborted((async()=>{const response=await fetch(formPath,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),signal:controller.signal});return {response,result:await response.json()};})(),controller.signal);
      if(!response.ok)throw new Error(typeof result?.detail==="string" ? result.detail : "입력을 확인하세요.");
      if(typeof result?.final_prompt!=="string" || !result.final_prompt.trim())throw new Error("검토할 최종 프롬프트를 확인할 수 없습니다. 다시 시도하세요.");
      await untilAborted(handoff.preview(payload,{signal:controller.signal}),controller.signal);
      if(reviewRequest.current!==controller)return;
      if(formRef.current!==formAtStart)throw new Error("검토 중 입력이 변경되었습니다. 다시 확인하세요.");
      setReview({payload,prompt:result.final_prompt,confirmation:confirmation.current.open()});
    }catch(error){if(reviewRequest.current===controller){handoff.clearReview();setNotice(timedOut ? "검토 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(error),true);}}
    finally{clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  async function reviewPreparation(){
    if(reviewRequest.current || interactionRef.current.busy || interactionRef.current.review)return;
    const controller=new AbortController();reviewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reviewEpoch.current++;
    reviewOrigin.current=document.activeElement;
    setNotice("");setBusy(true);
    try{
      if(music){
        const status=await untilAborted(managementCommand(service,"model-status",{},{signal:controller.signal}),controller.signal);
        if(!status || typeof status.ready!=="boolean" || (status.artifacts_ready!==undefined && typeof status.artifacts_ready!=="boolean"))throw new Error("모델 파일 상태를 확인할 수 없습니다. 다시 시도하세요.");
        if(!status.artifacts_ready)throw new Error("모델 관리에서 파일 다운로드를 먼저 완료하세요.");
      }
      if(reviewRequest.current===controller)setReview({payload:{action:"prepare"},confirmation:confirmation.current.open()});
    }catch(error){if(reviewRequest.current===controller)setNotice(timedOut ? "준비 검토 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(error),true);}
    finally{clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  async function submit(){
    if(!review || submitting.current || (review.payload.action==="generate" && !generationReady(model)))return;
    if(!confirmation.current.claim(review.confirmation))return;
    submitting.current=true;setBusy(true);
    try{
      if(handoff.review){await handoff.approve(review.payload);setNotice("확인한 GPU 양도 요청을 접수했습니다.");return;}
      const result=await managementCommand(service,review.payload.action,review.payload);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice(review.payload.action==="prepare"?"모델 준비를 대기열에 등록했습니다.":"공용 GPU 대기열에 등록했습니다.");
    }catch(error){setNotice(requestErrorMessage(error)+" · 생성 이력에서 접수 여부를 확인하세요.",true);}
    finally{handoff.clearReview();submitting.current=false;setBusy(false);setReview(null);}
  }
  return <article className={"audio-generator-page generator-page-common"+(embedded ? "" : " audio-standalone")}>{!embedded && <nav aria-label="워크플로우 탐색"><a href={"/management/assistant/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화</a></nav>}
    <h1 className={embedded ? "embedded-page-title" : undefined}>{music?"HeartMuLa 음악 생성":"Dasheng 효과음 생성"}</h1>
    <GeneratorChangelog generator={service} card/>
    <GeneratorSectionCard title="사용설명" summary="사용 방법과 제한 사항">{music ? <p>태그는 쉼표로 구분합니다. 가사·구간 태그와 최대 출력 시간을 입력하세요. 원곡 생성 후 Demucs가 MR과 보컬을 분리합니다.</p> : <p>원하는 효과음을 설명하고 반복 구조가 필요하면 선택하세요. 길이는 자동 예측하며 결과는 16kHz WAV입니다. <a href="https://huggingface.co/mispeech/Dasheng-AudioGen">모델과 라이선스</a></p>}<p>모델 준비를 확인하고 생성 요청을 검토한 뒤 접수하세요. 작업 상태와 결과는 생성 이력에서 확인할 수 있습니다.</p></GeneratorSectionCard>
    <GeneratorSectionNavigation inputRef={inputRegion} historyRef={historyRegion} resultRef={resultRegion} inputReady={Boolean(form)} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : generationReady(model) ? "준비 완료" : "준비 필요"}>
      <ModelReadiness session={session} service={service} onStatus={setModel} onError={setModelError}/>
      <details ref={prepareDetails}><summary ref={prepareSummary}>모델 다운로드·준비</summary>
        <DownloadProgress service={service}/>
        <button ref={prepareRef} disabled={Boolean(prepareReason)} aria-describedby={prepareReason ? prepareReasonId : undefined} onClick={reviewPreparation}>모델 준비 요청 검토</button>
        {prepareReason && <p id={prepareReasonId}>{prepareReason}</p>}
      </details>
    </GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={id=>openGeneratorHistory(historyRegion,id,setJob)}>
      <AudioActiveStatus statusRef={activeErrorRef} retryRef={activeRetryRef} loading={activeLoading} notice={activeNotice} error={activeError} activeId={activeId} job={job} onOpen={()=>openGeneratorHistory(historyRegion,activeId,setJob)} onRetry={()=>{if(activePending.current)return;activePending.current=true;activeRetryFocus.current=document.activeElement===activeRetryRef.current;setActiveLoading(true);setActiveError("");retryActive(value=>value+1);}}/>
    </ActiveGeneratorProgress>
    {!form && (inputError ? <div><p role="alert">{inputError}</p><button ref={inputRetryRef} type="button" onClick={()=>{if(inputPending.current)return;inputPending.current=true;inputRetryFocus.current=document.activeElement===inputRetryRef.current;setInputError("");retryInput(value=>value+1);}}>기본 입력 다시 불러오기</button></div> : <p role="status">기본 입력을 불러오는 중입니다.</p>)}
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service={service} status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
    <AudioReviewPending busy={busy} review={review}/>
    <GeneratorSectionCard title="생성 입력" summary={music ? "음악 태그와 가사" : "효과음 설명과 설정"} defaultOpen>
    {music && <fieldset className="audio-examples-controls" disabled={busy || Boolean(review) || Boolean(handoff.id) || !form} aria-describedby={busy || review || handoff.id || !form ? inputLockId : undefined}><legend className="generator-visually-hidden">음악 예제</legend><MusicExamples apply={request=>setForm(current=>({...current,...request}))}/></fieldset>}
    {form && <form ref={inputRegion} tabIndex={-1} aria-label={music ? "음악 생성 입력" : "효과음 생성 입력"} onSubmit={preview}><fieldset disabled={busy || Boolean(review) || Boolean(handoff.id)} aria-describedby={busy || review || handoff.id ? inputLockId : undefined}>
      <legend className="generator-visually-hidden">{music?"음악 생성 입력":"효과음 생성 입력"}</legend>
      <label>{music?"음악 태그":"효과음 설명"} <textarea ref={promptRef} required maxLength={4000} value={form.prompt} aria-describedby={music ? tagCountId : undefined} onChange={e=>edit("prompt",e.target.value)}/></label>{music ? <small id={tagCountId}>태그 {tagCount}개</small> : <PromptWordCount text={form.prompt}/>}
      <SeedInput value={form.seed} max={4294967295} error={audioSeedValid(form.seed) ? "" : "0부터 4,294,967,295까지의 정수로 입력하세요."} onChange={value=>edit("seed",value)}/>
      {music ? <>
        <label>가사·구간 태그 <textarea required maxLength={20000} value={form.lyrics} onChange={e=>edit("lyrics",e.target.value)}/></label><PromptWordCount text={form.lyrics}/>
        <div className="audio-duration-field"><label>최대 출력 시간(초) <input type="number" min="5" max="300" step="any" required aria-invalid={!audioDurationValid(form.duration_seconds) || undefined} aria-describedby={!audioDurationValid(form.duration_seconds) ? durationErrorId : undefined} value={form.duration_seconds} onChange={e=>edit("duration_seconds",e.target.value)}/></label>{!audioDurationValid(form.duration_seconds) && <small id={durationErrorId}>5~300초로 입력하세요.</small>}</div>
      </> : <label className="sound-loop"><input type="checkbox" checked={form.loop_request} onChange={e=>edit("loop_request",e.target.checked)}/>반복 구조 요청</label>}
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <ActionButton type="submit" reasons={audioInputIssues(form,music,model)}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {(busy || review || handoff.id || !form) && <p id={inputLockId} role="status">{!form ? "기본 입력을 확인하세요." : busy ? "요청을 처리하고 있습니다." : review ? "입력을 수정하려면 생성 요청 검토에서 입력 수정을 선택하세요." : "진행 중인 GPU 양도 요청을 확인하세요."}</p>}
    </GeneratorSectionCard>
    {review && <section ref={reviewRef} tabIndex={-1} aria-label="생성 요청 확인"><h2>{review.payload.action==="prepare"?"모델 다운로드·준비":"생성 요청 확인"}</h2>
      {review.payload.action==="generate" && <>
        <p>시드 {review.payload.seed} · {music ? `최대 출력 시간 ${review.payload.duration_seconds}초` : `반복 구조 ${review.payload.loop_request ? "요청" : "없음"}`}{review.payload.tag?.trim() && ` · 이력 태그 ${review.payload.tag.trim()}`}</p>
        <h3>최종 모델 입력</h3><p>{review.prompt} · <PromptWordCount text={review.prompt} label="최종 프롬프트"/></p>
        {music && review.payload.lyrics && <><h3>가사·구간 태그</h3><pre>{review.payload.lyrics}</pre></>}
      </>}
      <GpuQueueSummary/>
      {handoff.review && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 {music?"음악":"효과음"}을 생성합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={closeReview} onConfirm={submit} confirmLabel={handoff.review ? "해제·생성·재적재에 동의" : undefined} disabledReason={review.payload.action==="generate" && !generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/></section>}
    <fieldset ref={historyRegion} className="audio-history-controls" disabled={busy || Boolean(review) || !form} aria-describedby={busy || review || !form ? historyLockId : undefined}>
      <legend className="generator-visually-hidden">생성 이력</legend>
      <GeneratorHistory card allowPriority toggleResult onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service={service} readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob("")} restore={(input,record)=>{
        if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.review)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
        if(record.formAtStart!==formRef.current)throw new Error("입력 조회 중 작성 내용이 변경되어 적용하지 않았습니다.");
        setForm(input);setNotice("저장된 생성 입력을 불러왔습니다.");const card=promptRef.current?.closest('details');if(card)card.open=true;
        if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;if(record.reviewAtStart===reviewEpoch.current && !interactionRef.current.busy && !interactionRef.current.review && (document.activeElement===record.focusAtStart || document.activeElement===document.body) && promptRef.current?.isConnected && !promptRef.current.disabled)promptRef.current.focus();});
      }} renderResult={id=><section ref={resultRegion} tabIndex={-1} aria-label="선택한 오디오 작업 결과"><GeneratorJobResult selectionControls job={id} service={service} kind="audio" readJobWithSignal={readJob} onDeleted={cleaned}/></section>}/>
    </fieldset>
    {(busy || review || !form) && <p id={historyLockId} role="status">{!form ? "기본 입력을 확인한 뒤 이력을 사용할 수 있습니다." : busy ? "요청을 처리하고 있습니다." : "요청 검토를 마치거나 취소하면 이력을 사용할 수 있습니다."}</p>}
    <AudioNotice notice={notice} error={noticeError}/>
    <GeneratorJobResult selectionControls job="" service={service} kind="audio" onDeleted={cleaned}/>
  </article>;
}
