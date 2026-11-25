import React, {useCallback, useEffect, useRef, useState} from "react";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ActionButton from "./ActionButton.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {useMinimaxReportReceipt,MinimaxReportStatus} from "./useMinimaxReportReceipt.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import {validGenerationJobId} from "./generationJobId.mjs";

const service = "minimax-h3-image";
export function minimaxImageReasons({model,prompt,seed}) {
  return [!model?.generation_ready && "모델 준비 상태를 확인하세요.",!prompt.trim() && "프롬프트를 입력하세요.",(!Number.isInteger(seed) || seed<0 || seed>4294967295) && "시드는 0부터 4294967295까지의 정수로 입력하세요."];
}
export default function MiniMaxH3ImagePage({embedded=false,initialInputs=null,proposalScope=null,reportReceipt=null}={}) {
  const [prompt,setPrompt]=useState(initialInputs?.prompt || ""), [seed,setSeed]=useState(initialInputs?.seed ?? 42), [model,setModel]=useState(null);
  const [size,setSize]=useState(initialInputs?.width===512 && initialInputs?.height===512 ? 512 : 1024);
  const [pending,setPending]=useState(null), [preview,setPreview]=useState(""), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [job,setJob]=useState(()=>{
    const linked=new URLSearchParams(window.location.search).get("job");
    return !embedded && validGenerationJobId(linked) ? linked : "";
  }), [revision,setRevision]=useState(0);
  const localReceipt=useMinimaxReportReceipt(reportReceipt ? null : proposalScope,service);
  const receipt=reportReceipt || localReceipt;
  useEffect(()=>{if(receipt.state==="accepted" && receipt.job)setJob(receipt.job);},[receipt.state,receipt.job]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>4294967295;
  const reasons=[...minimaxImageReasons({model,prompt,seed}),proposalScope && receipt.state!=="editing" && "대화 접수 상태를 확인하세요."];
  const sending=useRef(false),promptRef=useRef(null),reviewRef=useRef(null),formRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),previewRequest=useRef(null),submissionRequest=useRef(null),modelStatus=useRef(null);
  const updateModel=useCallback(value=>{modelStatus.current=value;setModel(value);},[]);
  useEffect(()=>()=>{const preview=previewRequest.current,submission=submissionRequest.current;previewRequest.current=null;submissionRequest.current=null;preview?.abort();submission?.abort();},[]);
  async function review(event){
    event.preventDefault();
    if((proposalScope && receipt.state!=="editing") || sending.current || busy || pending || !model?.generation_ready || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295)return;
    const focused=document.activeElement;
    sending.current=true;setBusy(true);setError("");
    const request={action:"generate",prompt:prompt.trim(),images:[],width:size,height:size,steps:6,seed};
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      if(proposalScope)await untilAborted(verifyFluxProposal(managementCommand,proposalScope,proposalScope.proposal),controller.signal);
      const result=await untilAborted(managementCommand(service,"preview",request,{signal:controller.signal}),controller.signal);
      if(previewRequest.current!==controller)return;
      if(typeof result?.prompt!=="string" || !result.prompt || !/^[a-f0-9]{64}$/.test(result?.prompt_sha256 || ""))throw new Error("최종 프롬프트를 확인할 수 없습니다.");
      setPreview(result.prompt);setPending({...request,expected_prompt_sha256:result.prompt_sha256});
      requestAnimationFrame(()=>{if(document.activeElement===focused || document.activeElement===document.body)reviewRef.current?.focus();});
    }catch(problem){if(previewRequest.current===controller)setError(timedOut ? "프롬프트 검토 시간이 초과됐습니다. 다시 시도하세요." : problem?.message || "공용 화풍을 적용한 프롬프트를 확인할 수 없습니다.");}
    finally{clearTimeout(timeout);if(previewRequest.current===controller){previewRequest.current=null;sending.current=false;setBusy(false);}}
  }
  function closeReview(){
    const restore=reviewRef.current?.contains(document.activeElement);
    setPending(null);setPreview("");
    if(restore)requestAnimationFrame(()=>restoreLostFocus(document,promptRef.current));
  }
  async function submit(){
    if(!pending || sending.current || !modelStatus.current?.generation_ready || (proposalScope && receipt.state!=="editing"))return;
    sending.current=true;setBusy(true);setError("");
    const controller=new AbortController();submissionRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      if(proposalScope)await untilAborted(verifyFluxProposal(managementCommand,proposalScope,proposalScope.proposal),controller.signal);
      const result=await untilAborted(proposalScope ? managementCommand("hermes-agent","hermes-minimax-submit",{session_id:proposalScope.session,proposal_job_id:proposalScope.job,request_id:receipt.id,service,request:pending},{signal:controller.signal}) : managementCommand(service,"generate",pending,{signal:controller.signal}),controller.signal);
      if(submissionRequest.current!==controller)return;
      const resultId=proposalScope ? (result?.state==="accepted" ? result.job_id : null) : result?.id;
      if(!validGenerationJobId(resultId))throw new Error("접수 ID를 확인할 수 없습니다.");
      if(proposalScope)receipt.refresh();
      setJob(resultId);setRevision(n=>n+1);setPending(null);
    }catch(problem){if(proposalScope)receipt.unknown();if(submissionRequest.current===controller)setError((timedOut ? "응답 시간이 초과됐습니다." : problem?.message || "응답을 확인할 수 없습니다.")+" 접수 여부가 불확실합니다. 재접수 전에 이력을 확인하세요.");}
    finally{clearTimeout(timeout);if(submissionRequest.current===controller){submissionRequest.current=null;sending.current=false;setBusy(false);}}
  }
  return <article className="vace-page generator-page-common">
    <GeneratorPageIdentity service={service} embedded={embedded} changelogCard/>
    <GeneratorUsage generator={service}/>
    {proposalScope && !reportReceipt && <MinimaxReportStatus receipt={receipt}/>}
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <ModelReadiness service={service} onStatus={updateModel}/>
    <ActiveGeneratorProgress service={service} revision={revision} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}
    <GeneratorSectionCard title="생성 입력" summary="프롬프트와 시드" defaultOpen className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending}><legend className="generator-visually-hidden">생성 입력</legend>
      <label>프롬프트<textarea ref={promptRef} required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <PromptWordCount text={prompt}/>
      <SeedInput value={seed} max={4294967295} error={invalidSeed ? "0부터 4,294,967,295까지의 정수로 입력하세요." : ""} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <label>이미지 크기<select value={size} onChange={event=>setSize(Number(event.target.value))}><option value={512}>512×512</option><option value={1024}>1024×1024</option></select></label>
      <p>직접 생성 · 6스텝 · INT8{size===512 && " · 512×512 실제 생성 미검증"}</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="minimax-image-review" aria-label="생성 요청 확인"><h2>공용 화풍 적용 프롬프트</h2><GpuQueueSummary/><pre className="generation-review-text">{preview}</pre><PromptWordCount text={preview} label="최종 프롬프트"/><p>{pending.width}×{pending.height} · 6스텝 · 시드 {pending.seed}</p><GenerationReviewActions busy={busy} disabledReason={!model?.generation_ready ? "모델 준비 상태를 확인하세요." : proposalScope && receipt.state!=="editing" ? "대화 접수 상태를 확인하세요." : ""} onCancel={closeReview} onConfirm={submit}/></section>}
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")}
      onSelectedDeleted={(id)=>{if(id===job)setJob("");setRevision(n=>n+1);}}
      footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={()=>{setJob("");setRevision(n=>n+1);}}/>}
      renderResult={(id,close)=><section id="job-result" ref={resultRef} tabIndex={-1} aria-label="선택한 이미지 작업 결과"><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} statusCommand="status"/><MediaJobResult kind="image" service={service} id={id}/></section>}/></div>
  </article>;
}
