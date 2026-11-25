import React, {useCallback, useEffect, useId, useRef, useState} from "react";
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
import {requestErrorMessage} from "./requestError.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";

const service = "minimax-h3-image";
export function minimaxImageReasons({model,prompt,seed}) {
  return [!model?.generation_ready && "모델 준비 상태를 확인하세요.",!prompt.trim() && "프롬프트를 입력하세요.",(!Number.isInteger(seed) || seed<0 || seed>4294967295) && "시드는 0부터 4294967295까지의 정수로 입력하세요."];
}
function imageBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('참조 이미지를 읽을 수 없습니다.'));reader.readAsDataURL(file);});}
export default function MiniMaxH3ImagePage({embedded=false,initialInputs=null,proposalScope=null,reportReceipt=null}={}) {
  const inputLockId=useId();
  const [prompt,setPrompt]=useState(initialInputs?.prompt || ""), [seed,setSeed]=useState(initialInputs?.seed ?? 42), [model,setModel]=useState(null), [modelError,setModelError]=useState("");
  const [size,setSize]=useState(initialInputs?.width===832 && initialInputs?.height===480 ? 832 : initialInputs?.width===512 && initialInputs?.height===512 ? 512 : 1024);
  const [downscale,setDownscale]=useState(false);
  const [references,setReferences]=useState([null,null]),[checking,setChecking]=useState([false,false]);
  const [pending,setPending]=useState(null), [preview,setPreview]=useState(""), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [job,setJob]=useState(()=>{
    const linked=new URLSearchParams(window.location.search).get("job");
    return !embedded && validGenerationJobId(linked) ? linked : "";
  }), [revision,setRevision]=useState(0);
  const localReceipt=useMinimaxReportReceipt(reportReceipt ? null : proposalScope,service);
  const receipt=reportReceipt || localReceipt;
  useEffect(()=>{if(receipt.state==="accepted" && receipt.job)setJob(receipt.job);},[receipt.state,receipt.job]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>4294967295;
  const reasons=[...minimaxImageReasons({model,prompt,seed}),checking.some(Boolean) && "참조 이미지 확인이 끝날 때까지 기다리세요.",proposalScope && receipt.state!=="editing" && "대화 접수 상태를 확인하세요."];
  const sending=useRef(false),promptRef=useRef(null),reviewRef=useRef(null),formRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),previewRequest=useRef(null),submissionRequest=useRef(null),modelStatus=useRef(null),previewFocus=useRef(null);
  const updateModel=useCallback(value=>{modelStatus.current=value;setModel(value);},[]);
  useEffect(()=>()=>{const preview=previewRequest.current,submission=submissionRequest.current;previewRequest.current=null;submissionRequest.current=null;preview?.abort();submission?.abort();},[]);
  useEffect(()=>{if(pending && previewFocus.current && (document.activeElement===previewFocus.current || document.activeElement===document.body))reviewRef.current?.focus();},[pending]);
  useEffect(()=>{if(!busy && previewFocus.current){if(error)restoreLostFocus(document,previewFocus.current);previewFocus.current=null;}},[busy,error]);
  async function review(event){
    event.preventDefault();
    if((proposalScope && receipt.state!=="editing") || sending.current || busy || pending || checking.some(Boolean) || !model?.generation_ready || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295)return;
    const focused=document.activeElement;previewFocus.current=focused;
    sending.current=true;setBusy(true);setError("");
    const height=size===832?480:size;
    const request={action:"generate",prompt:prompt.trim(),images:[],width:downscale?size*2:size,height:downscale?height*2:height,steps:6,seed,...(downscale?{output_size:{width:size,height}}:{})};
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      request.images=await Promise.all(references.filter(Boolean).map(imageBase64));
      if(controller.signal.aborted)return;
      if(proposalScope)await untilAborted(verifyFluxProposal(managementCommand,proposalScope,proposalScope.proposal),controller.signal);
      const result=await untilAborted(managementCommand(service,"preview",request,{signal:controller.signal}),controller.signal);
      if(previewRequest.current!==controller)return;
      if(typeof result?.prompt!=="string" || !result.prompt || !/^[a-f0-9]{64}$/.test(result?.prompt_sha256 || ""))throw new Error("최종 프롬프트를 확인할 수 없습니다.");
      setPreview(result.prompt);setPending({...request,expected_prompt_sha256:result.prompt_sha256});
    }catch(problem){if(previewRequest.current===controller)setError(timedOut ? "프롬프트 검토 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
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
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}>
    <GeneratorPageIdentity service={service} embedded={embedded} changelogCard/>
    <GeneratorUsage generator={service}/>
    {proposalScope && !reportReceipt && <MinimaxReportStatus receipt={receipt}/>}
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : model.generation_ready ? "준비 완료" : "준비 필요"}><ModelReadiness service={service} onStatus={updateModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}
    <GeneratorSectionCard title="생성 입력" summary="프롬프트와 시드" defaultOpen className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending} aria-describedby={busy || pending ? inputLockId : undefined}><legend className="generator-visually-hidden">생성 입력</legend>
      <label>프롬프트<textarea ref={promptRef} required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <PromptWordCount text={prompt}/>
      <SeedInput value={seed} max={4294967295} error={invalidSeed ? "0부터 4,294,967,295까지의 정수로 입력하세요." : ""} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <label>이미지 크기<select value={size} onChange={event=>setSize(Number(event.target.value))}><option value={832}>832×480</option><option value={512}>512×512</option><option value={1024}>1024×1024</option></select></label>
      {!proposalScope && <label><input type="checkbox" checked={downscale} onChange={event=>setDownscale(event.target.checked)}/> 2배 크기로 생성 후 축소</label>}
      {downscale && <p>생성 {size*2}×{(size===832?480:size)*2} · 최종 {size}×{size===832?480:size} · OpenCV 영역 보간</p>}
      <section aria-label="참조 이미지"><p>참조 PNG · 최대 2장</p><div className="reference-image-slots">{[0,1].map(index=><ReferenceImageInput key={index} label={"참조 이미지 "+(index+1)} accept="image/png" maxBytes={3000000} source={references[index]} disabled={busy || !!pending || (index===1 && !references[0])} onCheckingChange={value=>setChecking(previous=>{const next=[...previous];next[index]=value;return next;})} onChange={value=>setReferences(previous=>{const next=[...previous];next[index]=value;if(index===0 && !value)next[1]=null;return next;})}/>)}</div>{!references[0] && <p>두 번째 참조를 추가하려면 먼저 첫 번째 참조를 선택하세요.</p>}</section>
      <p>직접 생성 · 6스텝 · INT8{size===512 && " · 512×512 실제 생성 미검증"}</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset>{(busy || pending) && <p id={inputLockId} role="status">{pending ? "입력을 수정하려면 아래 검토에서 입력 수정을 선택하세요." : "최종 프롬프트를 확인하고 있습니다. 잠시 기다려 주세요."}</p>}</form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review minimax-image-review" aria-label="생성 요청 확인"><h2>공용 화풍 적용 프롬프트</h2><GpuQueueSummary/><pre className="generation-review-text" tabIndex={0} aria-label="검토할 프롬프트">{preview}</pre><PromptWordCount text={preview} label="최종 프롬프트"/><p>생성 {pending.width}×{pending.height}{pending.output_size && ` · 최종 ${pending.output_size.width}×${pending.output_size.height} (OpenCV)`} · 6스텝 · 시드 {pending.seed} · 참조 {pending.images.length}장</p><GenerationReviewActions busy={busy} disabledReason={!model?.generation_ready ? "모델 준비 상태를 확인하세요." : proposalScope && receipt.state!=="editing" ? "대화 접수 상태를 확인하세요." : ""} onCancel={closeReview} onConfirm={submit}/></section>}
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")}
      onSelectedDeleted={(id)=>{if(id===job)setJob("");setRevision(n=>n+1);}}
      footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={()=>{setJob("");setRevision(n=>n+1);}}/>}
      renderResult={(id,close)=><section id="job-result" ref={resultRef} tabIndex={-1} aria-label="선택한 이미지 작업 결과"><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} statusCommand="status"/><MediaJobResult kind="image" service={service} id={id}/></section>}/></div>
  </article>;
}
