import {useMiniMaxPages,MiniMaxPageNavigation} from "./MiniMaxPageNavigation.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {useMinimaxReportReceipt,MinimaxReportStatus} from "./useMinimaxReportReceipt.jsx";
import {validVideoJobId} from "./videoJobId.mjs";
import {referencePng} from "./videoInputs.js";
import {generationReady} from "./generationReady.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import {restoreLostFocus,visibleFocusTarget} from "./restoreLostFocus.mjs";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import ActionButton from "./ActionButton.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";

const service="minimax-h3-i2v";
export default function MiniMaxH3Page({embedded=false,session:embeddedSession=""}={}) {
  const {page,navigate}=useMiniMaxPages(!embedded);
  const inputLockId=useId();
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [proposalScope,setProposalScope]=useState(null);
  const hasProposal=new URLSearchParams(location.search).has("proposal_job");
  const receipt=useMinimaxReportReceipt(proposalScope,service);
  const [policy,setPolicy]=useState(null);
  const [policyRevision,setPolicyRevision]=useState(0);
  useEffect(()=>{
    let active=true,timedOut=false;const controller=new AbortController();
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);setPolicy(null);
    (async()=>{try{
      const response=await untilAborted(fetch("/management/minimax-policy",{cache:"no-store",signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error("정책 조회 실패");
      const value=await untilAborted(response.json(),controller.signal);
      if(active)setPolicy(typeof value?.minimax_preferred==="boolean" ? value.minimax_preferred : "unknown");
    }catch{if(active)setPolicy(timedOut ? "timeout" : "unknown");}finally{clearTimeout(timer);}})();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[policyRevision]);
  const [prompt,setPrompt]=useState(""),[seed,setSeed]=useState(42),[file,setFile]=useState(null),[model,setModel]=useState(null),[modelError,setModelError]=useState("");
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[checking,setChecking]=useState(false),[imageError,setImageError]=useState(false),[previewError,setPreviewError]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0);
  const formRef=useRef(null),inputRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null),sending=useRef(false),reviewRequest=useRef(null),imageVersion=useRef(0),promptEdited=useRef(false),current=useRef(null);
  current.current={prompt,seed,file,pending,busy,checking};
  useEffect(()=>()=>{reviewRequest.current?.abort();reviewRequest.current=null;},[]);
  useEffect(()=>{if(!pending)return;const origin=reviewOrigin.current;reviewOrigin.current=null;if(document.activeElement===document.body || document.activeElement===origin)reviewRef.current?.focus();},[pending]);
  useEffect(()=>{if(busy || pending || !error || !reviewOrigin.current)return;const origin=reviewOrigin.current;reviewOrigin.current=null;const frame=requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(origin)));return ()=>cancelAnimationFrame(frame);},[busy,pending,error]);
  useEffect(()=>{let active=true;(async()=>{try{const scope=generationProposalScope(location.search,session,'video');if(!scope)return;const proposal=await readGenerationProposal(managementCommand,scope);if(proposal.service!==service || proposal.mode!=='first_frame' || !proposal.prompt.trim())throw new Error('MiniMax 영상 제안을 확인할 수 없습니다.');if(active){setProposalScope(scope);setPrompt(old=>promptEdited.current ? old : old || proposal.prompt);}}catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();return ()=>{active=false;};},[session]);
  useEffect(()=>{if(receipt.state==="accepted" && receipt.job)setJob(receipt.job);},[receipt.state,receipt.job]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>2147483647;
  const reasons=[hasProposal && (!proposalScope || receipt.state!=="editing") && "대화 접수 상태를 확인하세요.",!generationReady(model) && "모델 준비 상태를 확인하세요.",checking && "이미지 확인이 끝날 때까지 기다리세요.",!file && "첫 프레임 이미지를 선택하세요.",!prompt.trim() && "동작 프롬프트를 입력하세요.",invalidSeed && "시드는 0~2147483647의 정수여야 합니다."];
  async function review(event){
    event.preventDefault();if(busy || pending || reviewRequest.current || reasons.some(Boolean))return;
    const controller=new AbortController(),version=imageVersion.current;reviewOrigin.current=document.activeElement;reviewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const image=await untilAborted(referencePng(file),controller.signal);
      if(reviewRequest.current!==controller || controller.signal.aborted)return;
      const now=current.current;
      if(now.prompt!==prompt || now.seed!==seed || now.file!==file || now.checking || imageVersion.current!==version)throw new Error("이미지 확인 중 입력이 바뀌었습니다. 다시 검토하세요.");
      setPending({action:"generate",prompt:prompt.trim(),images:[image],width:832,height:480,frames:124,steps:8,seed});
    }catch(problem){if(reviewRequest.current===controller)setError(timedOut ? "이미지 확인 시간이 초과됐습니다. 다시 시도하세요." : problem.message || "이미지를 읽을 수 없습니다.");}
    finally{clearTimeout(timer);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  useEffect(()=>{if(embedded)return;const syncJob=()=>{const id=new URLSearchParams(location.search).get("job");setJob(id || "");};window.addEventListener("popstate",syncJob);return ()=>window.removeEventListener("popstate",syncJob);},[embedded]);
  useEffect(()=>{if(!embedded && page==="history"){const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;}},[embedded,page]);
  async function submit(){
    if(!pending || sending.current || !generationReady(model) || (hasProposal && (!proposalScope || receipt.state!=="editing")))return;
    sending.current=true;setBusy(true);setError("");setNotice("");const request=pending;
    const controller=new AbortController();let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{if(proposalScope)await untilAborted(readGenerationProposal(managementCommand,proposalScope),controller.signal);const result=await untilAborted(proposalScope ? managementCommand("hermes-agent","hermes-minimax-submit",{session_id:proposalScope.session,proposal_job_id:proposalScope.job,request_id:receipt.id,service,request},{signal:controller.signal}) : managementCommand(service,"generate",request,{signal:controller.signal}),controller.signal);const resultId=proposalScope ? (result?.state==="accepted" ? result.job_id : null) : result?.id;if(!validVideoJobId(resultId))throw new Error("접수 ID를 확인할 수 없습니다.");if(proposalScope)receipt.refresh();setJob(resultId);if(!embedded)navigate("history",resultId);setRevision(n=>n+1);setNotice("생성 요청을 접수했습니다. 작업 이력에서 진행 상태를 확인하세요.");}
    catch(problem){if(proposalScope)receipt.unknown();setError((timedOut ? "접수 응답 시간이 초과됐습니다." : problem.message || "접수 여부를 확인할 수 없습니다.")+" · 접수 여부가 불확실합니다. 재접수하기 전에 이력을 확인하세요.");}
    finally{const restore=reviewRef.current?.contains(document.activeElement);clearTimeout(timer);sending.current=false;setBusy(false);setPending(null);if(restore)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(formRef.current)));}
  }
  async function readSavedInput(id,forRestore=true,{signal}={}){
    const start=current.current,version=imageVersion.current,focusAtStart=document.activeElement;
    if(forRestore && (start.busy || start.pending || start.checking || reviewRequest.current))throw new Error("현재 입력 확인이 끝난 뒤 다시 시도하세요.");
    const controller=new AbortController();let timedOut=false;
    const cancel=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',cancel,{once:true});
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch('/management/assistant/minimax-h3-i2v-input/'+encodeURIComponent(id),{cache:'no-store',signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error('저장된 입력을 읽을 수 없습니다.');
      let record;try{record=await untilAborted(response.json(),controller.signal);}catch(problem){controller.signal.throwIfAborted();throw new Error('저장 입력 형식을 확인할 수 없습니다. 다시 조회하세요.');}
      if(record?.id!==id || !Array.isArray(record.request?.images) || record.request.images.length!==1 || typeof record.request.images[0]!=="string")throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      const request=record.request;
      if(forRestore && (request.action!=="generate" || typeof request.prompt!=="string" || !request.prompt.trim() || request.prompt.length>8000 || !Number.isInteger(request.seed) || request.seed<0 || request.seed>2147483647 || request.width!==832 || request.height!==480 || request.frames!==124 || request.steps!==8))throw new Error('현재 화면에서 지원하지 않는 저장 설정이 있어 입력을 적용하지 않았습니다. 저장 입력 상세를 확인하세요.');
      const bytes=Uint8Array.from(atob(record.request.images[0]),c=>c.charCodeAt(0));
      if(!bytes.length)throw new Error('저장된 참조 이미지를 확인할 수 없습니다.');
      return {...record,restoredFile:new File([bytes],'reference-1.png',{type:'image/png'}),inputAtStart:start,version,focusAtStart};
    } catch(problem){if(timedOut)throw new Error('저장 입력 조회 시간이 초과됐습니다. 다시 시도하세요.');throw problem;} finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
  }
  function restoreSavedInput(request,record){
    const now=current.current,start=record.inputAtStart;
    if(now.busy || now.pending || now.checking || reviewRequest.current || now.prompt!==start.prompt || now.seed!==start.seed || now.file!==start.file || imageVersion.current!==record.version)throw new Error('조회 중 입력이 바뀌어 적용하지 않았습니다. 다시 시도하세요.');
    if(!embedded)navigate("input");
    promptEdited.current=true;setPrompt(request.prompt);setSeed(request.seed);setFile(record.restoredFile);setNotice(record.id+'의 입력을 적용했습니다.');setError('');
    if(inputRef.current)inputRef.current.open=true;requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===record.focusAtStart)formRef.current?.focus();});
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);setPending(null);
    if(restore)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(formRef.current)));
  }
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}>
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    {hasProposal && (proposalScope ? <MinimaxReportStatus receipt={receipt}/> : <p role="status">대화 제안을 확인하고 있습니다.</p>)}
    <button type="button" onClick={()=>setPolicyRevision(n=>n+1)}>정책 상태 새로고침</button>
    <p role="status">헤르메스 MiniMax 우선 정책: {policy===null ? "조회 중" : policy===true ? "적용 중" : policy===false ? "적용 안 함" : policy==="timeout" ? "조회 시간 초과 · 새로고침하여 다시 확인하세요" : "게이트웨이 상태 확인 불가 · 새로고침하여 다시 확인하세요"}</p>
    {!embedded ? <MiniMaxPageNavigation page={page} navigate={navigate} locked={busy || !!pending}/> : <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>}
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : generationReady(model) ? "준비 완료" : "준비 필요"}><ModelReadiness session={session} service={service} onStatus={setModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={id=>{if(!embedded){setJob(id);navigate("history",id);}else openGeneratorHistory(historyRef,id,setJob);}}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div hidden={!embedded && page!=="input"}><GeneratorSectionCard title="생성 입력" summary={[checking && "이미지 확인 중",imageError && "이미지 확인 실패",previewError && "이미지 미리보기 실패"].filter(Boolean).join(" · ") || "첫 이미지와 동작 지시"} defaultOpen cardRef={inputRef} className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending} aria-describedby={busy || pending ? inputLockId : undefined}><legend className="generator-visually-hidden">생성 입력</legend>
      <ReferenceImageInput onPreviewErrorChange={setPreviewError} onErrorChange={setImageError} label="첫 프레임 이미지" source={file} onSelectionStart={()=>imageVersion.current++} onCheckingChange={setChecking} onChange={setFile} disabled={busy || !!pending}/>
      <p>이미지에 흰 여백을 넣어 832×480 영상에 맞춥니다.</p>
      <label>장면·동작 프롬프트<textarea required maxLength={8000} value={prompt} onChange={e=>{promptEdited.current=true;setPrompt(e.target.value);}}/></label><PromptWordCount text={prompt} final/>
      <SeedInput value={seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <p>832×480 · 124프레임 · 24fps · 약 5.17초 · Turbo 8스텝. 480p 생성과 동작 품질은 별도 확인이 필요합니다.</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset>{(busy || pending) && <p id={inputLockId} role="status">{busy ? "요청을 처리하고 있습니다. 잠시 기다려 주세요." : "입력을 수정하려면 생성 요청 검토에서 입력 수정을 선택하세요."}</p>}</form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · 832×480 · 124프레임 · 24fps · Turbo 8스텝 · 시드 {pending.seed}</p><ReviewPrompt label="장면·동작 프롬프트" text={pending.prompt}/><GenerationReviewActions busy={busy} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하세요." : ""} onCancel={cancelReview} onConfirm={submit}/></section>}
    </div>
    {(embedded || page==="history") && <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority toggleResult readJobWithSignal={(id,options)=>readSavedInput(id,true,options)} restore={restoreSavedInput} openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(n=>n+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(n=>n+1);}}/>} renderResult={id=><section ref={resultRef} tabIndex={-1} aria-label="선택한 영상 작업 결과"><SavedGeneratorInputs id={id} service={service} readJobWithSignal={(currentId,options)=>readSavedInput(currentId,false,options)}/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>}
  </article>;
}
