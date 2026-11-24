import React,{useEffect,useRef,useState} from "react";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {validVideoJobId} from "./videoJobId.mjs";
import {referencePng} from "./videoInputs.js";
import {generationReady} from "./generationReady.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
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
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";

const service="minimax-h3-i2v";
export default function MiniMaxH3Page({embedded=false,session:embeddedSession=""}={}) {
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
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
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[checking,setChecking]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0);
  const formRef=useRef(null),inputRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),reviewRef=useRef(null),sending=useRef(false),reviewRequest=useRef(null),imageVersion=useRef(0),promptEdited=useRef(false),current=useRef(null);
  current.current={prompt,seed,file,pending,busy,checking};
  useEffect(()=>()=>{reviewRequest.current?.abort();reviewRequest.current=null;},[]);
  useEffect(()=>{let active=true;(async()=>{try{const scope=generationProposalScope(location.search,session,'video');if(!scope)return;const proposal=await readGenerationProposal(managementCommand,scope);if(proposal.service!==service || proposal.mode!=='first_frame' || !proposal.prompt.trim())throw new Error('MiniMax 영상 제안을 확인할 수 없습니다.');if(active)setPrompt(old=>promptEdited.current ? old : old || proposal.prompt);}catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();return ()=>{active=false;};},[session]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>2147483647;
  const reasons=[!generationReady(model) && "모델 준비 상태를 확인하세요.",checking && "이미지 확인이 끝날 때까지 기다리세요.",!file && "첫 프레임 이미지를 선택하세요.",!prompt.trim() && "동작 프롬프트를 입력하세요.",invalidSeed && "시드는 0~2147483647의 정수여야 합니다."];
  async function review(event){
    event.preventDefault();if(busy || pending || reviewRequest.current || reasons.some(Boolean))return;
    const controller=new AbortController(),version=imageVersion.current,origin=document.activeElement;reviewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const image=await untilAborted(referencePng(file),controller.signal);
      if(reviewRequest.current!==controller || controller.signal.aborted)return;
      const now=current.current;
      if(now.prompt!==prompt || now.seed!==seed || now.file!==file || now.checking || imageVersion.current!==version)throw new Error("이미지 확인 중 입력이 바뀌었습니다. 다시 검토하세요.");
      setPending({action:"generate",prompt:prompt.trim(),images:[image],width:832,height:480,frames:124,steps:8,seed});requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===origin)reviewRef.current?.focus();});
    }catch(problem){if(reviewRequest.current===controller)setError(timedOut ? "이미지 확인 시간이 초과됐습니다. 다시 시도하세요." : problem.message || "이미지를 읽을 수 없습니다.");}
    finally{clearTimeout(timer);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);setError("");setNotice("");const request=pending;
    const controller=new AbortController();let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{const result=await untilAborted(managementCommand(service,"generate",request,{signal:controller.signal}),controller.signal);if(!validVideoJobId(result?.id))throw new Error("접수 ID를 확인할 수 없습니다.");setJob(result.id);setRevision(n=>n+1);setNotice("생성 요청을 접수했습니다. 작업 이력에서 진행 상태를 확인하세요.");}
    catch(problem){setError((timedOut ? "접수 응답 시간이 초과됐습니다." : problem.message || "접수 여부를 확인할 수 없습니다.")+" · 접수 여부가 불확실합니다. 재접수하기 전에 이력을 확인하세요.");}
    finally{const restore=reviewRef.current?.contains(document.activeElement);clearTimeout(timer);sending.current=false;setBusy(false);setPending(null);if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body)formRef.current?.focus();});}
  }
  async function readSavedInput(id,forRestore=true){
    const start=current.current,version=imageVersion.current,focusAtStart=document.activeElement;
    if(forRestore && (start.busy || start.pending || start.checking || reviewRequest.current))throw new Error("현재 입력 확인이 끝난 뒤 다시 시도하세요.");
    const controller=new AbortController();let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch('/management/assistant/minimax-h3-i2v-input/'+encodeURIComponent(id),{cache:'no-store',signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error('저장된 입력을 읽을 수 없습니다.');
      const record=await untilAborted(response.json(),controller.signal);
      if(record?.id!==id || !Array.isArray(record.request?.images) || record.request.images.length!==1 || typeof record.request.images[0]!=="string")throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      const request=record.request;
      if(forRestore && (request.action!=="generate" || typeof request.prompt!=="string" || !request.prompt.trim() || request.prompt.length>8000 || !Number.isInteger(request.seed) || request.seed<0 || request.seed>2147483647 || request.width!==832 || request.height!==480 || request.frames!==124 || request.steps!==8))throw new Error('현재 화면에서 지원하지 않는 저장 설정이 있어 입력을 적용하지 않았습니다. 저장 입력 상세를 확인하세요.');
      const bytes=Uint8Array.from(atob(record.request.images[0]),c=>c.charCodeAt(0));
      if(!bytes.length)throw new Error('저장된 참조 이미지를 확인할 수 없습니다.');
      return {...record,restoredFile:new File([bytes],'reference-1.png',{type:'image/png'}),inputAtStart:start,version,focusAtStart};
    } catch(problem){if(timedOut)throw new Error('저장 입력 조회 시간이 초과됐습니다. 다시 시도하세요.');throw problem;} finally{clearTimeout(timer);}
  }
  function restoreSavedInput(request,record){
    const now=current.current,start=record.inputAtStart;
    if(now.busy || now.pending || now.checking || reviewRequest.current || now.prompt!==start.prompt || now.seed!==start.seed || now.file!==start.file || imageVersion.current!==record.version)throw new Error('조회 중 입력이 바뀌어 적용하지 않았습니다. 다시 시도하세요.');
    promptEdited.current=true;setPrompt(request.prompt);setSeed(request.seed);setFile(record.restoredFile);setNotice(record.id+'의 입력을 적용했습니다.');setError('');
    if(inputRef.current)inputRef.current.open=true;requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===record.focusAtStart)formRef.current?.focus();});
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);setPending(null);
    if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body)formRef.current?.focus();});
  }
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}>
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    <button type="button" onClick={()=>setPolicyRevision(n=>n+1)}>정책 상태 새로고침</button>
    <p role="status">헤르메스 MiniMax 우선 정책: {policy===null ? "조회 중" : policy===true ? "적용 중" : policy===false ? "적용 안 함" : policy==="timeout" ? "조회 시간 초과 · 새로고침하여 다시 확인하세요" : "게이트웨이 상태 확인 불가 · 새로고침하여 다시 확인하세요"}</p>
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : generationReady(model) ? "준비 완료" : "준비 필요"}><ModelReadiness session={session} service={service} onStatus={setModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary="첫 이미지와 동작 지시" defaultOpen cardRef={inputRef} className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending}><legend className="generator-visually-hidden">생성 입력</legend>
      <ReferenceImageInput label="첫 프레임 이미지" source={file} onSelectionStart={()=>imageVersion.current++} onCheckingChange={setChecking} onChange={setFile} disabled={busy || !!pending}/>
      <p>이미지에 흰 여백을 넣어 832×480 영상에 맞춥니다.</p>
      <label>장면·동작 프롬프트<textarea required maxLength={8000} value={prompt} onChange={e=>{promptEdited.current=true;setPrompt(e.target.value);}}/><PromptWordCount text={prompt} final/></label>
      <SeedInput value={seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <p>832×480 · 124프레임 · 24fps · 약 5.17초 · Turbo 8스텝. 480p 생성과 동작 품질은 별도 확인이 필요합니다.</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · 832×480 · 124프레임 · 24fps · Turbo 8스텝 · 시드 {pending.seed}</p><ReviewPrompt label="장면·동작 프롬프트" text={pending.prompt}/><GenerationReviewActions busy={busy} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하세요." : ""} onCancel={cancelReview} onConfirm={submit}/></section>}
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority readJob={readSavedInput} restore={restoreSavedInput} openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(n=>n+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(n=>n+1);}}/>} renderResult={(id,close)=><section ref={resultRef} tabIndex={-1}><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} readJob={currentId=>readSavedInput(currentId,false)}/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>
  </article>;
}
