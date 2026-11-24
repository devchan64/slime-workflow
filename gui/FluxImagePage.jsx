import usePageTitle from "./usePageTitle.js";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import ActionButton from "./ActionButton.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {fluxProposalRequestId,classifyFluxProposalReceipt,verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import {fluxModelReady} from "./fluxModelReady.mjs";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";
import {prepareFluxPreview} from "./fluxPreview.mjs";
import {filterFluxGuides,addFluxRolePrompt} from "./fluxGuides.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import RecoverableImage from "./RecoverableImage.jsx";
import {imageRetryUrl} from "./imageRetryUrl.mjs";
import {validFluxProfile} from "./fluxProfileValidation.mjs";

import readReference from "./readReference.js";

function pngFile(encoded,name){
  return new File([Uint8Array.from(atob(encoded),char=>char.charCodeAt(0))],name,{type:"image/png"});
}

export function FluxToolFeedback({loading,notice,error}){
  return <>{loading && <p role="status">참조 입력을 불러오고 있습니다.</p>}{notice && <p role={error ? "alert" : "status"}>{notice}</p>}</>;
}

function GuideThumbnail({src}){
  const [failed,setFailed]=useState(false);
  return failed ? <span>미리보기 없음</span> : <img width="110" loading="lazy" src={src} alt="" onError={()=>setFailed(true)}/>;
}

export function FluxGuidePagination({count,page,pageSize,hintId,navRef,onMove}){
  const previousDisabled=page===0,nextDisabled=(page+1)*pageSize>=count;
  const hint=count===0 ? "검색 결과가 없어 페이지를 이동할 수 없습니다." : previousDisabled && nextDisabled ? "표시할 다른 가이드 페이지가 없습니다." : previousDisabled ? "첫 번째 가이드 페이지입니다." : nextDisabled ? "마지막 가이드 페이지입니다." : "";
  return <nav ref={navRef} className="flux-guides-pages" aria-label="가이드 페이지 이동">
    <button type="button" aria-label="이전 가이드 페이지" disabled={previousDisabled} aria-describedby={previousDisabled ? hintId : undefined} onClick={event=>onMove(event,-1)}>이전</button>
    <span aria-live="polite">{count ? page+1 : 0} / {Math.ceil(count/pageSize)} 페이지</span>
    <button type="button" aria-label="다음 가이드 페이지" disabled={nextDisabled} aria-describedby={nextDisabled ? hintId : undefined} onClick={event=>onMove(event,1)}>다음</button>
    <small id={hintId}>{hint}</small>
  </nav>;
}

export default function FluxImagePage(props={}){
  const service=props.serviceOverride || location.pathname.match(/\/management\/frame\/(flux-[a-z]+)-generator/)?.[1] || "flux-image";
  return <FluxImagePageForService key={service} {...props} serviceOverride={service}/>;
}

function FluxImagePageForService({serviceOverride,embedded=false,initialInputs=null,receiptScope=null,session:embeddedSession=""}={}){
  const referenceOrderHelpId=useId(),guidePageHelpId=useId();
  const service=serviceOverride || location.pathname.match(/\/management\/frame\/(flux-[a-z]+)-generator/)?.[1] || "flux-image";
  const [profile,setProfile]=useState(null),[attempt,setAttempt]=useState(0);
  const [profileError,setProfileError]=useState("");
  const profileRetryRef=useRef(null),profileRetryFocus=useRef(false),profilePending=useRef(true);
  function retryProfile(){
    if(profilePending.current)return;
    profilePending.current=true;profileRetryFocus.current=document.activeElement===profileRetryRef.current;
    setProfileError("");setAttempt(current=>current+1);
  }
  usePageTitle(profile?.label ? "FLUX 이미지 생성 · "+profile.label : "FLUX 이미지 생성",embedded);
  const seamless=service==="flux-seamless";
  const query=new URLSearchParams(location.search);
  const session=receiptScope?.session || embeddedSession || query.get("session") || "";
  const previewScope=JSON.stringify([service,session,receiptScope?.job || "",receiptScope?.snapshot || "",receiptScope?.offset ?? null]);
  const currentPreviewScope=useRef(previewScope);currentPreviewScope.current=previewScope;
  const [form,setForm]=useState({prompt:"",translation_source_ko:"",width:768,height:768,steps:16,seed:10107,tag:""});
  const [files,setFiles]=useState([]),[review,setReview]=useState(null);
  const inputRef=useRef({form,files});inputRef.current={form,files};
  const imageSelectionRevision=useRef(0),checkingSlots=useRef(new Set());
  const [imagesChecking,setImagesChecking]=useState(false);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[model,setModel]=useState(null);
  const reviewEpoch=useRef(0),interactionRef=useRef({busy,review});interactionRef.current={busy,review};
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [guideQuery,setGuideQuery]=useState(""),[guidePage,setGuidePage]=useState(0),[pageSize,setPageSize]=useState(8);
  const [guideThumbnailRevision,retryGuideThumbnails]=useState(0);
  const guideSearchRef=useRef(null),guidePagesRef=useRef(null),guidePageFrame=useRef(null),inputFormRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null);
  const previewRequest=useRef(null),previewCancelled=useRef(false);
  const [previewing,setPreviewing]=useState(false);
  useEffect(()=>{
    if(previewCancelled.current){previewCancelled.current=false;setBusy(false);setPreviewing(false);}
    return ()=>{const current=previewRequest.current;if(current){previewRequest.current=null;previewCancelled.current=true;current.abort();}};
  },[previewScope]);
  useEffect(()=>{if(!review)return;const origin=reviewOrigin.current;const frame=requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===origin) && reviewRef.current?.isConnected)reviewRef.current.focus();});return ()=>cancelAnimationFrame(frame);},[review]);
  useEffect(()=>{
    if(!profileRetryFocus.current || (!profile && !profileError))return;
    profileRetryFocus.current=false;
    const frame=requestAnimationFrame(()=>{if(document.activeElement===document.body)(profile ? inputFormRef.current : profileRetryRef.current)?.focus();});
    return ()=>cancelAnimationFrame(frame);
  },[profile,profileError]);
  const [selectedGuide,setSelectedGuide]=useState(""),[guideNotice,setGuideNotice]=useState(""),[guideError,setGuideError]=useState(false);
  const [toolNotice,setToolNotice]=useState(""),[toolError,setToolError]=useState(false),[toolLoading,setToolLoading]=useState(false);
  const guideRequest=useRef(null),toolFocus=useRef(null);
  useEffect(()=>()=>{const request=guideRequest.current;guideRequest.current=null;request?.abort();},[]);
  useEffect(()=>()=>{if(guidePageFrame.current!==null)cancelAnimationFrame(guidePageFrame.current);},[]);
  useEffect(()=>{
    if(busy || !toolFocus.current)return;
    const target=toolFocus.current;toolFocus.current=null;
    const frame=requestAnimationFrame(()=>{if(!restoreLostFocus(document,target))restoreLostFocus(document,inputFormRef.current);});
    return ()=>cancelAnimationFrame(frame);
  },[busy]);
  useEffect(()=>{setGuideNotice("");},[selectedGuide]);
  const [stage,setStage]=useState("");
  const [layout,setLayout]=useState(""),[subject,setSubject]=useState("");
  const sending=useRef(false);
  const [historyRevision,setHistoryRevision]=useState(0);
  const receiptKey=receiptScope ? `flux-proposal-receipt:${receiptScope.session}:${receiptScope.job}:${service}` : "";
  const handoffKey=session ? `flux-gpu-handoff:${session}:${receiptScope?.job || "direct"}:${service}` : "";
  const [handoffReview,setHandoffReview]=useState(null),[handoffId,setHandoffId]=useState(()=>handoffKey ? sessionStorage.getItem(handoffKey) || "" : ""),[handoffStatus,setHandoffStatus]=useState(null);
  useEffect(()=>{setReview(null);setHandoffReview(null);},[previewScope]);
  const [receipt,setReceipt]=useState("");
  const [receiptJob,setReceiptJob]=useState("");
  const [receiptNotice,setReceiptNotice]=useState("");
  const [receiptState,setReceiptState]=useState(()=>receiptKey ? "checking" : "editing");
  async function checkReceipt(id){
    const value=await managementCommand("hermes-agent","hermes-service-receipt",{service,request_id:id});
    const checked=classifyFluxProposalReceipt(value,id,service);
    if(checked.state==="accepted"){
      setReceiptJob(checked.job);setJob(checked.job);setReceiptState("accepted");setReceiptNotice("접수된 작업을 확인했습니다.");
    }else if(checked.state==="editing"){setReceiptJob("");setReceiptState("editing");setReceiptNotice("");}
    else if(checked.state==="rejected"){setReceiptJob("");setReceiptState("rejected");setReceiptNotice("생성 요청이 검증에 실패해 접수되지 않았습니다. GPU 양도 상태와 입력을 확인하세요.");}
    else{setReceiptJob("");setReceiptState("unknown");setReceiptNotice("접수 여부를 확인할 수 없습니다. 자동 재접수하지 않습니다. 생성 이력과 접수 기록을 확인하세요.");}
    return checked;
  }
  async function refreshReceipt(){
    setReceiptState("checking");
    try{
      const id=await fluxProposalRequestId(receiptScope.session,receiptScope.job,service);
      setReceipt(id);
      const handoff=validateGpuHandoffStatus(await managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id}),session,id,service);
      if(handoff.state!=="not_found"){
        setHandoffId(id);setHandoffStatus(handoff);
      }
      const checked=await checkReceipt(id);
      if(handoff.state!=="not_found" && checked.state==="editing"){
        setReceiptState("unknown");setReceiptNotice("GPU 양도 요청의 상태를 확인하세요. 같은 제안을 다시 접수하지 않습니다.");
      }
    }catch(error){setReceiptState("unknown");setReceiptNotice(error.message || "접수 기록을 확인할 수 없습니다. 생성 이력을 확인하세요.");}
  }
  useEffect(()=>{if(receiptKey)refreshReceipt();},[]);
  async function refreshHandoff(id){
    const value=await managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id});
    setHandoffStatus(validateGpuHandoffStatus(value,session,id,service));
    if(value.job_id)setJob(value.job_id);
  }
  useEffect(()=>{if(handoffId)refreshHandoff(handoffId).catch(()=>setNotice("GPU 양도 상태를 확인할 수 없습니다. 다시 확인하세요."));},[]);
  useEffect(()=>{
    const controller=new AbortController();
    let active=true,timedOut=false;
    profilePending.current=true;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function load(){
      setProfileError("");
      try{
        const defaults=await untilAborted((async()=>{const response=await fetch("/management/assistant/flux-defaults/"+service,{signal:controller.signal});if(!response.ok)throw new Error("생성기 기본 입력을 불러올 수 없습니다.");return response.json();})(),controller.signal);
        if(!validFluxProfile(defaults))throw new Error("생성기 기본 입력 형식을 확인할 수 없습니다.");
        if(controller.signal.aborted)return;
        setForm(current=>({...current,prompt:defaults.prompt,width:defaults.width,height:defaults.height,...(initialInputs || {})}));
        setStage(defaults.stages?.[0]?.id || "");
        setLayout(defaults.layouts?.[0] || "");setSubject(defaults.subject || "");
        setProfile(defaults);
      }catch(error){if(active && (timedOut || !controller.signal.aborted))setProfileError(timedOut ? "생성기 기본 입력 조회 시간이 초과됐습니다." : error?.message || "생성기 기본 입력을 불러오지 못했습니다. 다시 시도하세요.");}
      finally{clearTimeout(timeout);if(active)profilePending.current=false;}
    }
    load();return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[service,attempt]);
  async function readJob(id,{signal}={}){
    const inputAtStart=inputRef.current,imageAtStart=imageSelectionRevision.current,checkingAtStart=checkingSlots.current.size>0,reviewAtStart=reviewEpoch.current,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const cancel=()=>controller.abort();
    if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",cancel,{once:true});
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
    const record=await untilAborted((async()=>{const response=await fetch("/management/assistant/flux-image-input/"+encodeURIComponent(id)+"?service="+service,{cache:"no-store",signal:controller.signal});const value=await response.json();if(!response.ok)throw new Error(value.detail || "저장된 입력을 확인할 수 없습니다.");return value;})(),controller.signal);
    if(!record || record.id!==id || !record.request || typeof record.request!=="object" || Array.isArray(record.request) || !Array.isArray(record.images) || record.images.some(value=>typeof value!=="string"))throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
    const files=record.images.map((encoded,index)=>pngFile(encoded,"reference-"+(index+1)+".png"));
    return {id:record.id,request:record.request,files,inputAtStart,imageAtStart,checkingAtStart,reviewAtStart,focusAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);signal?.removeEventListener("abort",cancel);}
  }
  function restore(input,record){
    if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.review)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
    if(record.checkingAtStart || checkingSlots.current.size || record.inputAtStart.form!==inputRef.current.form || record.inputAtStart.files!==inputRef.current.files || record.imageAtStart!==imageSelectionRevision.current)throw new Error("이미지 확인 중이거나 조회 중 입력이 변경되어 적용하지 않았습니다. 확인 후 다시 시도하세요.");
    setForm(seamless?{...input,width:512,height:512}:input);setFiles(seamless?[]:record.files);
    setNotice(seamless?"프롬프트와 시드를 복원했습니다. 새 타일은 512×512 무참조로 생성합니다.":"선택한 이력의 입력과 참조 이미지를 불러왔습니다.");
    requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===record.focusAtStart) && inputFormRef.current?.isConnected)inputFormRef.current.focus();});
  }
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  const guides=filterFluxGuides(profile?.guides || [],guideQuery);
  const guideAvailable=guides.some(item=>item.id===selectedGuide);
  function moveGuidePage(event,delta){
    const target=event.currentTarget,restore=document.activeElement===target;
    setGuidePage(current=>current+delta);setSelectedGuide("");
    if(!restore)return;
    if(guidePageFrame.current!==null)cancelAnimationFrame(guidePageFrame.current);
    guidePageFrame.current=requestAnimationFrame(()=>{
      guidePageFrame.current=null;
      if(!restoreLostFocus(document,target))restoreLostFocus(document,guidePagesRef.current?.querySelector('button:not(:disabled)') || guideSearchRef.current);
    });
  }
  function resetGuideSearch(event){
    const restore=document.activeElement===event.currentTarget;
    setGuideQuery("");setGuidePage(0);setSelectedGuide("");
    if(!restore)return;
    if(guidePageFrame.current!==null)cancelAnimationFrame(guidePageFrame.current);
    guidePageFrame.current=requestAnimationFrame(()=>{guidePageFrame.current=null;restoreLostFocus(document,guideSearchRef.current);});
  }
  function guideUrl(id){return "/management/assistant/"+service+"-guide/"+encodeURIComponent(id);}
  async function applyReferenceGuide(){
    if(guideRequest.current || interactionRef.current.busy || interactionRef.current.review)return;
    if(!guideAvailable){setGuideError(true);setGuideNotice("적용할 참조 가이드를 다시 선택하세요.");return;}
    if(checkingSlots.current.size){setGuideError(false);setGuideNotice("이미지 확인이 끝난 뒤 가이드를 적용하세요.");return;}
    toolFocus.current=inputFormRef.current?.contains(document.activeElement) ? document.activeElement : null;
    const version=++imageSelectionRevision.current,guide=selectedGuide,controller=new AbortController();guideRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setNotice("");setGuideNotice("");setGuideError(false);
    try{
      const blob=await untilAborted((async()=>{const response=await fetch(guideUrl(guide),{signal:controller.signal});if(!response.ok)throw new Error("참조 가이드를 불러올 수 없습니다.");return response.blob();})(),controller.signal);
      if(guideRequest.current!==controller)return;
      if(imageSelectionRevision.current!==version)throw new Error("조회 중 참조 이미지가 변경되었습니다. 다시 선택하세요.");
      const file=new File([blob],guide+".png",{type:"image/png"});
      setFiles(current=>[file,...current.slice(1)]);
      if(profile.rolePrompt)setForm(current=>({...current,prompt:addFluxRolePrompt(current.prompt,profile.rolePrompt)}));
      setGuideNotice("선택한 가이드를 참조 이미지 1에 적용했습니다.");
    }catch(error){if(guideRequest.current===controller){setGuideError(true);setGuideNotice("참조 가이드를 적용하지 못했습니다. · "+(timedOut ? "조회 시간이 초과됐습니다. 다시 시도하세요." : error?.message || "다시 시도하세요."));}}
    finally{clearTimeout(timeout);if(guideRequest.current===controller){guideRequest.current=null;setBusy(false);}}
  }
  async function runInputTool(load){
    if(guideRequest.current || interactionRef.current.busy || interactionRef.current.review)return;
    if(checkingSlots.current.size){setToolError(false);setToolNotice("이미지 확인이 끝난 뒤 다시 시도하세요.");return;}
    toolFocus.current=inputFormRef.current?.contains(document.activeElement) ? document.activeElement : null;
    const version=++imageSelectionRevision.current,controller=new AbortController();guideRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setToolLoading(true);setToolError(false);setToolNotice("");
    try{
      const apply=await untilAborted(load(controller.signal),controller.signal);
      if(guideRequest.current!==controller)return;
      if(imageSelectionRevision.current!==version)throw new Error("조회 중 참조 이미지가 변경되었습니다. 다시 시도하세요.");
      apply();setToolNotice("참조 입력을 적용했습니다.");
    }catch(error){if(guideRequest.current===controller){setToolError(true);setToolNotice(timedOut ? "참조 입력 조회 시간이 초과됐습니다. 다시 시도하세요." : error?.message || "참조 입력을 불러오지 못했습니다. 다시 시도하세요.");}}
    finally{clearTimeout(timeout);if(guideRequest.current===controller){guideRequest.current=null;setToolLoading(false);setBusy(false);}}
  }
  function defaultFace(){return runInputTool(async signal=>{
    const response=await fetch("/management/assistant/flux-expression-face",{signal});
    if(!response.ok)throw new Error("기본 얼굴 이미지를 불러올 수 없습니다.");
    const blob=await response.blob();return ()=>setFiles([new File([blob],"default-face-front-v1.png",{type:"image/png"})]);
  });}
  function applyStage(){return runInputTool(async signal=>{
    const response=await fetch("/management/assistant/flux-mannequin-stage/"+encodeURIComponent(stage),{signal});
    if(!response.ok)throw new Error("마네킨 제작 단계의 참조를 불러올 수 없습니다.");
    const {prompt,width,height,images}=await response.json();
    if(typeof prompt!=="string" || !Number.isInteger(width) || !Number.isInteger(height) || !Array.isArray(images) || images.some(value=>typeof value!=="string"))throw new Error("제작 단계 응답을 확인할 수 없습니다.");
    const references=images.map((encoded,index)=>pngFile(encoded,stage+"-"+(index+1)+".png"));
    return ()=>{setFiles(references);setForm(current=>({...current,prompt,width,height}));};
  });}
  function applyGuide(){return runInputTool(async signal=>{
    const response=await fetch("/management/assistant/flux-billboard-guide",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({layout,subject}),signal});
    if(!response.ok)throw new Error((await response.json()).detail || "가이드를 불러올 수 없습니다.");
    const {prompt,image}=await response.json();
    if(typeof prompt!=="string" || typeof image!=="string")throw new Error("가이드 응답을 확인할 수 없습니다.");
    const guide=pngFile(image,layout+".png");return ()=>{setFiles(current=>[guide,...current.slice(1)]);edit("prompt",prompt);};
  });}
  async function preview(event){
    event.preventDefault();
    if(previewRequest.current || busy || review)return;
    if(checkingSlots.current.size){event.preventDefault();setNotice("이미지 확인이 끝난 뒤 생성 요청을 검토하세요.");return;}
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const requestScope=previewScope;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reviewOrigin.current=document.activeElement;
    reviewEpoch.current++;
    setNotice("");setBusy(true);setPreviewing(true);setHandoffReview(null);
    try{
      const outcome=await untilAborted(prepareFluxPreview({service,session,receiptScope,form,files,signal:controller.signal,
        verifyProposal:verifyFluxProposal,readReference,command:managementCommand,
        fetchPreview:(name,payload,signal)=>fetch("/management/assistant/flux-image-preview?service="+encodeURIComponent(name),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),signal})}),controller.signal);
      if(previewRequest.current===controller && currentPreviewScope.current===requestScope){setHandoffReview(outcome.handoff);setReview({payload:outcome.payload,result:outcome.result,scope:requestScope});}
    }catch(problem){if(previewRequest.current===controller && currentPreviewScope.current===requestScope)setNotice(timedOut ? "입력 검토 시간이 초과됐습니다. 입력을 확인한 뒤 다시 시도하세요." : problem.message || "입력을 확인할 수 없습니다.");}
    finally{clearTimeout(timeout);if(previewRequest.current===controller){previewRequest.current=null;setPreviewing(false);setBusy(false);}}
  }
  async function submit(){
    if(!review || review.scope!==currentPreviewScope.current || sending.current || !fluxModelReady(model))return;
    sending.current=true;setBusy(true);
    let dispatched=false;
    try{
      if(receiptScope)await verifyFluxProposal(managementCommand,receiptScope,receiptScope.proposal);
      if(handoffReview){
        const id=receiptScope ? await fluxProposalRequestId(receiptScope.session,receiptScope.job,service) : crypto.randomUUID().replaceAll("-","");
        sessionStorage.setItem(handoffKey,id);setHandoffId(id);setHandoffStatus({state:"checking"});
        dispatched=true;
        const result=await managementCommand("hermes-agent","hermes-gpu-handoff-approve",{request_id:id,session_id:session,resident_id:handoffReview.resident_id,service,request:review.payload,review_hash:handoffReview.review_hash,confirmed:true});
        validateGpuHandoffStatus(result,session,id,service);
        if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready"].includes(result.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다.");
        setHandoffStatus(result);setNotice("확인한 GPU 양도 요청을 접수했습니다. 진행 상태를 확인하세요.");
      }else if(receiptKey){
        if(receiptState!=="editing")throw new Error("이전 접수 상태를 먼저 확인하세요.");
        const requestId=await fluxProposalRequestId(receiptScope.session,receiptScope.job,service);
        setReceipt(requestId);setReceiptState("checking");
        dispatched=true;
        const result=await managementCommand("hermes-agent","hermes-delegate-flux-profile",{request_id:requestId,service,request:review.payload,session_id:receiptScope.session,proposal_job_id:receiptScope.job});
        if(result.state!=="accepted" || result.service!==service || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(result.job_id || ""))throw new Error("접수 결과를 확인할 수 없습니다.");
        setReceiptJob(result.job_id);setJob(result.job_id);setReceiptState("accepted");setReceiptNotice("공용 GPU 대기열에 등록했습니다.");
      }else{
        dispatched=true;
        const result=await managementCommand(service,"generate",review.payload);
        if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
        setJob(result.id);setNotice("공용 GPU 대기열에 등록했습니다.");
      }
    }catch(problem){if(!dispatched)setNotice(problem.message+" · 요청은 접수되지 않았습니다.");else if(handoffReview)setNotice(problem.message+" · GPU 양도 상태를 확인하세요.");else if(receiptKey){setReceiptState("unknown");setReceiptNotice(problem.message+" · 생성 이력에서 접수 여부를 확인하세요.");}else setNotice(problem.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{sending.current=false;setBusy(false);setReview(null);setHandoffReview(null);}
  }
  return <article className={"flux-page"+(embedded ? "" : " flux-standalone")}><a href={"/management/assistant/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화</a>
    <h1 className={embedded ? "embedded-page-title" : undefined}>FLUX 이미지 생성 · {profile?.label}</h1><GeneratorChangelog generator={service+"-generator"}/>{embedded ? <details><summary>모델 상태 · {model ? (fluxModelReady(model) ? "준비 완료" : "준비 필요") : "확인 필요"}</summary><ModelReadiness service={service} session={session} onStatus={setModel}/></details> : <ModelReadiness service={service} session={session} onStatus={setModel}/>}
    {profile && <p>{profile.description}</p>}
    {!profile && (profileError ? <div role="alert">{profileError} <button ref={profileRetryRef} type="button" onClick={retryProfile}>기본 입력 다시 불러오기</button></div> : <p role="status">기본 입력을 불러오는 중입니다.</p>)}
    {handoffId && <GpuHandoffStatus session={session} id={handoffId} service={service} status={handoffStatus} onUpdate={value=>{setHandoffStatus(value);if(value.job_id)setJob(value.job_id);}}
      onClose={receiptKey && handoffStatus?.state!=="withdrawn" ? undefined : ()=>{sessionStorage.removeItem(handoffKey);setHandoffId("");setHandoffStatus(null);if(receiptKey){setReceiptState("unknown");setReceiptNotice("이 제안의 양도 요청은 철회됐습니다. 새 작업은 생성기 화면에서 요청하세요.");}}}/>}
    {receiptKey && receiptState!=="editing" && <section aria-label="FLUX 제안 접수 상태"><p>접수 ID · {receiptState==="accepted"?"접수 확인됨":receiptState==="rejected"?"접수 거절됨":receiptState==="checking"?"확인 중":"확인 필요"}</p>{receipt ? <JobIdentifier id={receipt} label="접수 ID" compact/> : <p>확인 불가</p>}{receiptState==="accepted" && receiptJob && <div><p>접수 작업</p><JobIdentifier id={receiptJob} compact/> <button type="button" onClick={()=>setJob(receiptJob)}>이 작업 결과 조회</button></div>}{receiptNotice && <p role="status">{receiptNotice}</p>}<p>같은 제안은 중복 접수를 막기 위해 다시 제출할 수 없습니다. 다른 작업은 생성기 화면에서 새로 요청하세요.</p><button type="button" disabled={busy || receiptState==="checking"} onClick={refreshReceipt}>접수 상태 다시 확인</button></section>}
    <form ref={inputFormRef} tabIndex={-1} aria-label="생성 입력" onSubmit={preview}><fieldset disabled={!profile || busy || Boolean(review) || Boolean(handoffId) || (receiptKey && receiptState!=="editing")}>
      {profile?.guides && <section className="flux-guides"><h2>{profile.rolePrompt?"신체 비율 기준":"건물 배치 가이드"}</h2>
        <div className="flux-guides-toolbar">
        <label>가이드 검색 <input ref={guideSearchRef} value={guideQuery} onChange={e=>{setGuideQuery(e.target.value);setGuidePage(0);setSelectedGuide("");}}/></label>
        <label>페이지당 가이드 <select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setGuidePage(0);setSelectedGuide("");}}>{[4,8,16,32].map(size=><option key={size}>{size}</option>)}</select></label>
        {guideQuery && <button type="button" onClick={resetGuideSearch}>검색 초기화</button>}
        </div>
        <p aria-live="polite">검색 결과 {guides.length}건</p>
        {!guides.length && <p role="status">일치하는 가이드가 없습니다. 검색어를 바꿔 보세요.</p>}
        <div className="flux-guides-list">
        {guides.slice(guidePage*pageSize,(guidePage+1)*pageSize).map(item=><button type="button" key={item.id} aria-pressed={selectedGuide===item.id} onClick={()=>setSelectedGuide(item.id)}>
          <GuideThumbnail key={item.id+":"+guideThumbnailRevision} src={imageRetryUrl(guideUrl(item.id)+"?thumbnail=true",guideThumbnailRevision)}/><span>{item.label} · {item.id}</span></button>)}
        </div>{guides.length>0 && <button type="button" onClick={()=>retryGuideThumbnails(value=>value+1)}>가이드 미리보기 다시 불러오기</button>}<FluxGuidePagination count={guides.length} page={guidePage} pageSize={pageSize} hintId={guidePageHelpId} navRef={guidePagesRef} onMove={moveGuidePage}/>
        {profile.rolePrompt && guideAvailable && <figure><div style={{maxWidth:240}}><RecoverableImage src={guideUrl(selectedGuide)} name="선택한 신체 비율 기준" kind="가이드"/></div><figcaption>{guides.filter(item=>item.id===selectedGuide).map(item=>[item.role,item.version,item.sha256].join(" · "))}</figcaption></figure>}
        <ActionButton reasons={[!guideAvailable && "적용할 참조 가이드를 선택하세요."]} onClick={applyReferenceGuide}>선택한 가이드를 첫 참조에 적용</ActionButton>
        {guideNotice && <p role={guideError ? "alert" : "status"}>{guideNotice}</p>}
      </section>}
      {profile?.stages && <>
        <label>마네킨 제작 단계 <select value={stage} onChange={e=>setStage(e.target.value)}>{profile.stages.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button type="button" onClick={applyStage}>선택한 단계와 프롬프트 예시 불러오기</button>
      </>}
      {profile?.layouts && <>
        <label>점유 가이드 <select value={layout} onChange={e=>setLayout(e.target.value)}>{profile.layouts.map(value=><option key={value}>{value}</option>)}</select></label>
        <label>생성 대상 <input value={subject} onChange={e=>setSubject(e.target.value)}/></label>
        <button type="button" disabled={!subject.trim()} onClick={applyGuide}>선택한 가이드와 프롬프트 적용</button>
      </>}
      {profile?.expressions ? <>
        <label>표정 <select value={form.prompt} onChange={e=>edit("prompt",e.target.value)}>{profile.expressions.map(item=><option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
        <p>{profile.expressions.find(item=>item.id===form.prompt)?.text}<PromptWordCount text={profile.expressions.find(item=>item.id===form.prompt)?.text} label="기본 프롬프트"/></p>
        <button type="button" onClick={defaultFace}>기본 캐릭터 정면 얼굴 불러오기</button>
      </> : <label>{service==="flux-building"?"건물 디자인 (한국어)":"프롬프트"} <textarea value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/><PromptWordCount text={form.prompt}/></label>}
      <FluxToolFeedback loading={toolLoading} notice={toolNotice} error={toolError}/>
      {service!=="flux-building" && <label>번역할 한국어 설명 <textarea value={form.translation_source_ko} onChange={e=>edit("translation_source_ko",e.target.value)}/><PromptWordCount text={form.translation_source_ko}/><small>입력하면 번역을 먼저 진행하고 번역문을 위 프롬프트 뒤에 추가합니다.</small></label>}
      {profile?.rolePrompt && form.prompt.trim()===profile.rolePrompt.trim() && !form.translation_source_ko.trim() && <p role="status">현재 입력에는 신체 비율 참조 안내만 있습니다. 원하는 캐릭터 외형이나 자세를 추가할 수 있습니다.</p>}
      {!seamless && <section aria-label="참조 이미지"><p>{profile?.expressions?"얼굴 참조 PNG (1장)":"참조 PNG (최대 2장)"}</p><div className="reference-image-slots">
        {Array.from({length:profile?.expressions?1:2},(_,index)=><ReferenceImageInput key={index} label={profile?.expressions?"얼굴 참조 이미지":"참조 이미지 "+(index+1)}
          accept="image/png" maxBytes={3000000} source={files[index]} disabled={!profile || busy || Boolean(review) || Boolean(handoffId) || (receiptKey && receiptState!=="editing") || (index>0 && !files[0])} describedBy={index===1 && !files[0] ? referenceOrderHelpId : undefined} onSelectionStart={()=>{imageSelectionRevision.current++;}} onCheckingChange={value=>{if(value)checkingSlots.current.add(index);else checkingSlots.current.delete(index);setImagesChecking(checkingSlots.current.size>0);}}
          onChange={file=>{setGuideNotice("");setFiles(current=>{const next=[...current];if(file)next[index]=file;else next.splice(index,1);return next;});}}/>)}
      </div>{!profile?.expressions && !files[0] && <p id={referenceOrderHelpId}>두 번째 참조를 추가하려면 먼저 첫 번째 참조를 선택하세요.</p>}</section>}
      {[["width","너비"],["height","높이"]].map(([key,label])=><label key={key}>{label} <input type="number" readOnly={seamless} required min="256" max={service==="flux-character"?2048:1664} step="16" value={form[key]} onChange={e=>edit(key,e.target.value)}/></label>)}
      {service==="flux-character" ? <label>생성 스텝 <input type="number" required min="1" max="50" value={form.steps} onChange={e=>edit("steps",e.target.value)}/></label> : <p>생성 스텝: 16</p>}
      <p>FLUX.3 Image Klein Distilled의 <a href="https://huggingface.co/black-forest-labs/flux-3-image-klein" target="_blank" rel="noreferrer">모델 카드</a> 권장값은 16스텝입니다.</p>
      <p>모델 카드는 구체적인 장면 설명을 권장합니다. 필요한 피사체, 구도, 배경과 조명을 프롬프트에 적어 주세요. 자동 프롬프트 확장은 사용하지 않습니다.</p>
      <SeedInput value={form.seed} max={4294967295} onChange={value=>edit("seed",value)}/>
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <ActionButton type="submit" reasons={[
        !profile && "생성기 설정을 확인 중입니다. 잠시 기다리거나 다시 불러오세요.",
        imagesChecking && "선택한 이미지 확인이 끝날 때까지 기다리세요.",
        profile && files.length < profile.minimum && "필수 참조 이미지를 선택하세요.",
        !form.prompt.trim() && !form.translation_source_ko.trim() && "프롬프트 또는 번역할 설명을 입력하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>
    {review && review.scope===previewScope && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>{profile?.expressions?"표정 프롬프트":"공용 화풍 적용 프롬프트"}</h2><pre className="generation-review-text" tabIndex={0} aria-label="검토할 프롬프트">{review.result.prompt}</pre><p><PromptWordCount text={review.result.prompt} label={review.result.translation ? "번역 전 프롬프트" : "최종 프롬프트"}/>{review.result.translation && " · 번역 후 최종 단어 수는 생성 시 확정됩니다."}</p>
      {review.result.translation && <p className="generation-review-text">생성 시 번역할 내용 · {review.result.translation}</p>}
      <GpuQueueSummary/>{handoffReview && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 {profile?.label || "FLUX"} 생성을 실행합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}<GenerationReviewActions busy={busy} onCancel={()=>{const focused=document.activeElement;setReview(null);setHandoffReview(null);requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)inputFormRef.current?.focus();});}} onConfirm={submit} confirmLabel={handoffReview ? "해제·생성·재적재에 동의" : "확인 후 대기열에 추가"} disabledReason={!fluxModelReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : handoffId ? "이전 GPU 양도 상태를 먼저 확인하세요." : ""}/></section>}
    {previewing && <p role="status">입력과 GPU 양도 여부를 확인하고 있습니다.</p>}
    {notice && <p role="status">{notice}</p>}
    {profile && <fieldset className="flux-history-controls" disabled={busy || Boolean(review)}><GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setHistoryRevision(value=>value+1);}} key={historyRevision} service={service} readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob("")} restore={restore} renderResult={(id,close)=><section aria-label="선택한 FLUX 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} kind="flux" service={service} readJob={readJob} onDeleted={message=>{setJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/></section>}/></fieldset>}
    <GeneratorJobResult selectionControls job="" kind="flux" service={service} onDeleted={message=>{setJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/>
  </article>;
}
